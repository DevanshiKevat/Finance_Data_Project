resource "snowflake_database" "db" {
  name = "FINANCE_DB"
}

resource "snowflake_schema" "schema" {
  database = snowflake_database.db.name
  name     = "RAW"
}
########################
# DIM_CUSTOMERS
########################
resource "snowflake_table" "dim_customers" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_CUSTOMERS"

  column {
    name = "CUSTOMER_KEY"
    type = "STRING"
  }
  column {
    name = "CUSTOMER_ID"
    type = "NUMBER(10,0)"
  }
  column {
    name = "CUSTOMER_NAME"
    type = "STRING"
  }
  column {
    name = "CUSTOMER_TYPE"
    type = "STRING"
  }
  column {
    name = "REGION_KEY"
    type = "STRING"
  }
  column {
    name = "ONBOARDING_DATE"
    type = "STRING"
  }
  column {
    name = "STATUS"
    type = "STRING"
  }
  column {
    name = "GST_NO"
    type = "STRING"
  }
  column {
    name = "PAYMENT_HABIT"
    type = "STRING"
  }
  column {
    name = "BULK_PREFERENCE"
    type = "STRING"
  }
  column {
    name = "LOYALTY_TIER"
    type = "STRING"
  }
  column {
    name = "BUSINESS_CATEGORY"
    type = "STRING"
  }
  column {
    name = "CHURN_RISK"
    type = "STRING"
  }
  column {
    name = "CREDIT_SCORE"
    type = "STRING"
  }
}

########################
# CREDIT_POLICY
########################
resource "snowflake_table" "credit_policy" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_CREDIT_POLICY"

  column {
    name = "CREDIT_POLICY_KEY"
    type = "STRING"
  }
  column {
    name = "POLICY_CODE"
    type = "STRING"
  }
  column {
    name = "POLICY_NAME"
    type = "STRING"
  }
  column {
    name = "APPLICABLE_CUSTOMER_TYPE"
    type = "STRING"
  }
  column {
    name = "CREDIT_LIMIT_AMOUNT"
    type = "STRING"
  }
  column {
    name = "CREDIT_DAYS_LIMIT"
    type = "STRING"
  }
  column {
    name = "BLOCK_ON_EXCEED"
    type = "STRING"
  }
  column {
    name = "BLOCK_ON_OVERDUE_DAYS"
    type = "STRING"
  }
  column {
    name = "REQUIRES_DEPOSIT"
    type = "STRING"
  }
  column {
    name = "MINIMUM_DEPOSIT_AMOUNT"
    type = "STRING"
  }
  column {
    name = "APPROVAL_REQUIRED"
    type = "STRING"
  }
  column {
    name = "START_DATE"
    type = "STRING"
  }
  column {
    name = "END_DATE"
    type = "STRING"
  }
}

########################
# CUSTOMER CREDIT MAPPING
########################
resource "snowflake_table" "customer_credit_mapping" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_CUSTOMER_CREDIT_MAPPING"

  column {
    name = "CUSTOMER_CREDIT_KEY"
    type = "STRING"
  }
  column {
    name = "CUSTOMER_KEY"
    type = "STRING"
  }
  column {
    name = "CREDIT_POLICY_KEY"
    type = "STRING"
  }
  column {
    name = "APPROVAL_STATUS"
    type = "STRING"
  }
  column {
    name = "APPROVED_BY"
    type = "STRING"
  }
  column {
    name = "REVIEW_DATE"
    type = "STRING"
  }
  column {
    name = "EFFECTIVE_FROM"
    type = "STRING"
  }
  column {
    name = "EFFECTIVE_TO"
    type = "STRING"
  }
  column {
    name = "IS_CURRENT"
    type = "STRING"
  }
}

########################
# DIM_DATE
########################
resource "snowflake_table" "dim_date" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_DIM_DATE"

  column {
    name = "DATE_KEY"
    type = "STRING"
  }
  column {
    name = "FULL_DATE"
    type = "STRING"
  }
  column {
    name = "YEAR"
    type = "STRING"
  }
  column {
    name = "QUARTER"
    type = "STRING"
  }
  column {
    name = "MONTH"
    type = "STRING"
  }
  column {
    name = "MONTH_NAME"
    type = "STRING"
  }
  column {
    name = "DAY"
    type = "STRING"
  }
  column {
    name = "DAY_OF_WEEK"
    type = "STRING"
  }
  column {
    name = "DAY_NAME"
    type = "STRING"
  }
  column {
    name = "IS_WEEKEND"
    type = "STRING"
  }
  column {
    name = "IS_HOLIDAY"
    type = "STRING"
  }
}

