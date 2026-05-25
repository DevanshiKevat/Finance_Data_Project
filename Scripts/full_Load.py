"""
Financial Data Warehouse Generation Script - RAW Layer
Version 5.0 - Fixed All Data Gaps (Arithmetic + Temporal + GST)
"""

import csv
import json
import os
import random
import string
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from decimal import Decimal, ROUND_HALF_UP
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    TODAY            = date.today()
    HISTORICAL_DAYS  = 730
    START_DATE       = TODAY - timedelta(days=HISTORICAL_DAYS)
    OUTPUT_BASE_PATH = os.getenv('OUTPUT_PATH', './data')
    STATE_DIR        = os.path.join(OUTPUT_BASE_PATH, 'state')
    RANDOM_SEED      = 42
    COMPANY_STATE    = "Gujarat"

    VOLUME = {
        'regions':                5,
        'employees_per_location': (3, 8),
        'stores':                 50,
        'products':               50,
        'customers_initial': {
            'B2B': 300,
            'B2D': 200,
            'B2C': 2000,
        },
        'invoices_daily': {
            'B2B': (8, 20),
            'B2D': (10, 25),
            'B2C': (80, 200),
        },
    }

    RETURN_CONFIG = {
        'b2c_return_probability': 0.08,
        'b2b_return_probability': 0.02,
        'b2d_return_probability': 0.02,
        'category_return_multipliers': {
            'Electronics':   1.8, 'Grocery': 0.4, 'Dairy': 0.5,
            'Beverages':     0.6, 'Snacks':  0.7,
            'Personal Care': 1.2, 'Home Care': 1.1,
        },
        'category_return_reasons': {
            'Electronics': {
                'Damaged/Defective': 0.55, 'Wrong Product': 0.25,
                'Change of Mind': 0.15, 'Other': 0.05,
            },
            'Grocery': {
                'Expired Product': 0.45, 'Damaged/Defective': 0.25,
                'Change of Mind': 0.20, 'Other': 0.10,
            },
            'default': {
                'Change of Mind': 0.40, 'Wrong Product': 0.25,
                'Damaged/Defective': 0.20, 'Other': 0.15,
            },
        },
    }


# ============================================================================
# REFERENCE DATA (Same as before)
# ============================================================================

INDIAN_STATES = [
    "Gujarat", "Maharashtra", "Rajasthan", "Delhi", "Karnataka",
    "Tamil Nadu", "Uttar Pradesh", "West Bengal", "Telangana", "Madhya Pradesh",
    "Punjab", "Haryana", "Kerala", "Bihar", "Odisha",
]

