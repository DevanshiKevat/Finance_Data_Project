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

INCREMENTAL_TABLES = [
    ("FACT_INVOICE_HEADER_new",     "FACT_INVOICE_HEADER"),
    ("FACT_INVOICE_LINE_ITEM_new",  "FACT_INVOICE_LINE_ITEM"),
    ("FACT_INVOICE_HEADER_updates", "FACT_INVOICE_HEADER"),
    ("FACT_PAYMENT_B2B_B2D_new",    "FACT_PAYMENT_B2B_B2D"),
    ("FACT_PAYMENT_B2C_new",        "FACT_PAYMENT_B2C"),
    ("FACT_RETURNS_new",            "FACT_RETURNS"),
]


def get_conn():
    required = ["SNOWFLAKE_ORGANIZATION", "SNOWFLAKE_ACCOUNT",
                "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD"]
    for var in required:
        if not os.environ.get(var):
            raise ValueError(f"Missing required env var: {var}")

    org     = os.environ["SNOWFLAKE_ORGANIZATION"]
    account = os.environ["SNOWFLAKE_ACCOUNT"]

    return snowflake.connector.connect(
        account=f"{org}-{account}".lower(),
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "FINANCE_DATA_DB"),
        schema="RAW",
    )


def put_and_copy(cursor, local_path: str, stage_path: str, table_name: str):
    filename = os.path.basename(local_path)
    actual_stage_path = f"{stage_path}/{filename}.gz"
    db = os.environ.get("SNOWFLAKE_DATABASE", "FINANCE_DATA_DB")

    print(f"  PUT {local_path} → @FINANCE_STAGE/{stage_path}")
    cursor.execute(f"""
        PUT file://{local_path}
        @FINANCE_STAGE/{stage_path}
        AUTO_COMPRESS=TRUE OVERWRITE=TRUE
    """)

    print(f"  COPY INTO {db}.RAW.{table_name} FROM @FINANCE_STAGE/{actual_stage_path}")
    cursor.execute(f"""
        COPY INTO {db}.RAW.{table_name}
        FROM '@"{db}"."RAW"."FINANCE_STAGE"/{actual_stage_path}'
        FILE_FORMAT = (
            TYPE                         = 'CSV'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            SKIP_HEADER                  = 1
            NULL_IF                      = ('', 'None', 'NULL')
            EMPTY_FIELD_AS_NULL          = TRUE
        )
        ON_ERROR = 'ABORT_STATEMENT'
    """)

    results = cursor.fetchall()
    for row in results:
        print(f"    → {row}")


def run_full(conn):
    base = os.path.join(os.environ.get("OUTPUT_PATH", "./data"), "full_load")
    cursor = conn.cursor()

    for table in FULL_LOAD_TABLES:
        path = os.path.join(base, f"{table}.csv")
        if not os.path.exists(path):
            print(f"  SKIP {table} (file not found)")
            continue
        # stage_path has no .csv — avoids DIM_DATE.csv/DIM_DATE.csv.gz duplication
        put_and_copy(cursor, os.path.abspath(path), f"full/{table}", table)

    cursor.close()
    print("Full load upload complete.")


def run_incremental(conn):
    base = os.path.join(os.environ.get("OUTPUT_PATH", "./data"), "incremental")
    today = date.today().strftime("%Y%m%d")
    inc_dir = os.path.join(base, today)
    if not os.path.exists(inc_dir):
        print(f"No incremental dir found for {today}. Exiting.")
        return
    cursor = conn.cursor()

    # These are straight INSERT files — full schema, load directly
    insert_tables = [
        ("FACT_INVOICE_HEADER_new",    "FACT_INVOICE_HEADER"),
        ("FACT_INVOICE_LINE_ITEM_new", "FACT_INVOICE_LINE_ITEM"),
        ("FACT_PAYMENT_B2B_B2D_new",   "FACT_PAYMENT_B2B_B2D"),
        ("FACT_PAYMENT_B2C_new",       "FACT_PAYMENT_B2C"),
        ("FACT_RETURNS_new",           "FACT_RETURNS"),
    ]

    for (file_stem, target_table) in insert_tables:
        path = os.path.join(inc_dir, f"{file_stem}.csv")
        if not os.path.exists(path):
            print(f"  SKIP {file_stem} (not generated today)")
            continue
        put_and_copy(cursor, os.path.abspath(path),
                     f"incremental/{today}/{file_stem}.csv", target_table)

    # Updates file — partial columns, use a temp table + MERGE
    updates_path = os.path.join(inc_dir, "FACT_INVOICE_HEADER_updates.csv")
    if os.path.exists(updates_path):
        print("  Processing FACT_INVOICE_HEADER_updates...")
        stage_file = f"incremental/{today}/FACT_INVOICE_HEADER_updates.csv"

        # PUT the file to stage
        cursor.execute(f"""
            PUT file://{os.path.abspath(updates_path)}
            @FINANCE_STAGE/{stage_file}
            AUTO_COMPRESS=TRUE OVERWRITE=TRUE
        """)

        # Create temp table with only the update columns
        cursor.execute("""
            CREATE OR REPLACE TEMPORARY TABLE RAW.FACT_INVOICE_HEADER_UPDATES_TEMP (
                invoice_key     NUMBER,
                invoice_id      VARCHAR,
                customer_key    NUMBER,
                payment_status  VARCHAR,
                net_payment     FLOAT,
                updated_date    DATE
            )
        """)

        # Load into temp table
        cursor.execute(f"""
            COPY INTO RAW.FACT_INVOICE_HEADER_UPDATES_TEMP
            FROM @FINANCE_STAGE/{stage_file}.gz
            FILE_FORMAT = (
                TYPE = 'CSV'
                FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                SKIP_HEADER = 1
                NULL_IF = ('', 'None', 'NULL')
                EMPTY_FIELD_AS_NULL = TRUE
            )
            PURGE = TRUE
            ON_ERROR = 'SKIP_FILE'
        """)

        # MERGE updates into main table
        cursor.execute("""
            MERGE INTO RAW.FACT_INVOICE_HEADER AS target
            USING RAW.FACT_INVOICE_HEADER_UPDATES_TEMP AS source
            ON target.invoice_key = source.invoice_key
            WHEN MATCHED THEN UPDATE SET
                target.payment_status = source.payment_status,
                target.net_payment    = source.net_payment
        """)
        print("  ✅ FACT_INVOICE_HEADER updates merged.")

    cursor.close()
    print("Incremental upload complete.")

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
