import os
import glob
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


def get_csv_columns(local_path: str):
    """Read header row from CSV to get column names in order."""
    with open(local_path, encoding="utf-8") as f:
        header = f.readline().strip()
    return [col.strip().strip('"') for col in header.split(",")]


def put_and_copy(cursor, local_path: str, stage_file: str, table_name: str):
    # Read column order from the CSV header
    csv_cols = get_csv_columns(local_path)
    col_list = ", ".join(csv_cols)

    print(f"  PUT {local_path} → @FINANCE_STAGE/{stage_file}")
    cursor.execute(f"""
        PUT file://{local_path}
        @FINANCE_STAGE/{stage_file}
        AUTO_COMPRESS=TRUE OVERWRITE=TRUE
    """)

    print(f"  COPY INTO {table_name} ({col_list})")
    cursor.execute(f"""
        COPY INTO RAW.{table_name} ({col_list})
        FROM (
            SELECT {", ".join(f"$${i+1}" for i in range(len(csv_cols)))}
            FROM @FINANCE_STAGE/{stage_file}.gz
        )
        FILE_FORMAT = (
            TYPE = 'CSV'
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
            SKIP_HEADER = 1
            NULL_IF = ('', 'None', 'NULL')
        )
        ON_ERROR = 'ABORT_STATEMENT'
    """)

    # Print copy results
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
        put_and_copy(cursor, os.path.abspath(path), f"full/{table}.csv", table)
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
    for (file_stem, target_table) in INCREMENTAL_TABLES:
        path = os.path.join(inc_dir, f"{file_stem}.csv")
        if not os.path.exists(path):
            print(f"  SKIP {file_stem} (not generated today)")
            continue
        put_and_copy(cursor, os.path.abspath(path),
                     f"incremental/{today}/{file_stem}.csv", target_table)
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