########################
# DIM_EMPLOYEE
########################
resource "snowflake_table" "dim_employee" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_DIM_EMPLOYEE"

  column {
    name = "USER_KEY"
    type = "STRING"
  }
  column {
    name = "USER_ID"
    type = "STRING"
  }
  column {
    name = "EMPLOYEE_NAME"
    type = "STRING"
  }
  column {
    name = "DESIGNATION"
    type = "STRING"
  }
  column {
    name = "DEPARTMENT"
    type = "STRING"
  }
  column {
    name = "LOCATION_KEY"
    type = "STRING"
  }
  column {
    name = "REPORTING_MANAGER"
    type = "STRING"
  }
  column {
    name = "HIRE_DATE"
    type = "STRING"
  }
  column {
    name = "STATUS"
    type = "STRING"
  }
}

########################
# DIM_LOCATION
########################
resource "snowflake_table" "dim_location" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_DIM_LOCATION"

  column {
    name = "LOCATION_KEY"
    type = "STRING"
  }
  column {
    name = "LOCATION_ID"
    type = "STRING"
  }
  column {
    name = "LOCATION_NAME"
    type = "STRING"
  }
  column {
    name = "LOCATION_TYPE"
    type = "STRING"
  }
  column {
    name = "ADDRESS"
    type = "STRING"
  }
  column {
    name = "CITY"
    type = "STRING"
  }
  column {
    name = "STATE"
    type = "STRING"
  }
  column {
    name = "REGION_KEY"
    type = "STRING"
  }
  column {
    name = "MANAGER_NAME"
    type = "STRING"
  }
}

########################
# DIM_PRODUCTS
########################
resource "snowflake_table" "dim_products" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_DIM_PRODUCTS"

  column {
    name = "PRODUCT_KEY"
    type = "STRING"
  }
  column {
    name = "PRODUCT_ID"
    type = "STRING"
  }
  column {
    name = "PRODUCT_NAME"
    type = "STRING"
  }
  column {
    name = "CATEGORY"
    type = "STRING"
  }
  column {
    name = "HSN_CODE"
    type = "STRING"
  }
  column {
    name = "GST_RATE_PERCENT"
    type = "STRING"
  }
  column {
    name = "CGST_PERCENT"
    type = "STRING"
  }
  column {
    name = "SGST_PERCENT"
    type = "STRING"
  }
  column {
    name = "IGST_PERCENT"
    type = "STRING"
  }
  column {
    name = "COST_PRICE"
    type = "STRING"
  }
  column {
    name = "SELLING_PRICE"
    type = "STRING"
  }
  column {
    name = "BASE_PRICE"
    type = "STRING"
  }
}

########################
# DIM_REGION
########################
resource "snowflake_table" "dim_region" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_DIM_REGION"

  column {
    name = "REGION_KEY"
    type = "STRING"
  }
  column {
    name = "REGION_CODE"
    type = "STRING"
  }
  column {
    name = "REGION_NAME"
    type = "STRING"
  }
  column {
    name = "COUNTRY_NAME"
    type = "STRING"
  }
  column {
    name = "REGIONAL_MANAGER"
    type = "STRING"
  }
  column {
    name = "STATES_COVERED"
    type = "STRING"
  }
}

########################
# DIM_STORE
########################
resource "snowflake_table" "dim_store" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_DIM_STORE"

  column {
    name = "STORE_KEY"
    type = "STRING"
  }
  column {
    name = "STORE_ID"
    type = "STRING"
  }
  column {
    name = "STORE_NAME"
    type = "STRING"
  }
  column {
    name = "LOCATION_KEY"
    type = "STRING"
  }
  column {
    name = "GST_REGISTRATION_NO"
    type = "STRING"
  }
  column {
    name = "OPENING_DATE"
    type = "STRING"
  }
  column {
    name = "CLOSING_DATE"
    type = "STRING"
  }
  column {
    name = "STORE_MANAGER"
    type = "STRING"
  }
}

