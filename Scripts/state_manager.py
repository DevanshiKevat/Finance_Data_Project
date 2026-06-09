"""
State Manager - Saves/loads pipeline state to/from Snowflake
Tables: PIPELINE_CHECKPOINT, OPEN_INVOICES_STATE (in RAW schema)
"""

import json
import os
from datetime import datetime
import snowflake.connector

_DB     = "FINANCE_DATA_DB"
_SCHEMA = "RAW"
CHECKPOINT_TABLE    = f"{_DB}.{_SCHEMA}.PIPELINE_CHECKPOINT"
OPEN_INVOICES_TABLE = f"{_DB}.{_SCHEMA}.OPEN_INVOICES_STATE"


def get_conn():
    org     = os.environ["SNOWFLAKE_ORGANIZATION"]
    account = os.environ["SNOWFLAKE_ACCOUNT"]
    return snowflake.connector.connect(
        account   = f"{org}-{account}".lower(),
        user      = os.environ["SNOWFLAKE_USER"],
        password  = os.environ["SNOWFLAKE_PASSWORD"],
        warehouse = os.environ.get("SNOWFLAKE_WAREHOUSE", "FINANCE_WH"),
        database  = os.environ.get("SNOWFLAKE_DATABASE", "FINANCE_DATA_DB"),
        schema    = "RAW",
    )


def save_checkpoint(checkpoint_dict: dict):
    """Upsert checkpoint — UPDATE first, INSERT if no row exists."""
    conn   = get_conn()
    cursor = conn.cursor()
    now    = datetime.utcnow()
    json_str = json.dumps(checkpoint_dict)
    try:
        # Try UPDATE first
        cursor.execute(f"""
            UPDATE {CHECKPOINT_TABLE}
            SET    CHECKPOINT_VALUE = PARSE_JSON(%s),
                   UPDATED_AT       = %s
            WHERE  CHECKPOINT_KEY = 'main'
        """, (json_str, now))

        # If no rows matched, INSERT
        if cursor.rowcount == 0:
            cursor.execute(f"""
                INSERT INTO {CHECKPOINT_TABLE}
                    (CHECKPOINT_KEY, CHECKPOINT_VALUE, UPDATED_AT)
                VALUES ('main', PARSE_JSON(%s), %s)
            """, (json_str, now))

        print("✅ Checkpoint saved to Snowflake")
    except Exception as e:
        print(f"❌ save_checkpoint failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def load_checkpoint() -> dict | None:
    """
    Load checkpoint from Snowflake.
    Returns None on first run (empty table) — caller handles gracefully.
    """
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            SELECT CHECKPOINT_VALUE
            FROM   {CHECKPOINT_TABLE}
            WHERE  CHECKPOINT_KEY = 'main'
        """)
        row = cursor.fetchone()
    except Exception as e:
        print(f"⚠️  Snowflake checkpoint query failed: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

    if not row or row[0] is None:
        print("ℹ️  No checkpoint found — first run detected.")
        return None

    return json.loads(row[0])


def save_open_invoices(invoices: list):
    """Replace all open invoices state in Snowflake."""
    conn   = get_conn()
    cursor = conn.cursor()
    now    = datetime.utcnow()
    try:
        cursor.execute(f"DELETE FROM {OPEN_INVOICES_TABLE}")

        if invoices:
            values = [
                (
                    inv['invoice_key'],
                    inv['invoice_id'],
                    inv['customer_key'],
                    inv['customer_type'],
                    inv['invoice_date'],
                    inv['due_date'],
                    inv['original_amount'],
                    inv['paid_so_far'],
                    inv['remaining_balance'],
                    inv['payment_habit'],
                    inv.get('store_key'),
                    inv.get('store_id'),
                    inv.get('store_state'),
                    now,
                )
                for inv in invoices
            ]
            cursor.executemany(f"""
                INSERT INTO {OPEN_INVOICES_TABLE} (
                    INVOICE_KEY, INVOICE_ID, CUSTOMER_KEY, CUSTOMER_TYPE,
                    INVOICE_DATE, DUE_DATE, ORIGINAL_AMOUNT, PAID_SO_FAR,
                    REMAINING_BALANCE, PAYMENT_HABIT, STORE_KEY, STORE_ID,
                    STORE_STATE, UPDATED_AT
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, values)

        print(f"✅ Open invoices saved to Snowflake ({len(invoices)} records)")
    except Exception as e:
        print(f"❌ save_open_invoices failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def load_open_invoices() -> list:
    """Load all open invoices from Snowflake."""
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(f"""
            SELECT INVOICE_KEY, INVOICE_ID, CUSTOMER_KEY, CUSTOMER_TYPE,
                   INVOICE_DATE, DUE_DATE, ORIGINAL_AMOUNT, PAID_SO_FAR,
                   REMAINING_BALANCE, PAYMENT_HABIT, STORE_KEY, STORE_ID,
                   STORE_STATE
            FROM   {OPEN_INVOICES_TABLE}
        """)
        rows = cursor.fetchall()
    except Exception as e:
        print(f"❌ load_open_invoices failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

    cols = [
        'invoice_key', 'invoice_id', 'customer_key', 'customer_type',
        'invoice_date', 'due_date', 'original_amount', 'paid_so_far',
        'remaining_balance', 'payment_habit', 'store_key', 'store_id', 'store_state',
    ]

    result = []
    for row in rows:
        rec = dict(zip(cols, row))
        for f in ('invoice_date', 'due_date'):
            if rec[f]:
                rec[f] = str(rec[f])
        result.append(rec)

    print(f"✅ Loaded {len(result)} open invoices from Snowflake")
    return result
