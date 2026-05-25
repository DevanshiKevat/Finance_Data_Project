terraform {
  required_providers {
    snowflake = {
      source  = "Snowflake-Labs/snowflake"
      version = "~> 0.87"
    }
  }
}

provider "snowflake" {
  organization_name = var.snowflake_organization   
  account_name      = var.snowflake_account        
  user         = var.snowflake_user
  password          = var.snowflake_password
  role              = var.snowflake_role
}

resource "snowflake_database" "finance" {
  name = "FINANCE_DATA_DB"
}

resource "snowflake_warehouse" "compute" {
  name           = "FINANCE_WH"
  warehouse_size = "XSMALL"
  auto_suspend   = 60
  auto_resume    = true
}

resource "snowflake_schema" "raw" {
  database = snowflake_database.finance.name
  name     = "RAW"
}

resource "snowflake_schema" "staging" {
  database = snowflake_database.finance.name
  name     = "STAGING"
}

resource "snowflake_schema" "marts" {
  database = snowflake_database.finance.name
  name     = "MARTS"
}

resource "snowflake_stage" "internal_stage" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "FINANCE_STAGE"
}

# ── DIM Tables ──────────────────────────────────────────

resource "snowflake_table" "dim_date" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "DIM_DATE"
  column {
    name = "date_key"
    type = "NUMBER"
  }
  column {
    name = "full_date"
    type = "DATE"
  }
  column {
    name = "year"
    type = "NUMBER"
  }
  column {
    name = "quarter"
    type = "NUMBER"
  }
  column {
    name = "month"
    type = "NUMBER"
  }
  column {
    name = "month_name"
    type = "VARCHAR"
  }
  column {
    name = "day"
    type = "NUMBER"
  }
  column {
    name = "day_of_week"
    type = "NUMBER"
  }
  column {
    name = "day_name"
    type = "VARCHAR"
  }
  column {
    name = "is_weekend"
    type = "BOOLEAN"
  }
  column {
    name = "is_holiday"
    type = "BOOLEAN"
  }
}

resource "snowflake_table" "dim_region" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "DIM_REGION"
  column {
    name = "region_key"
    type = "NUMBER"
  }
  column {
    name = "region_code"
    type = "VARCHAR"
  }
  column {
    name = "region_name"
    type = "VARCHAR"
  }
  column {
    name = "country_name"
    type = "VARCHAR"
  }
  column {
    name = "regional_manager"
    type = "VARCHAR"
  }
  column {
    name = "states_covered"
    type = "VARCHAR"
  }
}

resource "snowflake_table" "dim_location" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "DIM_LOCATION"
  column {
    name = "location_key"
    type = "NUMBER"
  }
  column {
    name = "location_id"
    type = "VARCHAR"
  }
  column {
    name = "location_name"
    type = "VARCHAR"
  }
  column {
    name = "location_type"
    type = "VARCHAR"
  }
  column {
    name = "address"
    type = "VARCHAR"
  }
  column {
    name = "city"
    type = "VARCHAR"
  }
  column {
    name = "state"
    type = "VARCHAR"
  }
  column {
    name = "region_key"
    type = "NUMBER"
  }
  column {
    name = "manager_name"
    type = "VARCHAR"
  }
}

resource "snowflake_table" "dim_employee" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "DIM_EMPLOYEE"
  column {
    name = "user_key"
    type = "NUMBER"
  }
  column {
    name = "user_id"
    type = "VARCHAR"
  }
  column {
    name = "employee_name"
    type = "VARCHAR"
  }
  column {
    name = "designation"
    type = "VARCHAR"
  }
  column {
    name = "department"
    type = "VARCHAR"
  }
  column {
    name = "location_key"
    type = "NUMBER"
  }
  column {
    name = "reporting_manager"
    type = "VARCHAR"
  }
  column {
    name = "hire_date"
    type = "DATE"
  }
  column {
    name = "status"
    type = "VARCHAR"
  }
}

