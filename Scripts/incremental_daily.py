"""
================================================================================
Financial Data Warehouse - INCREMENTAL DAILY GENERATOR v2.2
Compatible with full_Load.py v6.0
State stored in Snowflake (PIPELINE_CHECKPOINT + OPEN_INVOICES_STATE)
================================================================================
"""

try:
    from state_manager import (
        save_checkpoint, load_checkpoint,
        save_open_invoices, load_open_invoices
    )
    USE_SNOWFLAKE_STATE = True
except ImportError:
    USE_SNOWFLAKE_STATE = False

import csv
import json
import os
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
import logging
import argparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# PATHS
# ============================================================================
BASE_PATH         = os.getenv('OUTPUT_PATH', './data')
STATE_DIR         = os.path.join(BASE_PATH, 'state')
FULL_LOAD_DIR     = os.path.join(BASE_PATH, 'full_load')
INCREMENTAL_DIR   = os.path.join(BASE_PATH, 'incremental')
CHECKPOINT_FILE   = os.path.join(STATE_DIR, 'checkpoint.json')
OPEN_INVOICES_FILE = os.path.join(STATE_DIR, 'open_invoices.json')

PAYMENT_MODES = {
    'B2B': ['NEFT', 'RTGS', 'IMPS', 'Cheque', 'Bank Transfer'],
    'B2D': ['NEFT', 'IMPS', 'Cash', 'UPI', 'Bank Transfer'],
    'B2C': ['Cash', 'UPI', 'Card', 'Wallet', 'Net Banking'],
}


# ============================================================================
# UTILITIES
# ============================================================================

def fmt_date(d: Optional[date]) -> Optional[str]:
    return d.strftime('%Y-%m-%d') if d else None


def parse_date(s: Optional[str]) -> Optional[date]:
    return date.fromisoformat(s) if s else None


def save_json(obj, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=2, default=str)


def load_json(path: str):
    with open(path) as f:
        return json.load(f)


def save_csv(rows: List[Dict], path: str):
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    logger.info(f"  Saved {len(rows):,} rows → {path}")


