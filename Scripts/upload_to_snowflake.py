"""
upload_to_snowflake.py
Uploads generated CSVs to Snowflake internal stage and COPY INTO tables.
Handles full load and incremental (inserts + MERGE for updates).

FIXES:
  1. ON_ERROR = 'ABORT_STATEMENT' instead of 'SKIP_FILE' — fails loudly.
  2. MERGE column names are double-quoted to match Terraform lowercase identifiers.
  3. Each upload is wrapped in try/except so failures are visible.
"""

import os
import argparse
import snowflake.connector
from datetime import date


FULL_LOAD_TABLES = [
    "DIM_DATE", "DIM_REGION", "DIM_LOCATION", "DIM_EMPLOYEE",
    "DIM_PRODUCTS", "DIM_CUSTOMERS", "DIM_STORE",
    "CREDIT_POLICY", "CUSTOMER_CREDIT_MAPPING",
    "FACT_INVOICE_HEADER", "FACT_INVOICE_LINE_ITEM",
    "FACT_PAYMENT_B2B_B2D", "FACT_PAYMENT_B2C", "FACT_RETURNS",
]

# Straight insert files for incremental (full schema match)
INCREMENTAL_INSERT_TABLES = [
    ("FACT_INVOICE_HEADER_new",    "FACT_INVOICE_HEADER"),
    ("FACT_INVOICE_LINE_ITEM_new", "FACT_INVOICE_LINE_ITEM"),
    ("FACT_PAYMENT_B2B_B2D_new",   "FACT_PAYMENT_B2B_B2D"),
    ("FACT_PAYMENT_B2C_new",       "FACT_PAYMENT_B2C"),
    ("FACT_RETURNS_new",           "FACT_RETURNS"),
]


def get_conn():
    required = ["SNOWFLAKE_ORGANIZATION", "SNOWFLAKE_ACCOUNT",
                "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]
    for var in required:
        if not os.environ.get(var):
            raise ValueError(f"Missing required env var: {var}")

    org     = os.environ["SNOWFLAKE_ORGANIZATION"]
    account = os.environ["SNOWFLAKE_ACCOUNT"]
    db      = os.environ.get("SNOWFLAKE_DATABASE", "FINANCE_DATA_DB")

    return snowflake.connector.connect(
        account=f"{org}-{account}".lower(),
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "FINANCE_WH"),
        database=db,
        schema="RAW",
    )


def put_and_copy(cursor, local_path: str, stage_path: str, table_name: str):
    """PUT a CSV to internal stage then COPY INTO the target table."""
    db       = os.environ.get("SNOWFLAKE_DATABASE", "FINANCE_DATA_DB")
    filename = os.path.basename(local_path)
    gz_path  = f"{stage_path}/{filename}.gz"

    print(f"  PUT  {local_path}")
    cursor.execute(f"""
        PUT file://{local_path}
        @"{db}"."RAW"."FINANCE_STAGE"/{stage_path}
        AUTO_COMPRESS=TRUE OVERWRITE=TRUE
    """)

    print(f"  COPY INTO {db}.RAW.{table_name}")
    cursor.execute(f"""
        COPY INTO "{db}"."RAW"."{table_name}"
        FROM '@"{db}"."RAW"."FINANCE_STAGE"/{gz_path}'
        FILE_FORMAT = (
            TYPE                         = 'CSV'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            SKIP_HEADER                  = 1
            NULL_IF                      = ('', 'None', 'NULL')
            EMPTY_FIELD_AS_NULL          = TRUE
        )
        ON_ERROR = 'ABORT_STATEMENT'
    """)
    # FIX 1: was 'SKIP_FILE' — silently swallowed schema mismatches.
    # 'ABORT_STATEMENT' raises an exception so the workflow fails visibly.

    for row in cursor.fetchall():
        print(f"    → {row}")