########################
# FACT TABLES
########################

resource "snowflake_table" "fact_invoice_header" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_FACT_INVOICE_HEADER"

  column { 
    name = "INVOICE_KEY" 
    type = "STRING" 
  }
  column { 
    name = "INVOICE_ID" 
    type = "STRING" 
  }
  column { 
    name = "CUSTOMER_KEY" 
    type = "STRING" 
  }
  column { 
    name = "STORE_KEY" 
    type = "STRING" 
  }
  column { 
    name = "INVOICE_DATE" 
    type = "STRING" 
  }
  column { 
    name = "TOTAL_AMOUNT" 
    type = "STRING" 
  }
  column { 
    name = "TOTAL_TAX" 
    type = "STRING" 
  }
  column { 
    name = "DISCOUNT_AMOUNT" 
    type = "STRING" 
  }
  column { 
    name = "NET_AMOUNT" 
    type = "STRING" 
  }
  column { 
    name = "PAYMENT_STATUS" 
    type = "STRING" 
  }
  column { 
    name = "CREATED_BY" 
    type = "STRING" 
  }
  column { 
    name = "CREATED_DATE" 
    type = "STRING" 
  }
}

resource "snowflake_table" "fact_invoice_line_item" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_FACT_INVOICE_LINE_ITEM"

  column { 
    name = "LINE_ITEM_KEY" 
    type = "STRING" 
  }
  column { 
    name = "INVOICE_KEY" 
    type = "STRING" 
  }
  column { 
    name = "PRODUCT_KEY" 
    type = "STRING" 
  }
  column { 
    name = "QUANTITY" 
    type = "STRING" 
  }
  column { 
    name = "UNIT_PRICE" 
    type = "STRING" 
  }
  column { 
    name = "DISCOUNT_PERCENT" 
    type = "STRING" 
  }
  column { 
    name = "TAX_PERCENT" 
    type = "STRING" 
  }
  column { 
    name = "LINE_TOTAL" 
    type = "STRING" 
  }
}

resource "snowflake_table" "fact_payment_b2b_b2d" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_FACT_PAYMENT_B2B_B2D"

  column { 
    name = "PAYMENT_KEY" 
    type = "STRING" 
  }
  column { 
    name = "INVOICE_KEY" 
    type = "STRING" 
  }
  column { 
    name = "CUSTOMER_KEY" 
    type = "STRING" 
  }
  column { 
    name = "PAYMENT_DATE" 
    type = "STRING" 
  }
  column { 
    name = "PAYMENT_MODE" 
    type = "STRING" 
  }
  column { 
    name = "PAID_AMOUNT" 
    type = "STRING" 
  }
  column { 
    name = "REFERENCE_NUMBER" 
    type = "STRING" 
  }
  column { 
    name = "STATUS" 
    type = "STRING" 
  }
}

resource "snowflake_table" "fact_payment_b2c" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_FACT_PAYMENT_B2C"

  column { 
    name = "PAYMENT_KEY" 
    type = "STRING" 
  }
  column { 
    name = "STORE_KEY" 
    type = "STRING" 
  }
  column { 
    name = "PAYMENT_DATE" 
    type = "STRING" 
  }
  column { 
    name = "PAYMENT_MODE" 
    type = "STRING" 
  }
  column { 
    name = "TOTAL_AMOUNT" 
    type = "STRING" 
  }
  column { 
    name = "REFERENCE_NUMBER" 
    type = "STRING" 
  }
  column { 
    name = "STATUS" 
    type = "STRING" 
  }
}

resource "snowflake_table" "fact_returns" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_FACT_RETURNS"

  column { 
    name = "RETURN_KEY" 
    type = "STRING" 
  }
  column { 
    name = "INVOICE_KEY" 
    type = "STRING" 
  }
  column { 
    name = "PRODUCT_KEY" 
    type = "STRING" 
  }
  column { 
    name = "RETURN_DATE" 
    type = "STRING" 
  }
  column { 
    name = "QUANTITY_RETURNED" 
    type = "STRING" 
  }
  column { 
    name = "RETURN_AMOUNT" 
    type = "STRING" 
  }
  column { 
    name = "REASON" 
    type = "STRING" 
  }
}