def load_csv(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as f:
        return list(csv.DictReader(f))


# ============================================================================
# CHECKPOINT
# ============================================================================

class Checkpoint:
    def __init__(self):
        self.last_run_date: Optional[date] = None
        self.sequences: Dict[str, int] = defaultdict(int)
        self.customer_outstanding: Dict[int, float] = defaultdict(float)
        self.last_purchase: Dict[int, date] = {}
        self.date_key_map: Dict[str, int] = {}
        self.return_sequence: Dict[int, int] = defaultdict(int)

    def save(self):
        # ── FIX: payload is now correctly indented inside save() ──
        payload = {
            'last_run_date': fmt_date(self.last_run_date),
            'sequences': dict(self.sequences),
            'customer_outstanding': {str(k): v for k, v in self.customer_outstanding.items()},
            'last_purchase': {str(k): fmt_date(v) for k, v in self.last_purchase.items()},
            'date_key_map': self.date_key_map,
            'return_sequence': dict(self.return_sequence),
        }
        # Save locally as backup
        save_json(payload, CHECKPOINT_FILE)
        # Save to Snowflake as primary state
        if USE_SNOWFLAKE_STATE:
            save_checkpoint(payload)

    @classmethod
    def load(cls) -> 'Checkpoint':
        cp = cls()

        # Try Snowflake state first
        if USE_SNOWFLAKE_STATE:
            try:
                raw = load_checkpoint()
                logger.info("  Loaded checkpoint from Snowflake")
            except Exception as e:
                logger.warning(f"  Snowflake checkpoint load failed: {e}. Trying local file...")
                raw = None
        else:
            raw = None

        # Fall back to local file
        # ✅ FIXED — graceful first-run handling
        if raw is None:
            if os.path.exists(CHECKPOINT_FILE):
                raw = load_json(CHECKPOINT_FILE)
                logger.info("  Loaded checkpoint from local file")
            else:
                # First run — no checkpoint anywhere, return empty state
                logger.warning("  No checkpoint found anywhere — fresh start (first run)")
                return cp   # cp.__init__ already sets safe defaults

        cp.last_run_date     = parse_date(raw.get('last_run_date'))
        cp.sequences         = defaultdict(int, {k: int(v) for k, v in raw.get('sequences', {}).items()})
        cp.customer_outstanding = defaultdict(float, {int(k): float(v) for k, v in raw.get('customer_outstanding', {}).items()})
        cp.last_purchase     = {int(k): date.fromisoformat(v) for k, v in raw.get('last_purchase', {}).items() if v}
        cp.date_key_map      = {k: int(v) for k, v in raw.get('date_key_map', {}).items()}
        cp.return_sequence   = defaultdict(int, {int(k): int(v) for k, v in raw.get('return_sequence', {}).items()})
        return cp

    def next_seq(self, name: str) -> int:
        self.sequences[name] += 1
        return self.sequences[name]

    def next_return_seq(self, invoice_key: int) -> int:
        self.return_sequence[invoice_key] += 1
        return self.return_sequence[invoice_key]

    # ✅ FIXED
    def get_date_key(self, d: date) -> int:
        if not self.date_key_map:
            logger.warning(f"  date_key_map is empty — using 0 as fallback key for {d}")
            return 0   # safe fallback; will be correct after full load populates it
        key = d.isoformat()
        if key in self.date_key_map:
            return self.date_key_map[key]
        closest = min(self.date_key_map.keys(), key=lambda x: abs((date.fromisoformat(x) - d).days))
        return self.date_key_map[closest]


# ============================================================================
# OPEN INVOICE STORE
# ============================================================================

class OpenInvoiceStore:
    def __init__(self):
        self._invoices: Dict[int, Dict] = {}

    def add(self, rec: Dict):
        self._invoices[rec['invoice_key']] = rec

    def all(self) -> List[Dict]:
        return list(self._invoices.values())

    def remove(self, invoice_key: int):
        self._invoices.pop(invoice_key, None)

    def update(self, invoice_key: int, paid_amount: float):
        if invoice_key in self._invoices:
            self._invoices[invoice_key]['paid_so_far']       += paid_amount
            self._invoices[invoice_key]['remaining_balance'] -= paid_amount

    def get(self, invoice_key: int) -> Optional[Dict]:
        return self._invoices.get(invoice_key)

    def save(self):
        # Save locally as backup
        save_json(self.all(), OPEN_INVOICES_FILE)
        # Save to Snowflake as primary state
        if USE_SNOWFLAKE_STATE:
            save_open_invoices(self.all())

    @classmethod
    def load(cls) -> 'OpenInvoiceStore':
        store = cls()

        # Try Snowflake first
        if USE_SNOWFLAKE_STATE:
            try:
                invoices = load_open_invoices()
                for rec in invoices:
                    store._invoices[rec['invoice_key']] = rec
                logger.info(f"  Loaded {len(store._invoices)} open invoices from Snowflake")
                return store
            except Exception as e:
                logger.warning(f"  Snowflake open invoices load failed: {e}. Trying local file...")

        # Fall back to local file
        if os.path.exists(OPEN_INVOICES_FILE):
            for rec in load_json(OPEN_INVOICES_FILE):
                store._invoices[rec['invoice_key']] = rec
            logger.info(f"  Loaded {len(store._invoices)} open invoices from local file")

        return store


# ============================================================================
# PAYMENT SIMULATOR
# ============================================================================

class PaymentSimulator:
    @staticmethod
    def simulate(inv: Dict, today: date) -> Optional[float]:
        due_date  = parse_date(inv['due_date'])
        habit     = inv['payment_habit']
        remaining = inv['remaining_balance']

        if remaining <= 0.01:
            return None

        days_since_due = (today - due_date).days

        if habit == 'on_time':
            if 0 <= days_since_due <= 5:
                if random.random() < 0.20:
                    return remaining
        elif habit == 'early':
            days_before_due = (due_date - today).days
            if 5 <= days_before_due <= 10:
                if random.random() < 0.14:
                    return remaining
        elif habit == 'mild_late':
            if 6 <= days_since_due <= 15:
                if random.random() < 0.10:
                    return remaining if random.random() < 0.85 else round(remaining * random.uniform(0.5, 0.8), 2)
        elif habit == 'moderate_late':
            if 16 <= days_since_due <= 30:
                if random.random() < 0.067:
                    return remaining if random.random() < 0.70 else round(remaining * random.uniform(0.3, 0.6), 2)
        elif habit == 'severe_late':
            if 31 <= days_since_due <= 60:
                if random.random() < 0.033:
                    if random.random() < 0.50:
                        return remaining
        elif habit == 'unpaid':
            if 45 <= days_since_due <= 90:
                if random.random() < 0.005:
                    if random.random() < 0.30:
                        return round(remaining * random.uniform(0.3, 0.7), 2)
        return None


# ============================================================================
# RETURN SIMULATOR
# ============================================================================

class ReturnSimulator:
    @staticmethod
    def should_return(invoice_amount: float, customer_type: str, days_since_invoice: int) -> bool:
        base_prob = {'B2C': 0.03, 'B2D': 0.02}.get(customer_type, 0.01)
        if invoice_amount > 100000:
            base_prob *= 1.5
        elif invoice_amount > 50000:
            base_prob *= 1.2
        if days_since_invoice <= 7:
            base_prob *= 2.0
        elif days_since_invoice <= 14:
            base_prob *= 1.5
        return random.random() < base_prob

    @staticmethod
    def calculate_return_amount(invoice_amount: float, paid_amount: float) -> float:
        if paid_amount <= 0:
            return 0.0
        if random.random() < 0.7:
            return min(invoice_amount, paid_amount)
        return round(paid_amount * random.uniform(0.2, 0.8), 2)


# ============================================================================
# DAILY RUNNER
# ============================================================================

class DailyRunner:
    def __init__(
        self,
        customers,
        products,
        stores,
        employees,
        locations,
        credit_policies,
        credit_mappings,
        run_date=None,
    ):
        self.customers       = customers
        self.products        = products
        self.stores          = stores
        self.employees       = employees
        self.locations       = locations
        self.credit_policies = credit_policies
        self.credit_mappings = credit_mappings
        self.run_date        = run_date or date.today()

        self.cp    = Checkpoint.load()
        self.store = OpenInvoiceStore.load()
        self._build_lookups()

    def _build_lookups(self):
        self.customer_map    = {int(c['customer_key']): c for c in self.customers}
        self.product_map     = {int(p['product_key']): p for p in self.products}
        self.product_list    = self.products
        self.store_map       = {int(s['store_key']): s for s in self.stores}
        self.store_id_map    = {int(s['store_key']): s['store_id'] for s in self.stores}
        self.store_list      = self.stores
        self.loc_state       = {int(l['location_key']): l['state'] for l in self.locations}
        self.store_loc       = {int(s['store_key']): int(s['location_key']) for s in self.stores}

        self.employees_by_loc: Dict[int, List[Dict]] = defaultdict(list)
        for e in self.employees:
            self.employees_by_loc[int(e['location_key'])].append(e)

        self.policy_map = {int(p['credit_policy_key']): p for p in self.credit_policies}

        self.cust_policy: Dict[int, Dict] = {}
        for m in self.credit_mappings:
            if str(m.get('is_current', 'True')).lower() in ('true', '1', 'yes'):
                ckey = int(m['customer_key'])
                pkey = int(m['credit_policy_key'])
                if pkey in self.policy_map:
                    self.cust_policy[ckey] = self.policy_map[pkey]

        CATEGORY_MAPPING = {
            'Electronics Retail':  ['Electronics'],
            'Grocery Wholesale':   ['Grocery', 'Dairy', 'Beverages', 'Snacks'],
            'Restaurant Supply':   ['Grocery', 'Dairy', 'Beverages', 'Snacks', 'Home Care'],
            'Pharmacy':            ['Personal Care'],
            'Hardware':            ['Home Care', 'Electronics'],
            'General Merchandise': ['Electronics', 'Grocery', 'Personal Care', 'Home Care'],
            'Kirana Store':        ['Grocery', 'Dairy', 'Beverages', 'Snacks', 'Personal Care'],
            'Mobile Shop':         ['Electronics'],
            'General Store':       ['Grocery', 'Dairy', 'Beverages', 'Snacks', 'Personal Care', 'Home Care'],
            'Electronics Outlet':  ['Electronics'],
            'Provisions Store':    ['Grocery', 'Dairy', 'Beverages', 'Snacks'],
        }

        self.cust_behavior: Dict[int, Dict] = {}
        for c in self.customers:
            ckey = int(c['customer_key'])
            bcat = c.get('business_category')
            self.cust_behavior[ckey] = {
                'payment_habit':     c.get('payment_habit', 'on_time'),
                'bulk_preference':   c.get('bulk_preference', 'medium'),
                'loyalty_tier':      c.get('loyalty_tier', 'regular'),
                'business_category': bcat,
                'allowed_categories': CATEGORY_MAPPING.get(bcat) if bcat else None,
                'customer_type':     c.get('customer_type'),
            }

        self.by_type: Dict[str, List[Dict]] = defaultdict(list)
        for c in self.customers:
            self.by_type[c['customer_type']].append(c)

        self.cust_primary_store: Dict[int, Optional[int]] = {}
        for c in self.customers:
            ckey  = int(c['customer_key'])
            ctype = c['customer_type']
            cstate = c.get('state', 'Gujarat')
            if ctype in ('B2B', 'B2D'):
                pool = [s for s in self.stores if self.loc_state.get(self.store_loc.get(int(s['store_key']))) == cstate]
                rng  = random.Random(ckey)
                self.cust_primary_store[ckey] = int(rng.choice(pool if pool else self.stores)['store_key'])
            else:
                self.cust_primary_store[ckey] = None

    def run(self):
        today = self.run_date
        logger.info("=" * 60)
        logger.info(f"DAILY RUN - {today}")
        logger.info(f"  Last run: {self.cp.last_run_date}")
        logger.info(f"  Open invoices: {len(self.store.all()):,}")
        logger.info("=" * 60)

        new_invoices  = []
        new_line_items = []
        updated_invoices = []
        pay_b2b_b2d   = []
        pay_b2c       = []
        returns       = []

        # Step 1: Settle old invoices & generate returns
        logger.info("Step 1: Settling open invoices & processing returns...")
        settled_keys = []

        for inv in self.store.all():
            pay_amount = PaymentSimulator.simulate(inv, today)
            if pay_amount is not None and pay_amount > 0:
                pay_amount = round(min(pay_amount, inv['remaining_balance']), 2)
                ckey  = int(inv['customer_key'])
                ctype = inv['customer_type']

                pkey     = self.cp.next_seq('payment')
                date_key = self.cp.get_date_key(today)

                pay_rec = {
                    'payment_key':            pkey,
                    'payment_id':             f"PAY_{pkey:010d}",
                    'invoice_key':            inv['invoice_key'],
                    'customer_key':           ckey,
                    'payment_date':           fmt_date(today),
                    'payment_date_key':       date_key,
                    'payment_amount':         pay_amount,
                    'payment_mode':           random.choice(PAYMENT_MODES.get(ctype, ['NEFT'])),
                    'bank_reference_number':  f"UTR{random.randint(100000000, 999999999)}",
                    'bank_account_number':    f"ACC{random.randint(10000000000, 99999999999)}",
                    'settlement_status':      'Settled',
                    'channel_type':           ctype,
                    'is_refund':              False,
                    'refund_amount':          0.0,
                    'refund_date_key':        None,
                    'remarks':                f"Payment for invoice {inv['invoice_id']}",
                }

                if ctype in ('B2B', 'B2D'):
                    pay_rec['enterprise_payment_key'] = pkey
                    pay_b2b_b2d.append(pay_rec)
                    self.cp.customer_outstanding[ckey] = max(0.0, self.cp.customer_outstanding[ckey] - pay_amount)
                else:
                    pay_rec['retail_payment_key'] = pkey
                    pay_rec['store_key']          = inv.get('store_key')
                    pay_rec['store_id']           = inv.get('store_id')
                    pay_b2c.append(pay_rec)

                self.store.update(inv['invoice_key'], pay_amount)
                new_remaining = inv['remaining_balance'] - pay_amount
                new_status    = 'Paid' if new_remaining <= 0.01 else 'Partially Paid'

                if new_remaining <= 0.01:
                    settled_keys.append(inv['invoice_key'])

                updated_invoices.append({
                    'invoice_key':    inv['invoice_key'],
                    'invoice_id':     inv['invoice_id'],
                    'customer_key':   ckey,
                    'payment_status': new_status,
                    'net_payment':    round(inv['paid_so_far'] + pay_amount, 2),
                    'updated_date':   fmt_date(today),
                })

            # Process returns
            inv_date          = parse_date(inv['invoice_date'])
            days_since_invoice = (today - inv_date).days
            paid_so_far       = inv['paid_so_far']

            if ReturnSimulator.should_return(inv['original_amount'], inv['customer_type'], days_since_invoice):
                return_amount = ReturnSimulator.calculate_return_amount(inv['original_amount'], paid_so_far)
                if return_amount > 0:
                    return_key = self.cp.next_seq('return')
                    date_key   = self.cp.get_date_key(today)
                    returns.append({
                        'return_key':    return_key,
                        'return_id':     f"RET_{return_key:010d}",
                        'invoice_key':   inv['invoice_key'],
                        'customer_key':  inv['customer_key'],
                        'return_date':   fmt_date(today),
                        'return_date_key': date_key,
                        'return_amount': return_amount,
                        'return_reason': random.choice(['Damaged', 'Wrong Item', 'Quality Issue', 'Expired', 'Customer Request']),
                        'return_status': 'Approved',
                        'refund_processed': return_amount <= paid_so_far,
                        'channel_type':  inv['customer_type'],
                        'store_key':     inv.get('store_key'),
                        'store_id':      inv.get('store_id'),
                        'remarks':       f"Return for invoice {inv['invoice_id']}",
                    })
                    if inv['customer_type'] in ('B2B', 'B2D'):
                        self.cp.customer_outstanding[int(inv['customer_key'])] = max(
                            0.0, self.cp.customer_outstanding[int(inv['customer_key'])] - return_amount)

        for k in settled_keys:
            self.store.remove(k)

        logger.info(f"  Payments: {len(pay_b2b_b2d) + len(pay_b2c):,}")
        logger.info(f"  Settled:  {len(settled_keys):,}")
        logger.info(f"  Returns:  {len(returns):,}")
        logger.info(f"  Remaining open: {len(self.store.all()):,}")

        # Step 2: Generate new invoices
        logger.info("Step 2: Generating today's new invoices...")
        new_invoices, new_line_items, new_pays_b2b, new_pays_b2c = self._gen_todays_invoices(today)
        pay_b2b_b2d.extend(new_pays_b2b)
        pay_b2c.extend(new_pays_b2c)

        # Step 3: Save CSVs
        out_dir = os.path.join(INCREMENTAL_DIR, today.strftime('%Y%m%d'))
        save_csv(new_invoices,    os.path.join(out_dir, 'FACT_INVOICE_HEADER_new.csv'))
        save_csv(new_line_items,  os.path.join(out_dir, 'FACT_INVOICE_LINE_ITEM_new.csv'))
        save_csv(updated_invoices, os.path.join(out_dir, 'FACT_INVOICE_HEADER_updates.csv'))
        save_csv(pay_b2b_b2d,     os.path.join(out_dir, 'FACT_PAYMENT_B2B_B2D_new.csv'))
        save_csv(pay_b2c,         os.path.join(out_dir, 'FACT_PAYMENT_B2C_new.csv'))
        save_csv(returns,         os.path.join(out_dir, 'FACT_RETURNS_new.csv'))

        # Step 4: Update state (Snowflake + local backup)
        self.cp.last_run_date = today
        self.cp.save()
        self.store.save()

        logger.info("=" * 60)
        logger.info(f"Daily run complete for {today}")
        logger.info(f"  New invoices:   {len(new_invoices):,}")
        logger.info(f"  New line items: {len(new_line_items):,}")
        logger.info(f"  Updates:        {len(updated_invoices):,}")
        logger.info(f"  Payments:       {len(pay_b2b_b2d) + len(pay_b2c):,}")
        logger.info(f"  Returns:        {len(returns):,}")
        logger.info("=" * 60)

    def _gen_todays_invoices(self, today: date):
        new_invoices    = []
        new_line_items  = []
        pays_b2b        = []
        pays_b2c        = []

        NATIONAL_HOLIDAYS = {'01-26', '08-15', '10-02', '01-01', '12-25'}
        is_sunday   = today.weekday() == 6
        is_holiday  = today.strftime('%m-%d') in NATIONAL_HOLIDAYS

        INVOICES_DAILY = {'B2B': (8, 20), 'B2D': (10, 25), 'B2C': (80, 200)}
        BULK_QTY = {
            'B2B': {'small': [10, 25], 'medium': [25, 50], 'large': [50, 100], 'extreme': [100, 250]},
            'B2D': {'small': [5, 10],  'medium': [10, 20], 'large': [20, 50],  'extreme': [50, 100]},
            'B2C': {'small': [1],      'medium': [1, 2],   'large': [2, 3],    'extreme': [3, 5]},
        }
        MIN_INV = {'B2B': 5000, 'B2D': 25000, 'B2C': 50}

        def seasonal_mult(d: date) -> float:
            m, day = d.month, d.day
            if (m == 10 and day >= 15) or (m == 11 and day <= 15): return 2.5
            if day >= 25: return 1.5
            if m == 1 and day <= 5: return 1.8
            return 1.0

        seas = seasonal_mult(today)
        line_item_key_counter = self.cp.sequences.get('line_item', 0)

        for ctype, count_range in INVOICES_DAILY.items():
            hol_red = 0.3 if is_holiday else 1.0
            sun_red = 0.2 if (is_sunday and ctype in ('B2B', 'B2D')) else 1.0
            count   = max(1, int(random.randint(*count_range) * seas * hol_red * sun_red))
            pool    = self.by_type.get(ctype, [])
            if not pool:
                continue

            for _ in range(count):
                c    = random.choice(pool)
                ckey = int(c['customer_key'])
                beh  = self.cust_behavior.get(ckey, {})
                loy  = beh.get('loyalty_tier', 'regular')
                bulk = beh.get('bulk_preference', 'medium')

                last = self.cp.last_purchase.get(ckey)
                if last:
                    freq = self._purchase_freq(ctype, bulk, loy)
                    if (today - last).days < max(1, int(freq * 0.7)):
                        continue

                policy = self.cust_policy.get(ckey)
                if policy and ctype in ('B2B', 'B2D'):
                    if str(policy.get('block_on_exceed', 'True')).lower() in ('true', '1'):
                        if self.cp.customer_outstanding.get(ckey, 0.0) >= float(policy.get('credit_limit_amount', 0)):
                            continue

                pstore_key = self.cust_primary_store.get(ckey)
                store = (self.store_map.get(pstore_key, random.choice(self.store_list))
                         if pstore_key and random.random() < 0.8
                         else random.choice(self.store_list))

                store_key     = int(store['store_key'])
                store_loc_key = self.store_loc.get(store_key, 1)
                store_state   = self.loc_state.get(store_loc_key, 'Gujarat')
                cust_state    = c.get('state', 'Gujarat')
                is_interstate = cust_state != store_state

                emp_pool  = self.employees_by_loc.get(store_loc_key, self.employees)
                employee  = random.choice(emp_pool) if emp_pool else {'user_key': 1}

                credit_days = 0
                if ctype in ('B2B', 'B2D') and policy:
                    credit_days = int(policy.get('credit_days_limit', 30))
                    if loy == 'vip':      credit_days += 15
                    elif loy == 'premium': credit_days += 7
                due_date = today + timedelta(days=credit_days)

                inv_key      = self.cp.next_seq('invoice')
                inv_number   = f"INV-{today.strftime('%Y%m%d')}-{inv_key:06d}"
                inv_date_key = self.cp.get_date_key(today)
                due_date_key = self.cp.get_date_key(min(due_date, date.today()))

                allowed_cats = beh.get('allowed_categories')
                prod_pool = ([p for p in self.product_list if p['category'] in allowed_cats]
                             if allowed_cats and ctype in ('B2B', 'B2D') else self.product_list[:])
                if not prod_pool:
                    prod_pool = self.product_list[:]

                n_items = (
                    random.randint(3, 10) if (ctype == 'B2B' and bulk in ('large', 'extreme'))
                    else random.randint(2, 7) if ctype == 'B2B'
                    else random.randint(4, 12) if (ctype == 'B2D' and bulk in ('large', 'extreme'))
                    else random.randint(3, 8)  if ctype == 'B2D'
                    else random.randint(1, 4)
                )
                n_items   = min(n_items, len(prod_pool))
                sel_prods = random.sample(prod_pool, n_items) if n_items > 0 else []

                invoice = {
                    'invoice_key':                   inv_key,
                    'invoice_id':                    inv_number,
                    'customer_key':                  ckey,
                    'customer_type':                 ctype,
                    'invoice_date':                  fmt_date(today),
                    'invoice_date_key':              inv_date_key,
                    'due_date':                      fmt_date(due_date),
                    'due_date_key':                  due_date_key,
                    'total_taxable_amount':          0.0,
                    'total_cgst_amount':             0.0,
                    'total_sgst_amount':             0.0,
                    'total_igst_amount':             0.0,
                    'total_tax_amount':              0.0,
                    'total_gross_amount':            0.0,
                    'total_discount_amount':         0.0,
                    'discount_percentage':           0.0,
                    'total_invoice_amount_incl_gst': 0.0,
                    'net_payment':                   0.0,
                    'invoice_status':                'Posted',
                    'payment_status':                'Unpaid',
                    'customer_gst_number':           c.get('gst_no'),
                    'location_key':                  store_loc_key,
                    'user_key':                      int(employee.get('user_key', 1)),
                    'store_key':                     store_key,
                    'is_interstate':                 is_interstate,
                    'store_state':                   store_state,
                }

                total_gross = 0.0
                total_disc  = 0.0
                line_items_for_invoice = []

                for prod in sel_prods:
                    prod_key  = int(prod['product_key'])
                    qty_opts  = BULK_QTY.get(ctype, {}).get(bulk, [1, 2])
                    qty       = random.choice(qty_opts)
                    unit_price = float(prod.get('selling_price', 100))
                    gross_line = round(qty * unit_price, 2)

                    bands = (
                        [(5,10,0.55),(10,15,0.30),(15,20,0.12),(20,25,0.03)] if ctype == 'B2B'
                        else [(3,7,0.50),(7,12,0.30),(12,18,0.15),(18,25,0.05)] if ctype == 'B2D'
                        else [(0,2,0.60),(2,5,0.30),(5,8,0.08),(8,12,0.02)]
                    )
                    r, cum, disc_pct = random.random(), 0.0, bands[0][0]
                    for lo, hi, prob in bands:
                        cum += prob
                        if r <= cum:
                            disc_pct = random.uniform(lo, hi)
                            break
                    disc_pct += {'small':0,'medium':2,'large':5,'extreme':8}.get(bulk, 0)
                    disc_pct += {'new':0,'regular':1,'premium':3,'vip':5}.get(loy, 0)
                    disc_pct  = min(disc_pct, 30.0)

                    disc_amt     = round(gross_line * disc_pct / 100, 2)
                    taxable_line = round(gross_line - disc_amt, 2)
                    cgst_p = float(prod.get('cgst_percent', 9))
                    sgst_p = float(prod.get('sgst_percent', 9))
                    igst_p = float(prod.get('igst_percent', 18))

                    if is_interstate:
                        cgst_a, sgst_a = 0.0, 0.0
                        igst_a = round(taxable_line * igst_p / 100, 2)
                    else:
                        cgst_a = round(taxable_line * cgst_p / 100, 2)
                        sgst_a = round(taxable_line * sgst_p / 100, 2)
                        igst_a = 0.0

                    tax_a    = cgst_a + sgst_a + igst_a
                    line_tot = taxable_line + tax_a

                    line_item_key_counter += 1
                    line_items_for_invoice.append({
                        'line_item_key':     line_item_key_counter,
                        'invoice_key':       inv_key,
                        'product_key':       prod_key,
                        'quantity':          qty,
                        'unit_price':        unit_price,
                        'gross_amount':      gross_line,
                        'discount_percentage': round(disc_pct, 2),
                        'discount_amount':   disc_amt,
                        'taxable_amount':    taxable_line,
                        'cgst_percent':      cgst_p if not is_interstate else 0,
                        'cgst_amount':       cgst_a,
                        'sgst_percent':      sgst_p if not is_interstate else 0,
                        'sgst_amount':       sgst_a,
                        'igst_percent':      igst_p if is_interstate else 0,
                        'igst_amount':       igst_a,
                        'total_tax_amount':  tax_a,
                        'line_total_amount': round(line_tot, 2),
                    })

                    total_gross += gross_line
                    total_disc  += disc_amt
                    invoice['total_taxable_amount']          += taxable_line
                    invoice['total_cgst_amount']             += cgst_a
                    invoice['total_sgst_amount']             += sgst_a
                    invoice['total_igst_amount']             += igst_a
                    invoice['total_tax_amount']              += tax_a
                    invoice['total_invoice_amount_incl_gst'] += line_tot

                for k in ('total_taxable_amount','total_cgst_amount','total_sgst_amount',
                          'total_igst_amount','total_tax_amount','total_invoice_amount_incl_gst'):
                    invoice[k] = round(invoice[k], 2)
                invoice['total_gross_amount']    = round(total_gross, 2)
                invoice['total_discount_amount'] = round(total_disc, 2)
                if total_gross > 0:
                    invoice['discount_percentage'] = round((total_disc / total_gross) * 100, 4)

                min_val = MIN_INV.get(ctype, 0)
                if invoice['total_invoice_amount_incl_gst'] < min_val:
                    sf = max(1.5, min_val / max(invoice['total_invoice_amount_incl_gst'], 0.01))
                    for field in ('total_taxable_amount','total_cgst_amount','total_sgst_amount',
                                  'total_igst_amount','total_tax_amount','total_invoice_amount_incl_gst',
                                  'total_gross_amount','total_discount_amount'):
                        invoice[field] = round(invoice[field] * sf, 2)
                    for li in line_items_for_invoice:
                        for field in ['gross_amount','discount_amount','taxable_amount',
                                      'cgst_amount','sgst_amount','igst_amount',
                                      'total_tax_amount','line_total_amount']:
                            li[field] = round(li[field] * sf, 2)

                inv_total = invoice['total_invoice_amount_incl_gst']
                new_line_items.extend(line_items_for_invoice)

                if ctype == 'B2C':
                    invoice['payment_status'] = 'Paid'
                    invoice['net_payment']    = inv_total
                    pkey     = self.cp.next_seq('payment')
                    date_key = self.cp.get_date_key(today)
                    pays_b2c.append({
                        'payment_key':           pkey,
                        'payment_id':            f"PAY_{pkey:010d}",
                        'invoice_key':           inv_key,
                        'customer_key':          ckey,
                        'payment_date':          fmt_date(today),
                        'payment_date_key':      date_key,
                        'payment_amount':        round(inv_total, 2),
                        'payment_mode':          random.choice(PAYMENT_MODES['B2C']),
                        'bank_reference_number': f"UTR{random.randint(100000000, 999999999)}",
                        'bank_account_number':   f"ACC{random.randint(10000000000, 99999999999)}",
                        'settlement_status':     'Settled',
                        'channel_type':          'B2C',
                        'is_refund':             False,
                        'refund_amount':         0.0,
                        'refund_date_key':       None,
                        'remarks':               None,
                        'retail_payment_key':    pkey,
                        'store_key':             store_key,
                        'store_id':              self.store_id_map.get(store_key),
                    })
                else:
                    self.cp.customer_outstanding[ckey] = self.cp.customer_outstanding.get(ckey, 0.0) + inv_total
                    self.store.add({
                        'invoice_key':       inv_key,
                        'invoice_id':        inv_number,
                        'customer_key':      ckey,
                        'customer_type':     ctype,
                        'invoice_date':      fmt_date(today),
                        'due_date':          fmt_date(due_date),
                        'original_amount':   inv_total,
                        'paid_so_far':       0.0,
                        'remaining_balance': inv_total,
                        'payment_habit':     beh.get('payment_habit', 'on_time'),
                        'store_key':         store_key,
                        'store_id':          self.store_id_map.get(store_key),
                    })

                new_invoices.append(invoice)
                self.cp.last_purchase[ckey] = today

        self.cp.sequences['line_item'] = line_item_key_counter
        return new_invoices, new_line_items, pays_b2b, pays_b2c

    @staticmethod
    def _purchase_freq(ctype: str, bulk: str, loyalty: str) -> int:
        if ctype == 'B2B':
            base = random.choice([15, 20, 25, 30])
            return max(1, int(base * 0.8)) if bulk in ('large', 'extreme') else base
        elif ctype == 'B2D':
            base = random.choice([7, 10, 14])
            return max(1, int(base * 0.7)) if bulk in ('large', 'extreme') else base
        else:
            base = random.choice([3, 5, 7, 10, 14])
            return max(1, int(base * 0.8)) if loyalty in ('premium', 'vip') else base


# ============================================================================
# BACKFILL RUNNER
# ============================================================================

class BackfillRunner:
    def __init__(self, *args, **kwargs):
        self._args   = args
        self._kwargs = kwargs

    def run(self):
        cp = Checkpoint.load()
        if cp.last_run_date is None:
            raise RuntimeError("No last_run_date. Run full load first.")
        today    = date.today()
        run_from = cp.last_run_date + timedelta(days=1)
        if run_from > today:
            logger.info("Already up to date.")
            return
        current = run_from
        while current <= today:
            logger.info(f"\n{'─'*60}\nBackfill: {current}")
            dr = DailyRunner(*self._args, **self._kwargs, run_date=current)
            dr.run()
            current += timedelta(days=1)


# ============================================================================
# LOAD DIMENSIONS
# ============================================================================

def load_dimensions(full_load_dir: str = FULL_LOAD_DIR) -> Dict:
    tables = ['DIM_CUSTOMERS','DIM_PRODUCTS','DIM_STORE','DIM_USER',
              'DIM_LOCATION','CREDIT_POLICY','CUSTOMER_CREDIT_MAPPING']
    result = {}
    for t in tables:
        path = os.path.join(full_load_dir, f'{t}.csv')
        if os.path.exists(path):
            result[t] = load_csv(path)
            logger.info(f"  Loaded {t}: {len(result[t]):,} rows")
        else:
            logger.warning(f"  {t}.csv not found")
            result[t] = []
    return result


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Incremental Generator v2.2')
    parser.add_argument('--mode', choices=['full', 'daily', 'backfill'], default='daily')
    parser.add_argument('--date', default=None, help='Run date (YYYY-MM-DD)')
    parser.add_argument('--full-load-dir', default=FULL_LOAD_DIR)
    args = parser.parse_args()

    if args.mode == 'full':
        try:
            from full_Load import FinancialDataGenerator
        except ImportError:
            logger.error("Could not import FinancialDataGenerator from full_Load.py")
            return
        FinancialDataGenerator().generate()
    else:
        dims     = load_dimensions(args.full_load_dir)
        run_date = date.fromisoformat(args.date) if args.date else None
        kwargs   = dict(
            customers      = dims.get('DIM_CUSTOMERS', []),
            products       = dims.get('DIM_PRODUCTS', []),
            stores         = dims.get('DIM_STORE', []),
            employees      = dims.get('DIM_USER', []),
            locations      = dims.get('DIM_LOCATION', []),
            credit_policies = dims.get('CREDIT_POLICY', []),
            credit_mappings = dims.get('CUSTOMER_CREDIT_MAPPING', []),
        )
        if args.mode == 'daily':
            if run_date:
                kwargs['run_date'] = run_date
            DailyRunner(**kwargs).run()
        elif args.mode == 'backfill':
            BackfillRunner(**kwargs).run()


if __name__ == '__main__':
    main()