resource "snowflake_table" "dim_products" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "DIM_PRODUCTS"
  column {
    name = "product_key"
    type = "NUMBER"
  }
  column {
    name = "product_id"
    type = "VARCHAR"
  }
  column {
    name = "product_name"
    type = "VARCHAR"
  }
  column {
    name = "category"
    type = "VARCHAR"
  }
  column {
    name = "hsn_code"
    type = "VARCHAR"
  }
  column {
    name = "gst_rate_percent"
    type = "FLOAT"
  }
  column {
    name = "cgst_percent"
    type = "FLOAT"
  }
  column {
    name = "sgst_percent"
    type = "FLOAT"
  }
  column {
    name = "igst_percent"
    type = "FLOAT"
  }
  column {
    name = "cost_price"
    type = "FLOAT"
  }
  column {
    name = "selling_price"
    type = "FLOAT"
  }
  column {
    name = "base_price"
    type = "FLOAT"
  }
}

resource "snowflake_table" "dim_customers" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "DIM_CUSTOMERS"
  column {
    name = "customer_key"
    type = "NUMBER"
  }
  column {
    name = "customer_id"
    type = "VARCHAR"
  }
  column {
    name = "customer_name"
    type = "VARCHAR"
  }
  column {
    name = "customer_type"
    type = "VARCHAR"
  }
  column {
    name = "state"
    type = "VARCHAR"
  }
  column {
    name = "city"
    type = "VARCHAR"
  }
  column {
    name = "region_key"
    type = "NUMBER"
  }
  column {
    name = "onboarding_date"
    type = "DATE"
  }
  column {
    name = "status"
    type = "VARCHAR"
  }
  column {
    name = "gst_no"
    type = "VARCHAR"
  }
  column {
    name = "payment_habit"
    type = "VARCHAR"
  }
  column {
    name = "bulk_preference"
    type = "VARCHAR"
  }
  column {
    name = "loyalty_tier"
    type = "VARCHAR"
  }
  column {
    name = "business_category"
    type = "VARCHAR"
  }
  column {
    name = "churn_risk"
    type = "FLOAT"
  }
  column {
    name = "credit_score"
    type = "NUMBER"
  }
}

resource "snowflake_table" "dim_store" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "DIM_STORE"
  column {
    name = "store_key"
    type = "NUMBER"
  }
  column {
    name = "store_id"
    type = "VARCHAR"
  }
  column {
    name = "store_name"
    type = "VARCHAR"
  }
  column {
    name = "location_key"
    type = "NUMBER"
  }
  column {
    name = "gst_registration_no"
    type = "VARCHAR"
  }
  column {
    name = "opening_date"
    type = "DATE"
  }
  column {
    name = "closing_date"
    type = "DATE"
  }
  column {
    name = "store_manager"
    type = "VARCHAR"
  }
}

resource "snowflake_table" "credit_policy" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "CREDIT_POLICY"
  column {
    name = "credit_policy_key"
    type = "NUMBER"
  }
  column {
    name = "policy_code"
    type = "VARCHAR"
  }
  column {
    name = "policy_name"
    type = "VARCHAR"
  }
  column {
    name = "applicable_customer_type"
    type = "VARCHAR"
  }
  column {
    name = "credit_limit_amount"
    type = "FLOAT"
  }
  column {
    name = "credit_days_limit"
    type = "NUMBER"
  }
  column {
    name = "block_on_exceed"
    type = "BOOLEAN"
  }
  column {
    name = "block_on_overdue_days"
    type = "NUMBER"
  }
  column {
    name = "requires_deposit"
    type = "BOOLEAN"
  }
  column {
    name = "minimum_deposit_amount"
    type = "FLOAT"
  }
  column {
    name = "approval_required"
    type = "BOOLEAN"
  }
  column {
    name = "start_date"
    type = "DATE"
  }
  column {
    name = "end_date"
    type = "DATE"
  }
}

resource "snowflake_table" "customer_credit_mapping" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "CUSTOMER_CREDIT_MAPPING"
  column {
    name = "customer_credit_key"
    type = "NUMBER"
  }
  column {
    name = "customer_key"
    type = "NUMBER"
  }
  column {
    name = "credit_policy_key"
    type = "NUMBER"
  }
  column {
    name = "approval_status"
    type = "VARCHAR"
  }
  column {
    name = "approved_by"
    type = "VARCHAR"
  }
  column {
    name = "review_date"
    type = "DATE"
  }
  column {
    name = "effective_from"
    type = "DATE"
  }
  column {
    name = "effective_to"
    type = "DATE"
  }
  column {
    name = "is_current"
    type = "BOOLEAN"
  }
}