CITIES_BY_STATE = {
    "Gujarat":        ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar", "Bhavnagar"],
    "Maharashtra":    ["Mumbai", "Pune", "Nagpur", "Nashik", "Thane", "Aurangabad"],
    "Rajasthan":      ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer", "Bikaner"],
    "Delhi":          ["New Delhi", "Dwarka", "Rohini", "Janakpuri", "Saket", "Lajpat Nagar"],
    "Karnataka":      ["Bengaluru", "Mysuru", "Hubli", "Mangaluru", "Belagavi", "Gulbarga"],
    "Tamil Nadu":     ["Chennai", "Coimbatore", "Madurai", "Salem", "Tirunelveli", "Tiruchirappalli"],
    "Uttar Pradesh":  ["Lucknow", "Kanpur", "Agra", "Varanasi", "Prayagraj", "Meerut"],
    "West Bengal":    ["Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri", "Kharagpur"],
    "Telangana":      ["Hyderabad", "Warangal", "Karimnagar", "Nizamabad", "Khammam", "Mahabubnagar"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain", "Sagar"],
    "Punjab":         ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Mohali"],
    "Haryana":        ["Gurgaon", "Faridabad", "Panipat", "Ambala", "Hisar", "Karnal"],
    "Kerala":         ["Kochi", "Thiruvananthapuram", "Kozhikode", "Thrissur", "Kollam", "Palakkad"],
    "Bihar":          ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga", "Arrah"],
    "Odisha":         ["Bhubaneswar", "Cuttack", "Rourkela", "Sambalpur", "Brahmapur", "Puri"],
}

REGION_STATES_MAP = {
    "West India Region":    ["Gujarat", "Maharashtra", "Rajasthan"],
    "North India Region":   ["Delhi", "Punjab", "Haryana", "Uttar Pradesh"],
    "South India Region":   ["Karnataka", "Tamil Nadu", "Telangana", "Kerala"],
    "East India Region":    ["West Bengal", "Bihar", "Odisha"],
    "Central India Region": ["Madhya Pradesh"],
}

REGIONAL_MANAGERS = {
    "West India Region":    "Rajesh Mehta",
    "North India Region":   "Amit Sharma",
    "South India Region":   "Priya Reddy",
    "East India Region":    "Sudipta Chatterjee",
    "Central India Region": "Vikram Singh",
}

PRODUCT_CATALOG = [
    ("Smartphone 128GB",      "Electronics",   "851713", 18, 9.0, 9.0, 18.0, 15000, 25000),
    ("Laptop i5",             "Electronics",   "847130", 18, 9.0, 9.0, 18.0, 35000, 55000),
    ("Wireless Headphones",   "Electronics",   "851830", 18, 9.0, 9.0, 18.0,  1500,  2999),
    ("Smart Watch",           "Electronics",   "910212", 18, 9.0, 9.0, 18.0,  2000,  4500),
    ("Power Bank 20000mAh",   "Electronics",   "850760", 18, 9.0, 9.0, 18.0,  1200,  2499),
    ("Tablet 10 inch",        "Electronics",   "847190", 18, 9.0, 9.0, 18.0, 12000, 22000),
    ("Basmati Rice 5kg",      "Grocery",       "100630",  5, 2.5, 2.5,  5.0,   250,   400),
    ("Wheat Flour 5kg",       "Grocery",       "110100",  5, 2.5, 2.5,  5.0,   150,   250),
    ("Sugar 1kg",             "Grocery",       "170114",  5, 2.5, 2.5,  5.0,    35,    55),
    ("Cooking Oil 1L",        "Grocery",       "151211",  5, 2.5, 2.5,  5.0,   100,   160),
    ("Toor Dal 1kg",          "Grocery",       "071340",  5, 2.5, 2.5,  5.0,    90,   140),
    ("Salt 1kg",              "Grocery",       "250100",  0, 0.0, 0.0,  0.0,    10,    20),
    ("Tea 250g",              "Grocery",       "090240",  5, 2.5, 2.5,  5.0,    80,   150),
    ("Coffee 50g",            "Grocery",       "090121", 12, 6.0, 6.0, 12.0,   120,   220),
    ("Fresh Milk 1L",         "Dairy",         "040120",  5, 2.5, 2.5,  5.0,    40,    60),
    ("Greek Yogurt 400g",     "Dairy",         "040310",  5, 2.5, 2.5,  5.0,    60,   100),
    ("Butter 100g",           "Dairy",         "040510", 12, 6.0, 6.0, 12.0,    40,    65),
    ("Paneer 200g",           "Dairy",         "040610",  5, 2.5, 2.5,  5.0,    70,   110),
    ("Soft Drink 2L",         "Beverages",     "220210", 28,14.0,14.0, 28.0,    60,    99),
    ("Fruit Juice 1L",        "Beverages",     "200990", 12, 6.0, 6.0, 12.0,    80,   130),
    ("Energy Drink 250ml",    "Beverages",     "220210", 28,14.0,14.0, 28.0,    50,    85),
    ("Mineral Water 1L",      "Beverages",     "220110",  0, 0.0, 0.0,  0.0,    15,    25),
    ("Potato Chips 100g",     "Snacks",        "190590", 18, 9.0, 9.0, 18.0,    15,    30),
    ("Biscuits 200g",         "Snacks",        "190531",  5, 2.5, 2.5,  5.0,    20,    40),
    ("Instant Noodles 70g",   "Snacks",        "190230", 18, 9.0, 9.0, 18.0,    10,    20),
    ("Shampoo 200ml",         "Personal Care", "330510", 18, 9.0, 9.0, 18.0,   150,   280),
    ("Soap Pack 100g",        "Personal Care", "340111", 18, 9.0, 9.0, 18.0,    80,   150),
    ("Toothpaste 150g",       "Personal Care", "330610", 18, 9.0, 9.0, 18.0,    60,   110),
    ("Face Wash 100ml",       "Personal Care", "340130", 18, 9.0, 9.0, 18.0,   100,   180),
    ("Body Lotion 300ml",     "Personal Care", "330499", 18, 9.0, 9.0, 18.0,   150,   280),
    ("Deodorant 150ml",       "Personal Care", "330720", 28,14.0,14.0, 28.0,   120,   220),
    ("Detergent Powder 1kg",  "Home Care",     "340220", 18, 9.0, 9.0, 18.0,    80,   150),
    ("Dishwash Liquid 500ml", "Home Care",     "340220", 18, 9.0, 9.0, 18.0,    50,    95),
    ("Floor Cleaner 1L",      "Home Care",     "340290", 18, 9.0, 9.0, 18.0,    60,   110),
    ("Toilet Cleaner 500ml",  "Home Care",     "340290", 18, 9.0, 9.0, 18.0,    55,    90),
]

DESIGNATIONS = [
    "Sales Executive", "Sales Manager", "Billing Executive", "Billing Manager",
    "Store Manager", "Regional Manager", "Finance Manager", "Customer Support Manager",
    "Operations Manager", "Warehouse Manager", "Procurement Executive",
]

DEPARTMENT_MAP = {
    "Sales Executive":          "Sales",
    "Sales Manager":            "Sales",
    "Billing Executive":        "Billing",
    "Billing Manager":          "Billing",
    "Store Manager":            "Operations",
    "Regional Manager":         "Operations",
    "Finance Manager":          "Finance",
    "Customer Support Manager": "Customer Service",
    "Operations Manager":       "Operations",
    "Warehouse Manager":        "Operations",
    "Procurement Executive":    "Procurement",
}

PAYMENT_MODES = {
    'B2B': ['NEFT', 'RTGS', 'IMPS', 'Cheque', 'Bank Transfer'],
    'B2D': ['NEFT', 'IMPS', 'Cash', 'UPI', 'Bank Transfer'],
    'B2C': ['Cash', 'UPI', 'Card', 'Wallet', 'Net Banking'],
}

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

STATE_GST_CODES = {
    "Gujarat": "24", "Maharashtra": "27", "Rajasthan": "08",
    "Delhi": "07", "Karnataka": "29", "Tamil Nadu": "33",
    "Uttar Pradesh": "09", "West Bengal": "19", "Telangana": "36",
    "Madhya Pradesh": "23", "Punjab": "03", "Haryana": "06",
    "Kerala": "32", "Bihar": "10", "Odisha": "21",
}

NATIONAL_HOLIDAYS = {'01-26', '08-15', '10-02', '01-01', '12-25'}


# ============================================================================
# FINANCIAL CALCULATION HELPER (CRITICAL FIX)
# ============================================================================

class FinancialCalculator:
    """Precise financial calculations using Decimal"""
    
    @staticmethod
    def calculate_tax(amount: float, rate: float) -> float:
        """Calculate tax with proper rounding"""
        if rate == 0:
            return 0.0
        d_amount = Decimal(str(amount))
        d_rate = Decimal(str(rate))
        result = (d_amount * d_rate / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return float(result)
    
    @staticmethod
    def calculate_discount(amount: float, percent: float) -> float:
        """Calculate discount with proper rounding"""
        if percent == 0:
            return 0.0
        d_amount = Decimal(str(amount))
        d_percent = Decimal(str(percent))
        result = (d_amount * d_percent / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return float(result)
    
    @staticmethod
    def sum_line_items(line_items: List[Dict], field: str) -> float:
        """Sum line item values precisely"""
        total = Decimal('0')
        for li in line_items:
            value = li.get(field, 0)
            if value is not None:
                total += Decimal(str(value))
        return float(total)


# ============================================================================
# HELPERS
# ============================================================================

def random_date(start: date, end: date) -> date:
    if start >= end:
        return start
    return start + timedelta(days=random.randint(0, (end - start).days))


def fmt_date(d: Optional[date]) -> Optional[str]:
    return d.strftime('%Y-%m-%d') if d else None


def fmt_dt(dt: datetime) -> str:
    return dt.isoformat()


def generate_gstin(state: str, seq: int) -> str:
    code = STATE_GST_CODES.get(state, "24")
    pan  = ''.join(random.choices(string.ascii_uppercase, k=5))
    pan += ''.join(random.choices(string.digits, k=4))
    pan += random.choice(string.ascii_uppercase)
    entity = f"{seq % 999 + 1:03d}"
    check  = random.randint(0, 9)
    return f"{code}{pan}{entity}{check}"


def generate_name() -> str:
    first = ["Aarav","Vihaan","Ananya","Advik","Kabir","Arjun","Reyansh","Rohan",
             "Krishna","Aryan","Shaurya","Ved","Ayaan","Diya","Ishaan","Myra",
             "Aadhya","Pari","Sai","Jiya","Nikhil","Priya","Rahul","Sneha",
             "Vikram","Neha","Amit","Pooja","Suresh","Deepa"]
    last  = ["Sharma","Verma","Patel","Gupta","Kumar","Singh","Reddy","Joshi",
             "Mehta","Shah","Agarwal","Desai","Rao","Nair","Iyer","Pillai",
             "Chowdhury","Bhatt","Malhotra","Kapoor"]
    return f"{random.choice(first)} {random.choice(last)}"


def generate_company_name(ctype: str, bcat: str = None) -> str:
    prefixes = ["Shree","Laxmi","Om","Jay","Sai","Balaji","Ganesh","Maa","Baba","Sri"]
    cores = {
        'Electronics Retail':  ["Digital","Electronics","Mobiles","Gadgets","Tech"],
        'Grocery Wholesale':   ["Traders","Suppliers","Mart","Bazaar","Wholesale"],
        'Restaurant Supply':   ["Caterers","Food Supply","Restaurant Services","Kitchen"],
        'Pharmacy':            ["Medicos","Pharmacy","Drugs","HealthCare","Medical"],
        'Hardware':            ["Hardware","Tools","Construction","Build Mart"],
        'General Merchandise': ["Stores","General","Traders","Enterprises"],
        'Kirana Store':        ["Kirana","General Store","Provision","Daily Need"],
        'Mobile Shop':         ["Mobiles","Phone Point","Communication","Digital Hub"],
        'General Store':       ["General Store","Mart","Provision","Stores"],
        'Electronics Outlet':  ["Electronics","Digital","Gadgets","Tech Hub"],
        'Provisions Store':    ["Provisions","Grocery","Mart","Bazaar"],
        'default':             ["Traders","Enterprises","Distributors","Suppliers","Mart"],
    }
    suffixes = {
        'B2B': ["Pvt Ltd","Ltd","Corporation","Enterprises","Industries","Group"],
        'B2D': ["Franchise","Outlet","Store","Express","Hub","Point"],
    }
    core = random.choice(cores.get(bcat, cores['default']))
    suf  = random.choice(suffixes.get(ctype, ["Company"]))
    return f"{random.choice(prefixes)} {core} {suf}"


def seasonal_multiplier(d: date) -> float:
    m, day = d.month, d.day
    if (m == 10 and day >= 15) or (m == 11 and day <= 15): return 2.5
    if day >= 25:                                           return 1.5
    if m == 1 and day <= 5:                                 return 1.8
    if (m == 8 and day in range(10, 16)) or (m == 1 and day in [24, 25, 26]): return 2.0
    return 1.0


def save_csv(data: List[Dict], filepath: str):
    if not data:
        logger.warning(f"No data for {filepath}")
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        w.writeheader()
        w.writerows(data)
    logger.info(f"  Saved {len(data):,} rows → {filepath}")


# ============================================================================
# MAIN GENERATOR
# ============================================================================

class FinancialDataGenerator:

    def __init__(self):
        random.seed(Config.RANDOM_SEED)
        self.calc = FinancialCalculator()

        self.data: Dict[str, List[Dict]] = {
            'DIM_DATE':                  [],
            'DIM_REGION':                [],
            'DIM_LOCATION':              [],
            'DIM_EMPLOYEE':              [],
            'DIM_PRODUCTS':              [],
            'DIM_CUSTOMERS':             [],
            'DIM_STORE':                 [],
            'CREDIT_POLICY':             [],
            'CUSTOMER_CREDIT_MAPPING':   [],
            'FACT_INVOICE_HEADER':       [],
            'FACT_INVOICE_LINE_ITEM':    [],
            'FACT_PAYMENT_B2B_B2D':      [],
            'FACT_PAYMENT_B2C':          [],
            'FACT_RETURNS':              [],
        }

        # Caches
        self.date_keys:          Dict[date, int]         = {}
        self.regions:            List[Dict]               = []
        self.location_cache:     List[Dict]               = []
        self.employee_cache:     List[Dict]               = []
        self.customer_cache:     List[Dict]               = []
        self.policy_cache:       List[Dict]               = []
        self.stores:             List[Dict]               = []
        self.customer_locations: Dict[int, Dict]          = {}
        self.customer_behavior:  Dict[int, Dict]          = {}
        self.location_map:       Dict[int, Dict]          = {}

        # Credit tracking
        self.customer_outstanding: Dict[int, float] = defaultdict(float)

        # Employee lookup by location
        self.employees_by_location: Dict[int, List[Dict]] = defaultdict(list)

        # Last purchase date per customer
        self.last_purchase_dates: Dict[int, date] = {}

        # State to region mapping
        self.state_to_region_key: Dict[str, int] = {}

        self.seq = defaultdict(int)

    def _next(self, name: str) -> int:
        self.seq[name] += 1
        return self.seq[name]

    # -------------------------------------------------------------------------
    # DIMENSIONS
    # -------------------------------------------------------------------------

    def gen_dim_date(self):
        cur = Config.START_DATE
        while cur <= Config.TODAY:
            key = self._next('date')
            self.date_keys[cur] = key
            self.data['DIM_DATE'].append({
                'date_key':    key,
                'full_date':   fmt_date(cur),
                'year':        cur.year,
                'quarter':     (cur.month - 1) // 3 + 1,
                'month':       cur.month,
                'month_name':  cur.strftime('%B'),
                'day':         cur.day,
                'day_of_week': cur.weekday() + 1,
                'day_name':    cur.strftime('%A'),
                'is_weekend':  cur.weekday() >= 5,
                'is_holiday':  cur.strftime('%m-%d') in NATIONAL_HOLIDAYS,
            })
            cur += timedelta(days=1)
        logger.info(f"DIM_DATE: {len(self.data['DIM_DATE'])} rows")

    def gen_dim_region(self):
        region_names = list(REGION_STATES_MAP.keys())
        
        for i, region_name in enumerate(region_names[:Config.VOLUME['regions']], 1):
            r = {
                'region_key':       i,
                'region_code':      f"REG_{i:03d}",
                'region_name':      region_name,
                'country_name':     'India',
                'regional_manager': REGIONAL_MANAGERS.get(region_name, generate_name()),
                'states_covered':   ', '.join(REGION_STATES_MAP.get(region_name, [])),
            }
            self.data['DIM_REGION'].append(r)
            self.regions.append(r)
            
            for state in REGION_STATES_MAP.get(region_name, []):
                self.state_to_region_key[state] = i
        
        # FIX: Ensure all states have region mapping
        for state in INDIAN_STATES:
            if state not in self.state_to_region_key:
                self.state_to_region_key[state] = 1
                logger.warning(f"State '{state}' had no region, assigned to region 1")
        
        logger.info(f"DIM_REGION: {len(self.data['DIM_REGION'])} rows")

    def gen_dim_location(self):
        for region in self.regions:
            region_name = region['region_name']
            states = REGION_STATES_MAP.get(region_name, [])
            for state in states:
                cities = CITIES_BY_STATE.get(state, [state])
                selected_cities = random.sample(cities, min(3, len(cities)))
                for city in selected_cities:
                    for ltype in ['Store', 'Warehouse']:
                        loc = {
                            'location_key':  self._next('location'),
                            'location_id':   f"LOC_{self.seq['location']:06d}",
                            'location_name': f"{city} {ltype}",
                            'location_type': ltype,
                            'address':       f"Plot {random.randint(1,999)}, {city}, {state}",
                            'city':          city,
                            'state':         state,
                            'region_key':    region['region_key'],
                            'manager_name':  generate_name(),
                        }
                        self.data['DIM_LOCATION'].append(loc)
                        self.location_cache.append(loc)
                        self.location_map[loc['location_key']] = loc
        
        stores_count = len([l for l in self.location_cache if l['location_type'] == 'Store'])
        logger.info(f"DIM_LOCATION: {len(self.data['DIM_LOCATION'])} rows (Stores: {stores_count})")

    def gen_dim_employee(self):
        for loc in self.location_cache:
            n = random.randint(*Config.VOLUME['employees_per_location'])
            for _ in range(n):
                desig = random.choice(DESIGNATIONS)
                emp = {
                    'user_key':          self._next('employee'),
                    'user_id':           f"EMP_{self.seq['employee']:06d}",
                    'employee_name':     generate_name(),
                    'designation':       desig,
                    'department':        DEPARTMENT_MAP.get(desig, 'Operations'),
                    'location_key':      loc['location_key'],
                    'reporting_manager': generate_name(),
                    'hire_date':         fmt_date(random_date(Config.START_DATE, Config.TODAY)),
                    'status':            'Active',
                }
                self.data['DIM_EMPLOYEE'].append(emp)
                self.employee_cache.append(emp)
                self.employees_by_location[loc['location_key']].append(emp)
        logger.info(f"DIM_EMPLOYEE: {len(self.data['DIM_EMPLOYEE'])} rows")

    def gen_dim_products(self):
        selected = random.sample(PRODUCT_CATALOG, min(Config.VOLUME['products'], len(PRODUCT_CATALOG)))
        for p in selected:
            name, cat, hsn, gst, cgst, sgst, igst, lo, hi = p
            prod = {
                'product_key':      self._next('product'),
                'product_id':       f"PROD_{self.seq['product']:06d}",
                'product_name':     name,
                'category':         cat,
                'hsn_code':         hsn,
                'gst_rate_percent': gst,
                'cgst_percent':     cgst,
                'sgst_percent':     sgst,
                'igst_percent':     igst,
                'cost_price':       round(random.uniform(lo * 0.6, lo * 0.8), 2),
                'selling_price':    round(random.uniform(lo, hi), 2),
                'base_price':       round(random.uniform(lo * 0.9, lo * 1.1), 2),
            }
            self.data['DIM_PRODUCTS'].append(prod)
        logger.info(f"DIM_PRODUCTS: {len(self.data['DIM_PRODUCTS'])} rows")

    def gen_dim_customers(self):
        PAYMENT_HABITS  = ['early', 'on_time', 'mild_late', 'moderate_late', 'severe_late', 'unpaid']
        PAYMENT_WEIGHTS = {
            'B2B': [0.08, 0.35, 0.22, 0.18, 0.12, 0.05],
            'B2D': [0.12, 0.45, 0.20, 0.12, 0.08, 0.03],
            'B2C': [0.00, 0.60, 0.20, 0.12, 0.06, 0.02],
        }
        BULK_PREFERENCES = ['small', 'medium', 'large', 'extreme']
        BULK_WEIGHTS = {
            'B2B': [0.05, 0.20, 0.45, 0.30],
            'B2D': [0.10, 0.35, 0.40, 0.15],
            'B2C': [0.60, 0.30, 0.08, 0.02],
        }
        LOYALTY_TIERS   = ['new', 'regular', 'premium', 'vip']
        LOYALTY_WEIGHTS = [0.30, 0.45, 0.18, 0.07]
        B2B_CATS = ['Electronics Retail','Grocery Wholesale','Restaurant Supply',
                    'Pharmacy','Hardware','General Merchandise']
        B2D_CATS = ['Kirana Store','Mobile Shop','General Store',
                    'Pharmacy','Electronics Outlet','Provisions Store']

        def _make_customer(ctype, i):
            if ctype == 'B2C' and random.random() < 0.7:
                state = Config.COMPANY_STATE
            else:
                state = random.choice(INDIAN_STATES)
            
            region_key = self.state_to_region_key.get(state, 1)
            region = next((r for r in self.regions if r['region_key'] == region_key), self.regions[0])
            city = random.choice(CITIES_BY_STATE.get(state, [state]))
            
            # FIX: Ensure onboarding date is NOT in the future
            max_onboard_date = Config.TODAY - timedelta(days=30)
            if Config.START_DATE >= max_onboard_date:
                max_onboard_date = Config.TODAY
            ondate = random_date(Config.START_DATE, max_onboard_date)

            habit   = random.choices(PAYMENT_HABITS,    weights=PAYMENT_WEIGHTS[ctype])[0]
            bulk    = random.choices(BULK_PREFERENCES,  weights=BULK_WEIGHTS[ctype])[0]
            loyalty = random.choices(LOYALTY_TIERS,     weights=LOYALTY_WEIGHTS)[0]
            bcat    = random.choice(B2B_CATS if ctype == 'B2B' else B2D_CATS) if ctype != 'B2C' else None
            days_old = (Config.TODAY - ondate).days

            churn = (
                round(random.uniform(0.01, 0.12), 2) if loyalty in ('vip', 'premium')
                else round(random.uniform(0.15, 0.45), 2) if days_old < 90
                else round(random.uniform(0.05, 0.25), 2)
            )

            key   = self._next('customer')
            cname = generate_company_name(ctype, bcat) if ctype != 'B2C' else generate_name()
            gstin = generate_gstin(state, key) if ctype != 'B2C' else None

            c = {
                'customer_key':      key,
                'customer_id':       f"CUST_{key:06d}",
                'customer_name':     cname,
                'customer_type':     ctype,
                'state':             state,
                'city':              city,
                'region_key':        region_key,
                'onboarding_date':   fmt_date(ondate),
                'status':            'Active',
                'gst_no':            gstin,
                'payment_habit':     habit,
                'bulk_preference':   bulk,
                'loyalty_tier':      loyalty,
                'business_category': bcat,
                'churn_risk':        churn,
                'credit_score':      random.randint(600, 900) if ctype != 'B2C' else None,
            }
            self.data['DIM_CUSTOMERS'].append(c)
            self.customer_cache.append(c)
            self.customer_locations[key] = {'state': state, 'city': city, 'gst_no': gstin}
            self.customer_behavior[key] = {
                'payment_habit':      habit,
                'bulk_preference':    bulk,
                'loyalty_tier':       loyalty,
                'business_category':  bcat,
                'allowed_categories': CATEGORY_MAPPING.get(bcat) if bcat else None,
            }

        for ctype, count in Config.VOLUME['customers_initial'].items():
            for i in range(count):
                _make_customer(ctype, i)

        logger.info(f"DIM_CUSTOMERS: {len(self.data['DIM_CUSTOMERS'])} rows")

    def gen_dim_store(self):
        store_locs = [l for l in self.location_cache if l['location_type'] == 'Store']
        selected_locs = random.sample(store_locs, min(Config.VOLUME['stores'], len(store_locs)))
        
        for loc in selected_locs:
            s = {
                'store_key':           self._next('store'),
                'store_id':            f"STR_{self.seq['store']:06d}",
                'store_name':          f"{loc['city']} Store",
                'location_key':        loc['location_key'],
                'gst_registration_no': generate_gstin(loc['state'], self.seq['store']),
                'opening_date':        fmt_date(random_date(Config.START_DATE, Config.TODAY)),
                'closing_date':        None,
                'store_manager':       generate_name(),
            }
            self.data['DIM_STORE'].append(s)
            self.stores.append(s)
        logger.info(f"DIM_STORE: {len(self.data['DIM_STORE'])} rows")

    def gen_credit_policy(self):
        policies = [
            {
                'credit_policy_key': 1, 'policy_code': 'POL_B2B_STD',
                'policy_name': 'Standard B2B Credit',
                'applicable_customer_type': 'B2B', 'credit_limit_amount': 500000.00,
                'credit_days_limit': 30, 'block_on_exceed': True,
                'block_on_overdue_days': 45, 'requires_deposit': True,
                'minimum_deposit_amount': 25000.00, 'approval_required': True,
                'start_date': fmt_date(Config.START_DATE), 'end_date': None,
            },
            {
                'credit_policy_key': 2, 'policy_code': 'POL_B2B_PRE',
                'policy_name': 'Premium B2B Credit',
                'applicable_customer_type': 'B2B', 'credit_limit_amount': 2000000.00,
                'credit_days_limit': 45, 'block_on_exceed': True,
                'block_on_overdue_days': 60, 'requires_deposit': True,
                'minimum_deposit_amount': 50000.00, 'approval_required': True,
                'start_date': fmt_date(Config.START_DATE), 'end_date': None,
            },
            {
                'credit_policy_key': 3, 'policy_code': 'POL_B2D_STD',
                'policy_name': 'Standard Franchise Credit',
                'applicable_customer_type': 'B2D', 'credit_limit_amount': 250000.00,
                'credit_days_limit': 30, 'block_on_exceed': True,
                'block_on_overdue_days': 45, 'requires_deposit': True,
                'minimum_deposit_amount': 15000.00, 'approval_required': True,
                'start_date': fmt_date(Config.START_DATE), 'end_date': None,
            },
            {
                'credit_policy_key': 4, 'policy_code': 'POL_B2D_PRE',
                'policy_name': 'Premium Franchise Credit',
                'applicable_customer_type': 'B2D', 'credit_limit_amount': 1000000.00,
                'credit_days_limit': 45, 'block_on_exceed': True,
                'block_on_overdue_days': 60, 'requires_deposit': True,
                'minimum_deposit_amount': 30000.00, 'approval_required': True,
                'start_date': fmt_date(Config.START_DATE), 'end_date': None,
            },
            {
                'credit_policy_key': 5, 'policy_code': 'POL_B2C_CASH',
                'policy_name': 'B2C Cash Policy',
                'applicable_customer_type': 'B2C', 'credit_limit_amount': 0.00,
                'credit_days_limit': 0, 'block_on_exceed': False,
                'block_on_overdue_days': 0, 'requires_deposit': False,
                'minimum_deposit_amount': 0.00, 'approval_required': False,
                'start_date': fmt_date(Config.START_DATE), 'end_date': None,
            },
        ]
        self.data['CREDIT_POLICY'] = policies
        self.policy_cache = policies
        logger.info(f"CREDIT_POLICY: {len(policies)} rows")

    def gen_customer_credit_mapping(self):
        pol_map = {p['policy_code']: p for p in self.policy_cache}

        def _pick_policy(ctype, score, loyalty):
            if ctype == 'B2C':
                return pol_map['POL_B2C_CASH']
            if ctype == 'B2B':
                return (pol_map['POL_B2B_PRE']
                        if (score or 0) >= 800 or loyalty in ('premium', 'vip')
                        else pol_map['POL_B2B_STD'])
            if ctype == 'B2D':
                return (pol_map['POL_B2D_PRE']
                        if (score or 0) >= 800 or loyalty in ('premium', 'vip')
                        else pol_map['POL_B2D_STD'])

        for c in self.customer_cache:
            pol = _pick_policy(c['customer_type'], c.get('credit_score'), c.get('loyalty_tier'))
            # FIX: Use onboarding date for effective_from, not a future date
            m = {
                'customer_credit_key': self._next('credit_mapping'),
                'customer_key':        c['customer_key'],
                'credit_policy_key':   pol['credit_policy_key'],
                'approval_status':     'Approved',
                'approved_by':         generate_name() if c['customer_type'] != 'B2C' else 'SYSTEM',
                'review_date':         c['onboarding_date'],  # FIX: Same as onboarding
                'effective_from':      c['onboarding_date'],
                'effective_to':        None,
                'is_current':          True,
            }
            self.data['CUSTOMER_CREDIT_MAPPING'].append(m)
        logger.info(f"CUSTOMER_CREDIT_MAPPING: {len(self.data['CUSTOMER_CREDIT_MAPPING'])} rows")

    # -------------------------------------------------------------------------
    # FACTS - CORRECTED VERSION
    # -------------------------------------------------------------------------

    def gen_fact_invoices_and_lineitems(self):
        products = self.data['DIM_PRODUCTS']
        loc_state = {l['location_key']: l['state'] for l in self.location_cache}
        store_loc = {s['store_key']: s['location_key'] for s in self.stores}

        cust_policy: Dict[int, Dict] = {}
        for m in self.data['CUSTOMER_CREDIT_MAPPING']:
            if m['is_current']:
                cust_policy[m['customer_key']] = next(
                    p for p in self.policy_cache
                    if p['credit_policy_key'] == m['credit_policy_key']
                )

        cust_primary_store: Dict[int, Optional[int]] = {}
        for c in self.customer_cache:
            ckey = c['customer_key']
            cstate = self.customer_locations[ckey]['state']
            if c['customer_type'] in ('B2B', 'B2D'):
                pool = [s for s in self.stores
                        if loc_state.get(store_loc.get(s['store_key'])) == cstate]
                if pool:
                    cust_primary_store[ckey] = random.choice(pool)['store_key']
                else:
                    cust_primary_store[ckey] = random.choice(self.stores)['store_key']
            else:
                cust_primary_store[ckey] = None

        purchase_freq: Dict[int, int] = {}
        for c in self.customer_cache:
            ckey = c['customer_key']
            beh = self.customer_behavior[ckey]
            bulk = beh['bulk_preference']
            loy = beh['loyalty_tier']
            if c['customer_type'] == 'B2B':
                base = random.choice([15, 20, 25, 30])
                base = int(base * 0.8) if bulk in ('large', 'extreme') else base
            elif c['customer_type'] == 'B2D':
                base = random.choice([7, 10, 14])
                base = int(base * 0.7) if bulk in ('large', 'extreme') else base
            else:
                base = random.choice([3, 5, 7, 10, 14])
                base = int(base * 0.8) if loy in ('premium', 'vip') else base
            purchase_freq[ckey] = max(1, base)

        last_purchase: Dict[int, Optional[date]] = {
            c['customer_key']: None for c in self.customer_cache
        }

        by_type: Dict[str, List[Dict]] = defaultdict(list)
        for c in self.customer_cache:
            by_type[c['customer_type']].append(c)

        BULK_QTY = {
            'B2B': {'small': [10, 25], 'medium': [25, 50], 'large': [50, 100], 'extreme': [100, 250]},
            'B2D': {'small': [5, 10], 'medium': [10, 20], 'large': [20, 50], 'extreme': [50, 100]},
            'B2C': {'small': [1], 'medium': [1, 2], 'large': [2, 3], 'extreme': [3, 5]},
        }
        MIN_INV = {'B2B': 5000, 'B2D': 25000, 'B2C': 50}

        cur = Config.START_DATE
        invoices_generated = 0
        customers_with_invoices = set()

        while cur <= Config.TODAY:
            days_ago = (Config.TODAY - cur).days
            scale = max(0.3, 1.0 - (days_ago / Config.HISTORICAL_DAYS) * 0.7)
            seas = seasonal_multiplier(cur)
            is_sunday = cur.weekday() == 6
            is_holiday = cur.strftime('%m-%d') in NATIONAL_HOLIDAYS

            for ctype, count_range in Config.VOLUME['invoices_daily'].items():
                hol_red = 0.3 if is_holiday else 1.0
                sun_red = 0.2 if (is_sunday and ctype in ('B2B', 'B2D')) else 1.0
                count = max(1, int(random.randint(*count_range) * scale * seas * hol_red * sun_red))
                pool = by_type[ctype]
                if not pool:
                    continue

                for _ in range(count):
                    c = random.choice(pool)
                    ckey = c['customer_key']
                    beh = self.customer_behavior[ckey]
                    loy = beh['loyalty_tier']
                    bulk = beh['bulk_preference']

                    last = last_purchase.get(ckey)
                    if last:
                        min_gap = max(1, int(purchase_freq[ckey] * 0.7))
                        if (cur - last).days < min_gap:
                            continue

                    policy = cust_policy.get(ckey)
                    if policy and ctype in ('B2B', 'B2D') and policy['block_on_exceed']:
                        if self.customer_outstanding[ckey] >= policy['credit_limit_amount']:
                            continue

                    pstore_key = cust_primary_store.get(ckey)
                    if pstore_key:
                        store = next((s for s in self.stores if s['store_key'] == pstore_key), None)
                        if not store:
                            store = random.choice(self.stores)
                    else:
                        store = random.choice(self.stores)

                    store_loc_key = store_loc[store['store_key']]
                    store_state = loc_state.get(store_loc_key, Config.COMPANY_STATE)
                    cust_state = self.customer_locations[ckey]['state']
                    is_interstate = cust_state != store_state

                    emp_pool = self.employees_by_location.get(store_loc_key) or self.employee_cache
                    employee = random.choice(emp_pool)

                    if ctype in ('B2B', 'B2D'):
                        credit_days = policy['credit_days_limit'] if policy else 30
                        if loy == 'vip':
                            credit_days += 15
                        elif loy == 'premium':
                            credit_days += 7
                        due_date = cur + timedelta(days=credit_days)
                    else:
                        due_date = cur

                    inv_key = self._next('invoice')
                    inv_number = f"INV-{cur.strftime('%Y%m%d')}-{inv_key:06d}"

                    inv_date_key = self.date_keys.get(cur, 1)
                    due_date_clamped = min(due_date, Config.TODAY)
                    due_date_key = self.date_keys.get(due_date_clamped,
                                                    self.date_keys.get(Config.TODAY, 1))

                    invoice = {
                        'invoice_key': inv_key,
                        'invoice_id': inv_number,
                        'customer_key': ckey,
                        'customer_type': ctype,
                        'invoice_date': fmt_date(cur),
                        'invoice_date_key': inv_date_key,
                        'due_date': fmt_date(due_date),
                        'due_date_key': due_date_key,
                        'payment_habit': beh['payment_habit'],
                        'total_taxable_amount': 0.0,
                        'total_cgst_amount': 0.0,
                        'total_sgst_amount': 0.0,
                        'total_igst_amount': 0.0,
                        'total_tax_amount': 0.0,
                        'total_gross_amount': 0.0,
                        'total_discount_amount': 0.0,
                        'discount_percentage': 0.0,
                        'total_invoice_amount_incl_gst': 0.0,
                        'net_payment': 0.0,
                        'invoice_status': 'Posted',
                        'payment_status': 'Unpaid',
                        'customer_gst_number': self.customer_locations[ckey]['gst_no'],
                        'location_key': store_loc_key,
                        'store_state': store_state,
                        'user_key': employee['user_key'],
                        'store_key': store['store_key'],
                        'is_interstate': is_interstate,
                        '_invoice_date_obj': cur,
                        '_due_date_obj': due_date,
                        '_cust_state': cust_state,
                    }

                    # ---- LINE ITEMS ----
                    allowed_cats = beh['allowed_categories']
                    if allowed_cats and ctype in ('B2B', 'B2D'):
                        prod_pool = [p for p in products if p['category'] in allowed_cats]
                    else:
                        prod_pool = products[:]
                    if not prod_pool:
                        prod_pool = products[:]

                    n_items = (
                        random.randint(3, 10) if (ctype == 'B2B' and bulk in ('large', 'extreme'))
                        else random.randint(2, 7) if ctype == 'B2B'
                        else random.randint(4, 12) if (ctype == 'B2D' and bulk in ('large', 'extreme'))
                        else random.randint(3, 8) if ctype == 'B2D'
                        else random.randint(1, 4)
                    )
                    n_items = min(n_items, len(prod_pool))
                    sel_prods = random.sample(prod_pool, n_items) if n_items > 0 else []

                    line_items = []

                    for prod in sel_prods:
                        qty_opts = BULK_QTY.get(ctype, {}).get(bulk, [1, 2])
                        qty = random.choice(qty_opts)
                        unit_price = prod['selling_price']
                        gross_line_val = qty * unit_price
                        gross_line = round(gross_line_val, 2)

                        if ctype == 'B2B':
                            bands = [(5, 10, 0.55), (10, 15, 0.30), (15, 20, 0.12), (20, 25, 0.03)]
                        elif ctype == 'B2D':
                            bands = [(3, 7, 0.50), (7, 12, 0.30), (12, 18, 0.15), (18, 25, 0.05)]
                        else:
                            bands = [(0, 2, 0.60), (2, 5, 0.30), (5, 8, 0.08), (8, 12, 0.02)]

                        r, cum = random.random(), 0.0
                        disc_pct = bands[0][0]
                        for lo, hi, prob in bands:
                            cum += prob
                            if r <= cum:
                                disc_pct = random.uniform(lo, hi)
                                break

                        disc_pct += {'small': 0, 'medium': 2, 'large': 5, 'extreme': 8}.get(bulk, 0)
                        disc_pct += {'new': 0, 'regular': 1, 'premium': 3, 'vip': 5}.get(loy, 0)
                        disc_pct = min(disc_pct, 30.0)

                        disc_amt = self.calc.calculate_discount(gross_line, disc_pct)
                        taxable_line_val = gross_line - disc_amt
                        taxable_line = round(taxable_line_val, 2)

                        if is_interstate:
                            cgst_p, sgst_p, igst_p = 0.0, 0.0, prod['igst_percent']
                            cgst_a = sgst_a = 0.0
                            igst_a = self.calc.calculate_tax(taxable_line, igst_p)
                        else:
                            cgst_p, sgst_p, igst_p = prod['cgst_percent'], prod['sgst_percent'], 0.0
                            cgst_a = self.calc.calculate_tax(taxable_line, cgst_p)
                            sgst_a = self.calc.calculate_tax(taxable_line, sgst_p)
                            igst_a = 0.0

                        tax_a = cgst_a + sgst_a + igst_a
                        line_tot_val = taxable_line + tax_a
                        line_tot = round(line_tot_val, 2)

                        li = {
                            'invoice_line_key': self._next('line'),
                            'invoice_key': inv_key,
                            'product_key': prod['product_key'],
                            'quantity': qty,
                            'unit_price_excl_gst': unit_price,
                            'gross_line_amount': gross_line,
                            'discount_percent': round(disc_pct, 4),
                            'discount_amount': disc_amt,
                            'taxable_amount': taxable_line,
                            'cgst_percent': cgst_p,
                            'sgst_percent': sgst_p,
                            'igst_percent': igst_p,
                            'cgst_amount': cgst_a,
                            'sgst_amount': sgst_a,
                            'igst_amount': igst_a,
                            'total_tax_amount': tax_a,
                            'line_total_incl_gst': line_tot,
                        }
                        line_items.append(li)

                    # ========== CRITICAL FIX ==========
                    # Calculate header totals directly from line items (no accumulation issues)
                    if line_items:
                        invoice['total_gross_amount'] = self.calc.sum_line_items(line_items, 'gross_line_amount')
                        invoice['total_discount_amount'] = self.calc.sum_line_items(line_items, 'discount_amount')
                        invoice['total_taxable_amount'] = self.calc.sum_line_items(line_items, 'taxable_amount')
                        invoice['total_cgst_amount'] = self.calc.sum_line_items(line_items, 'cgst_amount')
                        invoice['total_sgst_amount'] = self.calc.sum_line_items(line_items, 'sgst_amount')
                        invoice['total_igst_amount'] = self.calc.sum_line_items(line_items, 'igst_amount')
                        invoice['total_tax_amount'] = self.calc.sum_line_items(line_items, 'total_tax_amount')
                        invoice['total_invoice_amount_incl_gst'] = self.calc.sum_line_items(line_items, 'line_total_incl_gst')
                        
                        if invoice['total_gross_amount'] > 0:
                            invoice['discount_percentage'] = round(
                                (invoice['total_discount_amount'] / invoice['total_gross_amount']) * 100, 4)
                    
                    # Minimum invoice floor adjustment - FIXED
                    min_val = MIN_INV.get(ctype, 0)
                    if invoice['total_invoice_amount_incl_gst'] < min_val and line_items and min_val > 0:
                        multiplier = max(1.5, min_val / max(invoice['total_invoice_amount_incl_gst'], 0.01))
                        
                        # Recalculate all line items with multiplier
                        for li in line_items:
                            new_qty = max(1, round(li['quantity'] * multiplier))
                            ratio = new_qty / li['quantity']
                            
                            li['quantity'] = new_qty
                            li['gross_line_amount'] = round(li['gross_line_amount'] * ratio, 2)
                            li['discount_amount'] = round(li['discount_amount'] * ratio, 2)
                            li['taxable_amount'] = round(li['taxable_amount'] * ratio, 2)
                            li['cgst_amount'] = round(li['cgst_amount'] * ratio, 2)
                            li['sgst_amount'] = round(li['sgst_amount'] * ratio, 2)
                            li['igst_amount'] = round(li['igst_amount'] * ratio, 2)
                            li['total_tax_amount'] = round(li['total_tax_amount'] * ratio, 2)
                            li['line_total_incl_gst'] = round(li['line_total_incl_gst'] * ratio, 2)
                        
                        # CRITICAL: Recalculate header from line items (replace, not add)
                        invoice['total_gross_amount'] = self.calc.sum_line_items(line_items, 'gross_line_amount')
                        invoice['total_discount_amount'] = self.calc.sum_line_items(line_items, 'discount_amount')
                        invoice['total_taxable_amount'] = self.calc.sum_line_items(line_items, 'taxable_amount')
                        invoice['total_cgst_amount'] = self.calc.sum_line_items(line_items, 'cgst_amount')
                        invoice['total_sgst_amount'] = self.calc.sum_line_items(line_items, 'sgst_amount')
                        invoice['total_igst_amount'] = self.calc.sum_line_items(line_items, 'igst_amount')
                        invoice['total_tax_amount'] = self.calc.sum_line_items(line_items, 'total_tax_amount')
                        invoice['total_invoice_amount_incl_gst'] = self.calc.sum_line_items(line_items, 'line_total_incl_gst')
                        
                        if invoice['total_gross_amount'] > 0:
                            invoice['discount_percentage'] = round(
                                (invoice['total_discount_amount'] / invoice['total_gross_amount']) * 100, 4)

                    if ctype in ('B2B', 'B2D'):
                        self.customer_outstanding[ckey] += invoice['total_invoice_amount_incl_gst']

                    self.data['FACT_INVOICE_HEADER'].append(invoice)
                    self.data['FACT_INVOICE_LINE_ITEM'].extend(line_items)
                    last_purchase[ckey] = cur
                    invoices_generated += 1
                    customers_with_invoices.add(ckey)

            cur += timedelta(days=1)

        self.last_purchase_dates = {
            k: v for k, v in last_purchase.items() if v is not None
        }

        logger.info(f"FACT_INVOICE_HEADER:    {len(self.data['FACT_INVOICE_HEADER']):,} rows")
        logger.info(f"FACT_INVOICE_LINE_ITEM: {len(self.data['FACT_INVOICE_LINE_ITEM']):,} rows")
        logger.info(f"Customers with invoices: {len(customers_with_invoices):,} / {len(self.customer_cache):,}")

        all_customers = set(c['customer_key'] for c in self.customer_cache)
        missing_customers = all_customers - customers_with_invoices
        if missing_customers:
            logger.warning(f"⚠️ {len(missing_customers)} customers have NO invoices! Forcing...")
            self._force_missing_customer_invoices(missing_customers, products, store_loc, loc_state,
                                                cust_policy, cust_primary_store, BULK_QTY, MIN_INV)
            
    def _force_missing_customer_invoices(self, missing_customers, products, store_loc, loc_state,
                                          cust_policy, cust_primary_store, BULK_QTY, MIN_INV):
        """Force generate at least one invoice for any customer that was completely skipped"""
        logger.info(f"Forcing invoices for {len(missing_customers)} missing customers...")
        
        for ckey in missing_customers:
            customer = next((c for c in self.customer_cache if c['customer_key'] == ckey), None)
            if not customer:
                continue
            
            ctype = customer['customer_type']
            beh = self.customer_behavior[ckey]
            cust_state = self.customer_locations[ckey]['state']
            
            # FIX: Ensure onboarding date is not future
            onboard_date = datetime.strptime(customer['onboarding_date'], '%Y-%m-%d').date()
            if onboard_date > Config.TODAY:
                onboard_date = Config.TODAY - timedelta(days=30)
                logger.warning(f"Customer {ckey} had future onboarding date, adjusted to {onboard_date}")
            
            # FIX: Ensure invoice date is not before customer onboarding
            invoice_date = max(onboard_date, Config.START_DATE)
            
            pstore_key = cust_primary_store.get(ckey)
            if pstore_key:
                store = next((s for s in self.stores if s['store_key'] == pstore_key), None)
                if not store:
                    store = random.choice(self.stores)
            else:
                store = random.choice(self.stores)
            
            store_loc_key = store_loc[store['store_key']]
            store_state = loc_state.get(store_loc_key, Config.COMPANY_STATE)
            is_interstate = cust_state != store_state
            
            if ctype in ('B2B', 'B2D'):
                policy = cust_policy.get(ckey)
                credit_days = policy['credit_days_limit'] if policy else 30
                due_date = invoice_date + timedelta(days=credit_days)
            else:
                due_date = invoice_date
            
            inv_key = self._next('invoice')
            inv_number = f"INV-{invoice_date.strftime('%Y%m%d')}-{inv_key:06d}"
            inv_date_key = self.date_keys.get(invoice_date, 1)
            due_date_clamped = min(due_date, Config.TODAY)
            due_date_key = self.date_keys.get(due_date_clamped, 1)
            
            product = random.choice(products)
            bulk = beh['bulk_preference']
            qty = random.choice(BULK_QTY.get(ctype, {}).get(bulk, [1, 2]))
            unit_price = product['selling_price']
            gross_line = round(qty * unit_price, 2)
            
            disc_pct = random.uniform(0, 10)
            disc_amt = self.calc.calculate_discount(gross_line, disc_pct)
            taxable_line = round(gross_line - disc_amt, 2)
            
            if is_interstate:
                cgst_p, sgst_p, igst_p = 0.0, 0.0, product['igst_percent']
                cgst_a = sgst_a = 0.0
                igst_a = self.calc.calculate_tax(taxable_line, igst_p)
            else:
                cgst_p, sgst_p, igst_p = product['cgst_percent'], product['sgst_percent'], 0.0
                cgst_a = self.calc.calculate_tax(taxable_line, cgst_p)
                sgst_a = self.calc.calculate_tax(taxable_line, sgst_p)
                igst_a = 0.0
            
            tax_a = cgst_a + sgst_a + igst_a
            line_tot = round(taxable_line + tax_a, 2)
            
            invoice = {
                'invoice_key': inv_key,
                'invoice_id': inv_number,
                'customer_key': ckey,
                'customer_type': ctype,
                'invoice_date': fmt_date(invoice_date),
                'invoice_date_key': inv_date_key,
                'due_date': fmt_date(due_date),
                'due_date_key': due_date_key,
                'payment_habit': beh['payment_habit'],
                'total_taxable_amount': taxable_line,
                'total_cgst_amount': cgst_a,
                'total_sgst_amount': sgst_a,
                'total_igst_amount': igst_a,
                'total_tax_amount': tax_a,
                'total_gross_amount': gross_line,
                'total_discount_amount': disc_amt,
                'discount_percentage': round(disc_pct, 4),
                'total_invoice_amount_incl_gst': line_tot,
                'net_payment': 0.0,
                'invoice_status': 'Posted',
                'payment_status': 'Unpaid',
                'customer_gst_number': self.customer_locations[ckey]['gst_no'],
                'location_key': store_loc_key,
                'store_state': store_state,
                'user_key': self.employee_cache[0]['user_key'] if self.employee_cache else 1,
                'store_key': store['store_key'],
                'is_interstate': is_interstate,
                '_invoice_date_obj': invoice_date,
                '_due_date_obj': due_date,
                '_cust_state': cust_state,
            }
            
            line_item = {
                'invoice_line_key': self._next('line'),
                'invoice_key': inv_key,
                'product_key': product['product_key'],
                'quantity': qty,
                'unit_price_excl_gst': unit_price,
                'gross_line_amount': gross_line,
                'discount_percent': round(disc_pct, 4),
                'discount_amount': disc_amt,
                'taxable_amount': taxable_line,
                'cgst_percent': cgst_p,
                'sgst_percent': sgst_p,
                'igst_percent': igst_p,
                'cgst_amount': cgst_a,
                'sgst_amount': sgst_a,
                'igst_amount': igst_a,
                'total_tax_amount': tax_a,
                'line_total_incl_gst': line_tot,
            }
            
            self.data['FACT_INVOICE_HEADER'].append(invoice)
            self.data['FACT_INVOICE_LINE_ITEM'].append(line_item)
            
            if ctype in ('B2B', 'B2D'):
                self.customer_outstanding[ckey] += line_tot
            
            self.last_purchase_dates[ckey] = invoice_date

    def gen_fact_payments(self):
        """Generate payments for ALL invoices"""
        store_id_map    = {s['store_key']: s['store_id'] for s in self.stores}
        payments_by_inv: Dict[int, float] = defaultdict(float)

        for inv in self.data['FACT_INVOICE_HEADER']:
            if inv['invoice_status'] in ('Cancelled', 'Draft'):
                inv['payment_status'] = 'No Payment Required'
                inv['net_payment']    = 0.0
                continue

            inv_total = inv['total_invoice_amount_incl_gst']
            inv_date  = inv['_invoice_date_obj']
            due_date  = inv['_due_date_obj']
            ctype     = inv['customer_type']
            ckey      = inv['customer_key']
            habit     = inv['payment_habit']

            paid_amt = 0.0
            pay_date = None
            settlement_status = 'Pending'

            if habit == 'on_time':
                paid_amt = inv_total
                pay_date = due_date + timedelta(days=random.randint(0, 5))
                settlement_status = 'Settled'
            elif habit == 'early':
                paid_amt = inv_total
                pay_date = due_date - timedelta(days=random.randint(5, 10))
                settlement_status = 'Settled'
            elif habit == 'mild_late':
                if random.random() < 0.85:
                    paid_amt = inv_total
                else:
                    paid_amt = round(inv_total * random.uniform(0.5, 0.8), 2)
                pay_date = due_date + timedelta(days=random.randint(6, 15))
                settlement_status = 'Settled' if paid_amt >= inv_total - 0.01 else 'Partially Settled'
            elif habit == 'moderate_late':
                if random.random() < 0.70:
                    paid_amt = inv_total
                else:
                    paid_amt = round(inv_total * random.uniform(0.3, 0.6), 2)
                pay_date = due_date + timedelta(days=random.randint(16, 30))
                settlement_status = 'Settled' if paid_amt >= inv_total - 0.01 else 'Partially Settled'
            elif habit == 'severe_late':
                if random.random() < 0.50:
                    paid_amt = inv_total
                    pay_date = due_date + timedelta(days=random.randint(31, 60))
                    settlement_status = 'Settled'
                else:
                    if random.random() < 0.30:
                        paid_amt = round(inv_total * random.uniform(0.2, 0.5), 2)
                        pay_date = due_date + timedelta(days=random.randint(45, 90))
                        settlement_status = 'Partially Settled'
            else:  # unpaid
                if random.random() < 0.30:
                    paid_amt = round(inv_total * random.uniform(0.3, 0.7), 2)
                    pay_date = due_date + timedelta(days=random.randint(45, 90))
                    settlement_status = 'Partially Settled'

            if pay_date is None and paid_amt == 0:
                pay_date = due_date + timedelta(days=90)
                if pay_date > Config.TODAY:
                    pay_date = Config.TODAY
                settlement_status = 'Defaulted'

            if pay_date:
                pay_date = max(pay_date, inv_date)
                if pay_date > Config.TODAY:
                    pay_date = Config.TODAY

            pkey         = self._next('payment')
            pay_date_key = self.date_keys.get(pay_date) if pay_date else self.date_keys.get(Config.TODAY, 1)
            if pay_date_key is None and pay_date:
                closest_date = min(self.date_keys.keys(), key=lambda d: abs((d - pay_date).days))
                pay_date_key = self.date_keys[closest_date]
            elif pay_date_key is None:
                pay_date_key = 1

            payment_mode = random.choice(PAYMENT_MODES.get(ctype, ['NEFT'])) if paid_amt > 0 else 'None'

            rec = {
                'payment_key':          pkey,
                'payment_id':           f"PAY_{pkey:010d}",
                'invoice_key':          inv['invoice_key'],
                'customer_key':         ckey,
                'payment_date':         fmt_date(pay_date) if pay_date else fmt_date(Config.TODAY),
                'payment_date_key':     pay_date_key,
                'payment_amount':       round(paid_amt, 2),
                'payment_mode':         payment_mode,
                'bank_reference_number': f"UTR{random.randint(100000000, 999999999)}" if paid_amt > 0 else None,
                'settlement_status':    settlement_status,
                'channel_type':         ctype,
                'is_refund':            False,
                'remarks':              'No payment received' if paid_amt == 0 else None,
            }

            if ctype in ('B2B', 'B2D'):
                rec['enterprise_payment_key'] = pkey
                self.data['FACT_PAYMENT_B2B_B2D'].append(rec)
                if paid_amt > 0:
                    self.customer_outstanding[ckey] = max(0.0, self.customer_outstanding[ckey] - paid_amt)
            else:
                rec['retail_payment_key'] = pkey
                rec['store_key']          = inv['store_key']
                rec['store_id']           = store_id_map.get(inv['store_key'])
                self.data['FACT_PAYMENT_B2C'].append(rec)

            payments_by_inv[inv['invoice_key']] += paid_amt

        for inv in self.data['FACT_INVOICE_HEADER']:
            total_paid = payments_by_inv.get(inv['invoice_key'], 0.0)
            inv_total  = inv['total_invoice_amount_incl_gst']
            if inv_total <= 0:
                inv['payment_status'] = 'Refunded'
                inv['net_payment']    = 0.0
            elif total_paid >= inv_total - 0.01:
                inv['payment_status'] = 'Paid'
                inv['net_payment']    = round(inv_total, 2)
            elif total_paid > 0:
                inv['payment_status'] = 'Partially Paid'
                inv['net_payment']    = round(total_paid, 2)
            else:
                inv['payment_status'] = 'Unpaid'
                inv['net_payment']    = 0.0

        logger.info(f"FACT_PAYMENT_B2B_B2D: {len(self.data['FACT_PAYMENT_B2B_B2D']):,} rows")
        logger.info(f"FACT_PAYMENT_B2C:     {len(self.data['FACT_PAYMENT_B2C']):,} rows")

    def gen_fact_returns(self):
        products    = self.data['DIM_PRODUCTS']
        prod_cat    = {p['product_key']: p['category'] for p in products}
        managers    = [e for e in self.employee_cache if 'Manager' in e['designation']]
        store_id_map = {s['store_key']: s['store_id'] for s in self.stores}

        line_by_inv: Dict[int, List[Dict]] = defaultdict(list)
        for li in self.data['FACT_INVOICE_LINE_ITEM']:
            line_by_inv[li['invoice_key']].append(li)

        inv_refund_total: Dict[int, float] = defaultdict(float)

        for inv in self.data['FACT_INVOICE_HEADER']:
            if inv['invoice_status'] != 'Posted':
                continue

            ckey     = inv['customer_key']
            ctype    = inv['customer_type']
            loy      = self.customer_behavior[ckey]['loyalty_tier']
            inv_date = inv['_invoice_date_obj']

            base_prob = Config.RETURN_CONFIG[f"{ctype.lower()}_return_probability"]
            loy_mult  = {'vip':0.5, 'premium':0.7, 'regular':1.0, 'new':1.3}.get(loy, 1.0)
            if random.random() > base_prob * loy_mult:
                continue

            lis = line_by_inv.get(inv['invoice_key'], [])
            if not lis:
                continue

            for li in lis:
                pkey  = li['product_key']
                cat   = prod_cat.get(pkey, 'default')
                cat_m = Config.RETURN_CONFIG['category_return_multipliers'].get(cat, 1.0)
                if random.random() > 0.3 * cat_m:
                    continue

                max_qty = int(li['quantity'])
                if max_qty < 1:
                    continue
                ret_qty   = random.randint(1, max_qty) if random.random() < 0.8 else max_qty
                qty_ratio = ret_qty / li['quantity']

                taxable_refund_gross = round(li['taxable_amount']    * qty_ratio, 2)
                cgst_refund_gross    = round(li['cgst_amount']       * qty_ratio, 2)
                sgst_refund_gross    = round(li['sgst_amount']       * qty_ratio, 2)
                igst_refund_gross    = round(li['igst_amount']       * qty_ratio, 2)
                tax_refund_gross     = round(li['total_tax_amount']  * qty_ratio, 2)
                total_refund_gross   = round(taxable_refund_gross + tax_refund_gross, 2)

                roll = random.random()
                if roll < 0.70:
                    ref_pct = 1.0;  ref_type = 'Full Refund';    restock_pct = 0.0
                elif roll < 0.90:
                    ref_pct = random.uniform(0.5, 0.9); ref_type = 'Partial Refund'
                    restock_pct = random.uniform(0, 10)
                else:
                    ref_pct = 1.0;  ref_type = 'Store Credit';  restock_pct = 0.0

                restock_fee = round(total_refund_gross * ref_pct * restock_pct / 100, 2)
                net_refund  = round(total_refund_gross * ref_pct - restock_fee, 2)
                net_tax_ref = round(tax_refund_gross   * ref_pct, 2)
                net_tax_amt = round(net_tax_ref - round(
                    restock_fee * (tax_refund_gross / max(total_refund_gross, 0.01)), 2), 2)

                days_since = (Config.TODAY - inv_date).days
                max_ret_d  = min(30, days_since)
                if max_ret_d < 1:
                    continue
                ret_date     = inv_date + timedelta(days=random.randint(1, max_ret_d))
                ret_date_key = self.date_keys.get(ret_date, 1)

                refund_date  = ret_date + timedelta(days=random.randint(3, 10))
                if refund_date > Config.TODAY:
                    refund_date = Config.TODAY
                ref_date_key = self.date_keys.get(refund_date, 1)

                reasons = Config.RETURN_CONFIG['category_return_reasons'].get(
                    cat, Config.RETURN_CONFIG['category_return_reasons']['default'])
                reason = random.choices(list(reasons.keys()), weights=list(reasons.values()))[0]

                approver = random.choice(managers) if managers else self.employee_cache[0]

                rkey = self._next('return')
                self.data['FACT_RETURNS'].append({
                    'return_key':             rkey,
                    'return_id':              f"RET_{rkey:010d}",
                    'invoice_key':            inv['invoice_key'],
                    'invoice_id':             inv['invoice_id'],
                    'customer_key':           ckey,
                    'product_key':            pkey,
                    'return_quantity':        ret_qty,
                    'original_quantity':      li['quantity'],
                    'refund_amount':          round(net_refund - net_tax_amt, 2),
                    'refund_tax_amount':      net_tax_amt,
                    'total_refund_amount':    net_refund,
                    'return_date_key':        ret_date_key,
                    'return_date':            fmt_date(ret_date),
                    'refund_date_key':        ref_date_key,
                    'refund_date':            fmt_date(refund_date),
                    'return_reason_category': reason,
                    'return_reason_detail':   f"Customer requested {reason.lower()}",
                    'return_channel':         random.choice(['In-Store','Online','Phone']),
                    'refund_type':            ref_type,
                    'restocking_fee_percent': restock_pct,
                    'restocking_fee_amount':  restock_fee,
                    'net_refund_amount':      net_refund,
                    'approved_by_user_key':   approver['user_key'],
                    'approved_by_name':       approver['employee_name'],
                    'status':                 'Completed',
                    'created_at':             fmt_dt(datetime.combine(ret_date, datetime.min.time())),
                })
                inv_refund_total[inv['invoice_key']] += net_refund

                if net_refund > 0:
                    rpkey = self._next('payment')
                    ref_rec = {
                        'payment_key':          rpkey,
                        'payment_id':           f"PAY_{rpkey:010d}",
                        'invoice_key':          inv['invoice_key'],
                        'customer_key':         ckey,
                        'payment_date':         fmt_date(refund_date),
                        'payment_date_key':     ref_date_key,
                        'payment_amount':       round(-net_refund, 2),
                        'payment_mode':         random.choice(PAYMENT_MODES.get(ctype, ['NEFT'])),
                        'bank_reference_number': f"REF{random.randint(100000000, 999999999)}",
                        'settlement_status':    'Settled',
                        'channel_type':         ctype,
                        'is_refund':            True,
                        'remarks':              f"Refund for {inv['invoice_id']} - {reason}",
                    }
                    if ctype in ('B2B', 'B2D'):
                        ref_rec['enterprise_payment_key'] = rpkey
                        self.data['FACT_PAYMENT_B2B_B2D'].append(ref_rec)
                    else:
                        ref_rec['retail_payment_key'] = rpkey
                        ref_rec['store_key']          = inv['store_key']
                        ref_rec['store_id']           = store_id_map.get(inv['store_key'])
                        self.data['FACT_PAYMENT_B2C'].append(ref_rec)

        for inv in self.data['FACT_INVOICE_HEADER']:
            ref_total = inv_refund_total.get(inv['invoice_key'], 0.0)
            if ref_total > 0:
                inv['total_invoice_amount_incl_gst'] = max(0.0, round(
                    inv['total_invoice_amount_incl_gst'] - ref_total, 2))
                if inv['total_invoice_amount_incl_gst'] <= 0:
                    inv['payment_status'] = 'Refunded'
                    inv['invoice_status'] = 'Closed'
                    inv['net_payment']    = 0.0

        logger.info(f"FACT_RETURNS: {len(self.data['FACT_RETURNS']):,} rows")

    # -------------------------------------------------------------------------
    # VALIDATION - NEW ENHANCED VERSION
    # -------------------------------------------------------------------------

    def validate_data_consistency(self):
        """Enhanced validation to catch all gaps"""
        logger.info("\n" + "=" * 70)
        logger.info("DATA CONSISTENCY VALIDATION v5.0")
        logger.info("=" * 70)
        
        issues_found = False
        
        # Check 1: Every customer has at least one invoice
        customers_with_invoices = set(inv['customer_key'] for inv in self.data['FACT_INVOICE_HEADER'])
        all_customers = set(c['customer_key'] for c in self.customer_cache)
        missing_customers = all_customers - customers_with_invoices
        
        if missing_customers:
            logger.error(f"❌ {len(missing_customers)} customers have NO invoices!")
            issues_found = True
        else:
            logger.info(f"✅ All {len(all_customers)} customers have at least one invoice")
        
        # Check 2: Invoice header totals match line items
        # IMPORTANT: gen_fact_returns reduces invoice_total on the header (by refund amount)
        # but does NOT modify line items — returns are stored in FACT_RETURNS separately.
        # So invoices that had returns will always show header < line_sum by exactly the
        # refund amount. We skip those to avoid false-positive errors.
        # Fast O(n) lookup: build line-item sum dict once.
        line_item_sums: Dict[int, float] = defaultdict(float)
        for li in self.data['FACT_INVOICE_LINE_ITEM']:
            line_item_sums[li['invoice_key']] += li['line_total_incl_gst']

        invoice_mismatches = 0
        skipped_returns    = 0

        for inv in self.data['FACT_INVOICE_HEADER']:
            inv_key      = inv['invoice_key']
            line_total   = line_item_sums.get(inv_key, 0.0)
            header_total = inv['total_invoice_amount_incl_gst']

            if line_total == 0:
                continue

            diff = abs(line_total - header_total)
            if diff <= 0.1:
                continue  # within rounding tolerance — fine

            # If header < line_total it means gen_fact_returns reduced the header.
            # This is expected and correct — skip silently.
            if header_total < line_total:
                skipped_returns += 1
                continue

            # Header > line_total: genuine mismatch (should never happen)
            invoice_mismatches += 1
            if invoice_mismatches <= 10:
                logger.error(f"  Invoice {inv_key}: Header={header_total:,.2f}, "
                             f"Line sum={line_total:,.2f}, Diff={diff:,.2f}")

        if invoice_mismatches > 0:
            logger.error(f"❌ {invoice_mismatches} invoices have header > line-item sum (genuine mismatch)")
            issues_found = True
        else:
            logger.info(
                f"✅ Invoice totals consistent  "
                f"({len(self.data['FACT_INVOICE_HEADER'])} invoices, "
                f"{skipped_returns} skipped due to returns — expected)"
            )
        
        # Check 3: Date consistency (no future dates)
        future_dates = 0
        for c in self.customer_cache:
            if c['onboarding_date'] and c['onboarding_date'] > fmt_date(Config.TODAY):
                future_dates += 1
                logger.error(f"  Customer {c['customer_key']}: onboarding {c['onboarding_date']} is in future!")
        
        if future_dates > 0:
            logger.error(f"❌ {future_dates} customers have future onboarding dates!")
            issues_found = True
        else:
            logger.info(f"✅ All customers have valid onboarding dates")
        
        # Check 4: Region-state consistency
        region_issues = []
        for c in self.customer_cache:
            state = c['state']
            region_key = c['region_key']
            expected_region = self.state_to_region_key.get(state)
            if expected_region and region_key != expected_region:
                region_issues.append(c['customer_key'])
        
        if region_issues:
            logger.error(f"❌ {len(region_issues)} customers have incorrect region mapping!")
            issues_found = True
        else:
            logger.info("✅ All customers have correct region-state mapping")
        
        # Check 5: Outstanding balance consistency
        # Source of truth: sum (invoice_total - net_payment) for Unpaid/Partially Paid invoices.
        # invoice_total already has returns deducted (gen_fact_returns reduces the header),
        # so we must NOT subtract ref_tot again — that would double-count returns.
        total_outstanding_from_invoices = sum(
            max(0.0, inv['total_invoice_amount_incl_gst'] - inv.get('net_payment', 0.0))
            for inv in self.data['FACT_INVOICE_HEADER']
            if inv['payment_status'] in ('Unpaid', 'Partially Paid')
        )
        # Recalculate tracker from invoices so both sides use the same logic
        recalc_tracker = sum(self.customer_outstanding.values())

       if abs(recalc_tracker - total_outstanding_from_invoices) > 10000:
            logger.warning(
                f"⚠️  Outstanding balance drift: "
                f"tracker=₹{recalc_tracker:,.2f}  invoices=₹{total_outstanding_from_invoices:,.2f}  "
                f"diff=₹{abs(recalc_tracker - total_outstanding_from_invoices):,.2f}  "
                f"(expected — tracker is reset to invoice values at end of generate())"
            )
        else:
            logger.info(f"✅ Outstanding balance consistent: ₹{total_outstanding_from_invoices:,.2f}")
        
        # Check 6: GST calculation accuracy
        gst_issues = 0
        for inv in self.data['FACT_INVOICE_HEADER']:
            expected_tax = inv['total_cgst_amount'] + inv['total_sgst_amount'] + inv['total_igst_amount']
            if abs(expected_tax - inv['total_tax_amount']) > 0.1:
                gst_issues += 1
        
        if gst_issues > 0:
            logger.warning(f"⚠️ {gst_issues} invoices have GST calculation inconsistencies")
        else:
            logger.info(f"✅ GST calculations are consistent")
        
        if not issues_found:
            logger.info("\n🎉 ALL VALIDATION CHECKS PASSED!")
        else:
            logger.info("\n⚠️ Some validation issues found. Please review.")
        
        logger.info("=" * 70)
        return not issues_found

    # -------------------------------------------------------------------------
    # CHECKPOINT & SAVE
    # -------------------------------------------------------------------------

    def _save_checkpoint(self):
        os.makedirs(Config.STATE_DIR, exist_ok=True)

        checkpoint = {
            'last_run_date': str(Config.TODAY),
            'sequences':     dict(self.seq),
            'customer_outstanding': {
                str(k): round(v, 2)
                for k, v in self.customer_outstanding.items()
            },
            'last_purchase': {
                str(k): str(v)
                for k, v in self.last_purchase_dates.items()
            },
            'date_key_map': {
                str(d): k
                for d, k in self.date_keys.items()
            },
        }

        path = os.path.join(Config.STATE_DIR, 'checkpoint.json')
        with open(path, 'w') as f:
            json.dump(checkpoint, f, indent=2)
        logger.info(f"  Checkpoint saved → {path}")

    def _save_open_invoices(self):
        store_id_map = {s['store_key']: s['store_id'] for s in self.stores}
        open_invoices = []

        for inv in self.data['FACT_INVOICE_HEADER']:
            if inv['payment_status'] not in ('Unpaid', 'Partially Paid'):
                continue
            if inv['invoice_status'] in ('Cancelled', 'Closed', 'Draft'):
                continue

            inv_total  = inv['total_invoice_amount_incl_gst']
            net_paid   = inv.get('net_payment', 0.0)
            remaining  = max(0.0, round(inv_total - net_paid, 2))

            if remaining <= 0.01:
                continue

            open_invoices.append({
                'invoice_key':       inv['invoice_key'],
                'invoice_id':        inv['invoice_id'],
                'customer_key':      inv['customer_key'],
                'customer_type':     inv['customer_type'],
                'invoice_date':      inv['invoice_date'],
                'due_date':          inv['due_date'],
                'original_amount':   inv_total,
                'paid_so_far':       net_paid,
                'remaining_balance': remaining,
                'payment_habit':     inv['payment_habit'],
                'store_key':         inv.get('store_key'),
                'store_id':          store_id_map.get(inv.get('store_key')),
                'store_state':       inv.get('store_state')
            })

        path = os.path.join(Config.STATE_DIR, 'open_invoices.json')
        with open(path, 'w') as f:
            json.dump(open_invoices, f, indent=2, default=str)
        logger.info(f"  Open invoices saved ({len(open_invoices):,} records) → {path}")

    TEMP_FIELDS = {'_invoice_date_obj', '_due_date_obj', '_cust_state', '_store_state'}

    def _clean_invoices(self):
        for inv in self.data['FACT_INVOICE_HEADER']:
            for f in self.TEMP_FIELDS:
                inv.pop(f, None)

    # full_Load.py → save() method
    def save(self):
        out = os.path.join(Config.OUTPUT_BASE_PATH, 'full_load')
        logger.info(f"\nSaving CSVs to {out}/")
        self._clean_invoices()
        for table, rows in self.data.items():
            if rows:
                save_csv(rows, f"{out}/{table}.csv")

    # -------------------------------------------------------------------------
    # ORCHESTRATOR
    # -------------------------------------------------------------------------

    def generate(self):
        import time
        t0 = time.time()
        logger.info("=" * 70)
        logger.info("Financial Data Generator v5.0  (Fixed All Data Gaps)")
        logger.info(f"Date range : {Config.START_DATE} → {Config.TODAY}  ({Config.HISTORICAL_DAYS} days)")
        logger.info(f"Customers  : B2B={Config.VOLUME['customers_initial']['B2B']}  "
                    f"B2D={Config.VOLUME['customers_initial']['B2D']}  "
                    f"B2C={Config.VOLUME['customers_initial']['B2C']}")
        logger.info("=" * 70)

        steps = [
            ("DIM_DATE",                   self.gen_dim_date),
            ("DIM_REGION",                 self.gen_dim_region),
            ("DIM_LOCATION",               self.gen_dim_location),
            ("DIM_EMPLOYEE",               self.gen_dim_employee),
            ("DIM_PRODUCTS",               self.gen_dim_products),
            ("DIM_CUSTOMERS",              self.gen_dim_customers),
            ("DIM_STORE",                  self.gen_dim_store),
            ("CREDIT_POLICY",              self.gen_credit_policy),
            ("CUSTOMER_CREDIT_MAPPING",    self.gen_customer_credit_mapping),
            ("FACT_INVOICES + LINE_ITEMS", self.gen_fact_invoices_and_lineitems),
            ("FACT_PAYMENTS",              self.gen_fact_payments),
            ("FACT_RETURNS",               self.gen_fact_returns),
        ]

        for label, fn in steps:
            t = time.time()
            fn()
            logger.info(f"  ✓ {label} done in {time.time()-t:.1f}s")

        self.validate_data_consistency()

        inv_val  = sum(i['total_invoice_amount_incl_gst'] for i in self.data['FACT_INVOICE_HEADER'])
        pay_tot  = sum(p['payment_amount'] for p in self.data['FACT_PAYMENT_B2B_B2D'] if not p.get('is_refund', False) and p['payment_amount'] > 0)
        pay_tot += sum(p['payment_amount'] for p in self.data['FACT_PAYMENT_B2C'] if not p.get('is_refund', False) and p['payment_amount'] > 0)
        ref_tot  = sum(r['total_refund_amount'] for r in self.data['FACT_RETURNS'])

        # ── Sync customer_outstanding from invoice headers before saving checkpoint ──
        # invoice_total already reflects returns; net_payment reflects payments.
        # This makes the checkpoint state consistent with what incremental.py will load.
        self.customer_outstanding.clear()
        for inv in self.data['FACT_INVOICE_HEADER']:
            if inv['customer_type'] in ('B2B', 'B2D') and inv['payment_status'] in ('Unpaid', 'Partially Paid'):
                remaining = max(0.0, inv['total_invoice_amount_incl_gst'] - inv.get('net_payment', 0.0))
                if remaining > 0.01:
                    self.customer_outstanding[inv['customer_key']] = (
                        self.customer_outstanding.get(inv['customer_key'], 0.0) + remaining
                    )
        net_outstanding = sum(self.customer_outstanding.values())

        logger.info("\n" + "=" * 70)
        logger.info(f"Total invoice value   : ₹{inv_val:>18,.2f}")
        logger.info(f"Total payments in     : ₹{pay_tot:>18,.2f}")
        logger.info(f"Total refunds issued  : ₹{ref_tot:>18,.2f}")
        logger.info(f"Net outstanding (AR)  : ₹{net_outstanding:>18,.2f}")
        logger.info(f"Total elapsed         : {time.time()-t0:.1f}s")
        logger.info("=" * 70)

        self.save()
        logger.info("\nSaving incremental state …")
        self._save_checkpoint()
        self._save_open_invoices()

        logger.info("\nFull load complete. Ready for daily incremental runs.")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    gen = FinancialDataGenerator()
    gen.generate()