def run_full(conn):
    """Upload all 14 full-load CSVs."""
    base   = os.path.join(os.environ.get("OUTPUT_PATH", "./data"), "full_load")
    cursor = conn.cursor()

    for table in FULL_LOAD_TABLES:
        path = os.path.join(base, f"{table}.csv")
        if not os.path.exists(path):
            print(f"  SKIP {table} (file not found)")
            continue
        # FIX 3: wrap each upload so failures surface clearly
        try:
            put_and_copy(cursor, os.path.abspath(path), f"full/{table}", table)
        except Exception as e:
            print(f"  ❌ FAILED {table}: {e}")
            raise

    cursor.close()
    print("✅ Full load upload complete.")


def run_incremental(conn):
    """Upload today's incremental files. Inserts go direct; updates use MERGE."""
    base    = os.path.join(os.environ.get("OUTPUT_PATH", "./data"), "incremental")
    today   = date.today().strftime("%Y%m%d")
    inc_dir = os.path.join(base, today)

    if not os.path.exists(inc_dir):
        print(f"No incremental dir for {today}. Exiting.")
        return

    db     = os.environ.get("SNOWFLAKE_DATABASE", "FINANCE_DATA_DB")
    cursor = conn.cursor()

    # ── Straight inserts ──────────────────────────────────────
    for (file_stem, target_table) in INCREMENTAL_INSERT_TABLES:
        path = os.path.join(inc_dir, f"{file_stem}.csv")
        if not os.path.exists(path):
            print(f"  SKIP {file_stem} (not generated today)")
            continue
        # FIX 3: wrap each upload so failures surface clearly
        try:
            put_and_copy(cursor, os.path.abspath(path),
                         f"incremental/{today}/{file_stem}", target_table)
        except Exception as e:
            print(f"  ❌ FAILED {file_stem}: {e}")
            raise

    # ── Updates via MERGE ─────────────────────────────────────
    updates_path = os.path.join(inc_dir, "FACT_INVOICE_HEADER_updates.csv")
    if os.path.exists(updates_path):
        print("  Processing FACT_INVOICE_HEADER_updates (MERGE)...")
        stage_dir = f"incremental/{today}/FACT_INVOICE_HEADER_updates"
        filename  = "FACT_INVOICE_HEADER_updates.csv"
        gz_path   = f"{stage_dir}/{filename}.gz"

        cursor.execute(f"""
            PUT file://{os.path.abspath(updates_path)}
            @"{db}"."RAW"."FINANCE_STAGE"/{stage_dir}
            AUTO_COMPRESS=TRUE OVERWRITE=TRUE
        """)

        cursor.execute("""
            CREATE OR REPLACE TEMPORARY TABLE RAW.FACT_INVOICE_HEADER_UPDATES_TEMP (
                invoice_key    NUMBER,
                invoice_id     VARCHAR,
                customer_key   NUMBER,
                payment_status VARCHAR,
                net_payment    FLOAT,
                updated_date   DATE
            )
        """)

        cursor.execute(f"""
            COPY INTO RAW.FACT_INVOICE_HEADER_UPDATES_TEMP
            FROM '@"{db}"."RAW"."FINANCE_STAGE"/{gz_path}'
            FILE_FORMAT = (
                TYPE                         = 'CSV'
                FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                SKIP_HEADER                  = 1
                NULL_IF                      = ('', 'None', 'NULL')
                EMPTY_FIELD_AS_NULL          = TRUE
            )
            ON_ERROR = 'ABORT_STATEMENT'
        """)

        # FIX 2: quote column names to match Terraform lowercase identifiers.
        # Without quotes, Snowflake uppercases them → "invalid identifier" error.
        cursor.execute("""
            MERGE INTO RAW.FACT_INVOICE_HEADER AS target
            USING RAW.FACT_INVOICE_HEADER_UPDATES_TEMP AS source
            ON target."invoice_key" = source."invoice_key"
            WHEN MATCHED THEN UPDATE SET
                target."payment_status" = source."payment_status",
                target."net_payment"    = source."net_payment"
        """)
        print("  ✅ FACT_INVOICE_HEADER updates merged.")

    cursor.close()
    print("✅ Incremental upload complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "incremental"], required=True)
    args = parser.parse_args()

    conn = get_conn()
    if args.mode == "full":
        run_full(conn)
    else:
        run_incremental(conn)
    conn.close()