# ── FACT Tables ─────────────────────────────────────────

resource "snowflake_table" "fact_invoice_header" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "FACT_INVOICE_HEADER"
  column {
    name = "invoice_key"
    type = "NUMBER"
  }
  column {
    name = "invoice_id"
    type = "VARCHAR"
  }
  column {
    name = "customer_key"
    type = "NUMBER"
  }
  column {
    name = "customer_type"
    type = "VARCHAR"
  }
  column {
    name = "invoice_date"
    type = "DATE"
  }
  column {
    name = "invoice_date_key"
    type = "NUMBER"
  }
  column {
    name = "due_date"
    type = "DATE"
  }
  column {
    name = "due_date_key"
    type = "NUMBER"
  }
  column {
    name = "payment_habit"
    type = "VARCHAR"
  }
  column {
    name = "total_taxable_amount"
    type = "FLOAT"
  }
  column {
    name = "total_cgst_amount"
    type = "FLOAT"
  }
  column {
    name = "total_sgst_amount"
    type = "FLOAT"
  }
  column {
    name = "total_igst_amount"
    type = "FLOAT"
  }
  column {
    name = "total_tax_amount"
    type = "FLOAT"
  }
  column {
    name = "total_gross_amount"
    type = "FLOAT"
  }
  column {
    name = "total_discount_amount"
    type = "FLOAT"
  }
  column {
    name = "discount_percentage"
    type = "FLOAT"
  }
  column {
    name = "total_invoice_amount_incl_gst"
    type = "FLOAT"
  }
  column {
    name = "net_payment"
    type = "FLOAT"
  }
  column {
    name = "invoice_status"
    type = "VARCHAR"
  }
  column {
    name = "payment_status"
    type = "VARCHAR"
  }
  column {
    name = "customer_gst_number"
    type = "VARCHAR"
  }
  column {
    name = "location_key"
    type = "NUMBER"
  }
  column {
    name = "store_state"
    type = "VARCHAR"
  }
  column {
    name = "user_key"
    type = "NUMBER"
  }
  column {
    name = "store_key"
    type = "NUMBER"
  }
  column {
    name = "is_interstate"
    type = "BOOLEAN"
  }
}

resource "snowflake_table" "fact_invoice_line_item" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "FACT_INVOICE_LINE_ITEM"
  column {
    name = "invoice_line_key"
    type = "NUMBER"
  }
  column {
    name = "invoice_key"
    type = "NUMBER"
  }
  column {
    name = "product_key"
    type = "NUMBER"
  }
  column {
    name = "quantity"
    type = "NUMBER"
  }
  column {
    name = "unit_price_excl_gst"
    type = "FLOAT"
  }
  column {
    name = "gross_line_amount"
    type = "FLOAT"
  }
  column {
    name = "discount_percent"
    type = "FLOAT"
  }
  column {
    name = "discount_amount"
    type = "FLOAT"
  }
  column {
    name = "taxable_amount"
    type = "FLOAT"
  }
  column {
    name = "cgst_percent"
    type = "FLOAT"
  }
  column {
    name = "sgst_percent"
    type = "FLOAT"
  }
  column {
    name = "igst_percent"
    type = "FLOAT"
  }
  column {
    name = "cgst_amount"
    type = "FLOAT"
  }
  column {
    name = "sgst_amount"
    type = "FLOAT"
  }
  column {
    name = "igst_amount"
    type = "FLOAT"
  }
  column {
    name = "total_tax_amount"
    type = "FLOAT"
  }
  column {
    name = "line_total_incl_gst"
    type = "FLOAT"
  }
}

