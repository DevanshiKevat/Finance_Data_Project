"""
State Manager - Saves/loads pipeline state to/from Snowflake
Tables: PIPELINE_CHECKPOINT, OPEN_INVOICES_STATE (in RAW schema)
"""

import json
import os
from datetime import datetime
import snowflake.connector


def get_conn():
    org     = os.environ["SNOWFLAKE_ORGANIZATION"]
    account = os.environ["SNOWFLAKE_ACCOUNT"]
    return snowflake.connector.connect(
        account=f"{org}-{account}".lower(),
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "FINANCE_WH"),
        database=os.environ.get("SNOWFLAKE_DATABASE", "FINANCE_DATA_DB"),
        schema="RAW",
    )


def save_checkpoint(checkpoint_dict: dict):
    """Upsert checkpoint into Snowflake PIPELINE_CHECKPOINT table"""
    conn   = get_conn()
    cursor = conn.cursor()
    now    = datetime.utcnow()
    cursor.execute("""
        MERGE INTO RAW.PIPELINE_CHECKPOINT AS target
        USING (
            SELECT %s AS checkpoint_key,
                   PARSE_JSON(%s) AS checkpoint_value,
                   %s AS updated_at
        ) AS source
        ON target.checkpoint_key = source.checkpoint_key
        WHEN MATCHED THEN UPDATE SET
            target.checkpoint_value = source.checkpoint_value,
            target.updated_at       = source.updated_at
        WHEN NOT MATCHED THEN INSERT
            (checkpoint_key, checkpoint_value, updated_at)
            VALUES (source.checkpoint_key, source.checkpoint_value, source.updated_at)
    """, ('main', json.dumps(checkpoint_dict), now))
    cursor.close()
    conn.close()
    print("✅ Checkpoint saved to Snowflake")


def load_checkpoint() -> dict | None:
    """
    Load checkpoint dict from Snowflake.
    Returns None on first run (empty table) so caller can handle gracefully.
    """
    conn   = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT checkpoint_value
            FROM FINANCE_DATA_DB.RAW.PIPELINE_CHECKPOINT
            WHERE checkpoint_key = 'main'
        """)
        row = cursor.fetchone()
    except Exception as e:
        print(f"⚠️  Snowflake checkpoint query failed: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

    if not row or row[0] is None:
        print("ℹ️  No checkpoint found — first run detected. Starting from scratch.")
        return None                    # ← caller decides what to do

    return json.loads(row[0])

def save_open_invoices(invoices: list):
    """Replace all open invoices state in Snowflake"""
    conn   = get_conn()
    cursor = conn.cursor()
    now    = datetime.utcnow()

    cursor.execute("DELETE FROM RAW.OPEN_INVOICES_STATE")

    if invoices:
        values = []
        for inv in invoices:
            values.append((
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
            ))
        cursor.executemany("""
            INSERT INTO RAW.OPEN_INVOICES_STATE (
                invoice_key, invoice_id, customer_key, customer_type,
                invoice_date, due_date, original_amount, paid_so_far,
                remaining_balance, payment_habit, store_key, store_id,
                store_state, updated_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, values)

    cursor.close()
    conn.close()
    print(f"✅ Open invoices saved to Snowflake ({len(invoices)} records)")


def load_open_invoices() -> list:
    """Load all open invoices from Snowflake"""
    conn   = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT invoice_key, invoice_id, customer_key, customer_type,
               invoice_date, due_date, original_amount, paid_so_far,
               remaining_balance, payment_habit, store_key, store_id, store_state
        FROM RAW.OPEN_INVOICES_STATE
    """)
    rows = cursor.fetchall()
    cols = ['invoice_key','invoice_id','customer_key','customer_type',
            'invoice_date','due_date','original_amount','paid_so_far',
            'remaining_balance','payment_habit','store_key','store_id','store_state']
    cursor.close()
    conn.close()

    result = []
    for row in rows:
        rec = dict(zip(cols, row))
        for f in ('invoice_date', 'due_date'):
            if rec[f]:
                rec[f] = str(rec[f])
        result.append(rec)

    print(f"✅ Loaded {len(result)} open invoices from Snowflake")
    return result