resource "snowflake_table" "fact_payment_b2b_b2d" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "FACT_PAYMENT_B2B_B2D"
  column {
    name = "payment_key"
    type = "NUMBER"
  }
  column {
    name = "payment_id"
    type = "VARCHAR"
  }
  column {
    name = "invoice_key"
    type = "NUMBER"
  }
  column {
    name = "customer_key"
    type = "NUMBER"
  }
  column {
    name = "payment_date"
    type = "DATE"
  }
  column {
    name = "payment_date_key"
    type = "NUMBER"
  }
  column {
    name = "payment_amount"
    type = "FLOAT"
  }
  column {
    name = "payment_mode"
    type = "VARCHAR"
  }
  column {
    name = "bank_reference_number"
    type = "VARCHAR"
  }
  column {
    name = "settlement_status"
    type = "VARCHAR"
  }
  column {
    name = "channel_type"
    type = "VARCHAR"
  }
  column {
    name = "is_refund"
    type = "BOOLEAN"
  }
  column {
    name = "remarks"
    type = "VARCHAR"
  }
  column {
    name = "enterprise_payment_key"
    type = "NUMBER"
  }
}

resource "snowflake_table" "fact_payment_b2c" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "FACT_PAYMENT_B2C"
  column {
    name = "payment_key"
    type = "NUMBER"
  }
  column {
    name = "payment_id"
    type = "VARCHAR"
  }
  column {
    name = "invoice_key"
    type = "NUMBER"
  }
  column {
    name = "customer_key"
    type = "NUMBER"
  }
  column {
    name = "payment_date"
    type = "DATE"
  }
  column {
    name = "payment_date_key"
    type = "NUMBER"
  }
  column {
    name = "payment_amount"
    type = "FLOAT"
  }
  column {
    name = "payment_mode"
    type = "VARCHAR"
  }
  column {
    name = "bank_reference_number"
    type = "VARCHAR"
  }
  column {
    name = "settlement_status"
    type = "VARCHAR"
  }
  column {
    name = "channel_type"
    type = "VARCHAR"
  }
  column {
    name = "is_refund"
    type = "BOOLEAN"
  }
  column {
    name = "remarks"
    type = "VARCHAR"
  }
  column {
    name = "retail_payment_key"
    type = "NUMBER"
  }
  column {
    name = "store_key"
    type = "NUMBER"
  }
  column {
    name = "store_id"
    type = "VARCHAR"
  }
}

resource "snowflake_table" "fact_returns" {
  database = snowflake_database.finance.name
  schema   = snowflake_schema.raw.name
  name     = "FACT_RETURNS"
  column {
    name = "return_key"
    type = "NUMBER"
  }
  column {
    name = "return_id"
    type = "VARCHAR"
  }
  column {
    name = "invoice_key"
    type = "NUMBER"
  }
  column {
    name = "invoice_id"
    type = "VARCHAR"
  }
  column {
    name = "customer_key"
    type = "NUMBER"
  }
  column {
    name = "product_key"
    type = "NUMBER"
  }
  column {
    name = "return_quantity"
    type = "NUMBER"
  }
  column {
    name = "original_quantity"
    type = "NUMBER"
  }
  column {
    name = "refund_amount"
    type = "FLOAT"
  }
  column {
    name = "refund_tax_amount"
    type = "FLOAT"
  }
  column {
    name = "total_refund_amount"
    type = "FLOAT"
  }
  column {
    name = "return_date_key"
    type = "NUMBER"
  }
  column {
    name = "return_date"
    type = "DATE"
  }
  column {
    name = "refund_date_key"
    type = "NUMBER"
  }
  column {
    name = "refund_date"
    type = "DATE"
  }
  column {
    name = "return_reason_category"
    type = "VARCHAR"
  }
  column {
    name = "return_reason_detail"
    type = "VARCHAR"
  }
  column {
    name = "return_channel"
    type = "VARCHAR"
  }
  column {
    name = "refund_type"
    type = "VARCHAR"
  }
  column {
    name = "restocking_fee_percent"
    type = "FLOAT"
  }
  column {
    name = "restocking_fee_amount"
    type = "FLOAT"
  }
  column {
    name = "net_refund_amount"
    type = "FLOAT"
  }
  column {
    name = "approved_by_user_key"
    type = "NUMBER"
  }
  column {
    name = "approved_by_name"
    type = "VARCHAR"
  }
  column {
    name = "status"
    type = "VARCHAR"
  }
  column {
    name = "created_at"
    type = "TIMESTAMP_NTZ"
  }
}
