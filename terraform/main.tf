resource "snowflake_database" "db" {
  name = "FINANCE_DB"
}

resource "snowflake_schema" "schema" {
  database = snowflake_database.db.name
  name     = "RAW"
}

resource "snowflake_table" "dim_customers" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_CUSTOMERS"

  column {
    name = "CUSTOMER_KEY"
    type = "NUMBER"
  }

  column {
    name = "CUSTOMER_ID"
    type = "STRING"
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
    type = "NUMBER"
  }

  column {
    name = "ONBOARDING_DATE"
    type = "DATE"
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
    type = "BOOLEAN"
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
    type = "NUMBER"
  }
}

resource "snowflake_table" "credit_policy" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_CREDIT_POLICY"

  column { name = "CREDIT_POLICY_KEY" type = "NUMBER" }
  column { name = "POLICY_CODE" type = "STRING" }
  column { name = "POLICY_NAME" type = "STRING" }
  column { name = "APPLICABLE_CUSTOMER_TYPE" type = "STRING" }
  column { name = "CREDIT_LIMIT_AMOUNT" type = "FLOAT" }
  column { name = "CREDIT_DAYS_LIMIT" type = "NUMBER" }
  column { name = "BLOCK_ON_EXCEED" type = "BOOLEAN" }
  column { name = "BLOCK_ON_OVERDUE_DAYS" type = "NUMBER" }
  column { name = "REQUIRES_DEPOSIT" type = "BOOLEAN" }
  column { name = "MINIMUM_DEPOSIT_AMOUNT" type = "FLOAT" }
  column { name = "APPROVAL_REQUIRED" type = "BOOLEAN" }
  column { name = "START_DATE" type = "STRING" }
  column { name = "END_DATE" type = "FLOAT" }
}

resource "snowflake_table" "customer_credit_mapping" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_CUSTOMER_CREDIT_MAPPING"

  column { name = "CUSTOMER_CREDIT_KEY" type = "NUMBER" }
  column { name = "CUSTOMER_KEY" type = "NUMBER" }
  column { name = "CREDIT_POLICY_KEY" type = "NUMBER" }
  column { name = "APPROVAL_STATUS" type = "STRING" }
  column { name = "APPROVED_BY" type = "STRING" }
  column { name = "REVIEW_DATE" type = "STRING" }
  column { name = "EFFECTIVE_FROM" type = "STRING" }
  column { name = "EFFECTIVE_TO" type = "FLOAT" }
  column { name = "IS_CURRENT" type = "STRING" }
}

resource "snowflake_table" "dim_date" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_DIM_DATE"

  column { name = "DATE_KEY" type = "NUMBER" }
  column { name = "FULL_DATE" type = "STRING" }
  column { name = "YEAR" type = "NUMBER" }
  column { name = "QUARTER" type = "NUMBER" }
  column { name = "MONTH" type = "NUMBER" }
  column { name = "MONTH_NAME" type = "STRING" }
  column { name = "DAY" type = "NUMBER" }
  column { name = "DAY_OF_WEEK" type = "NUMBER" }
  column { name = "DAY_NAME" type = "STRING" }
  column { name = "IS_WEEKEND" type = "BOOLEAN" }
  column { name = "IS_HOLIDAY" type = "BOOLEAN" }
}

resource "snowflake_table" "dim_employee" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_DIM_EMPLOYEE"

  column { name = "USER_KEY" type = "NUMBER" }
  column { name = "USER_ID" type = "STRING" }
  column { name = "EMPLOYEE_NAME" type = "STRING" }
  column { name = "DESIGNATION" type = "STRING" }
  column { name = "DEPARTMENT" type = "STRING" }
  column { name = "LOCATION_KEY" type = "NUMBER" }
  column { name = "REPORTING_MANAGER" type = "STRING" }
  column { name = "HIRE_DATE" type = "STRING" }
  column { name = "STATUS" type = "STRING" }
}

resource "snowflake_table" "dim_location" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_DIM_LOCATION"

  column { name = "LOCATION_KEY" type = "NUMBER" }
  column { name = "LOCATION_ID" type = "STRING" }
  column { name = "LOCATION_NAME" type = "STRING" }
  column { name = "LOCATION_TYPE" type = "STRING" }
  column { name = "ADDRESS" type = "STRING" }
  column { name = "CITY" type = "STRING" }
  column { name = "STATE" type = "STRING" }
  column { name = "REGION_KEY" type = "NUMBER" }
  column { name = "MANAGER_NAME" type = "STRING" }
}

resource "snowflake_table" "dim_products" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_DIM_PRODUCTS"

  column { name = "PRODUCT_KEY" type = "NUMBER" }
  column { name = "PRODUCT_ID" type = "STRING" }
  column { name = "PRODUCT_NAME" type = "STRING" }
  column { name = "CATEGORY" type = "STRING" }
  column { name = "HSN_CODE" type = "NUMBER" }
  column { name = "GST_RATE_PERCENT" type = "NUMBER" }
  column { name = "CGST_PERCENT" type = "FLOAT" }
  column { name = "SGST_PERCENT" type = "FLOAT" }
  column { name = "IGST_PERCENT" type = "FLOAT" }
  column { name = "COST_PRICE" type = "FLOAT" }
  column { name = "SELLING_PRICE" type = "FLOAT" }
  column { name = "BASE_PRICE" type = "FLOAT" }
}

resource "snowflake_table" "dim_region" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_DIM_REGION"

  column { name = "REGION_KEY" type = "NUMBER" }
  column { name = "REGION_CODE" type = "STRING" }
  column { name = "REGION_NAME" type = "STRING" }
  column { name = "COUNTRY_NAME" type = "STRING" }
  column { name = "REGIONAL_MANAGER" type = "STRING" }
  column { name = "STATES_COVERED" type = "STRING" }
}

resource "snowflake_table" "dim_store" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_DIM_STORE"

  column { name = "STORE_KEY" type = "NUMBER" }
  column { name = "STORE_ID" type = "STRING" }
  column { name = "STORE_NAME" type = "STRING" }
  column { name = "LOCATION_KEY" type = "NUMBER" }
  column { name = "GST_REGISTRATION_NO" type = "STRING" }
  column { name = "OPENING_DATE" type = "STRING" }
  column { name = "CLOSING_DATE" type = "FLOAT" }
  column { name = "STORE_MANAGER" type = "STRING" }
}

resource "snowflake_table" "fact_invoice_header" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_FACT_INVOICE_HEADER"

  column { name = "INVOICE_KEY" type = "NUMBER" }
  column { name = "INVOICE_ID" type = "STRING" }
  column { name = "CUSTOMER_KEY" type = "NUMBER" }
  column { name = "STORE_KEY" type = "NUMBER" }
  column { name = "INVOICE_DATE" type = "STRING" }
  column { name = "TOTAL_AMOUNT" type = "FLOAT" }
  column { name = "TOTAL_TAX" type = "FLOAT" }
  column { name = "DISCOUNT_AMOUNT" type = "FLOAT" }
  column { name = "NET_AMOUNT" type = "FLOAT" }
  column { name = "PAYMENT_STATUS" type = "STRING" }
  column { name = "CREATED_BY" type = "STRING" }
  column { name = "CREATED_DATE" type = "STRING" }
}

resource "snowflake_table" "fact_invoice_line_item" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_FACT_INVOICE_LINE_ITEM"

  column { name = "LINE_ITEM_KEY" type = "NUMBER" }
  column { name = "INVOICE_KEY" type = "NUMBER" }
  column { name = "PRODUCT_KEY" type = "NUMBER" }
  column { name = "QUANTITY" type = "NUMBER" }
  column { name = "UNIT_PRICE" type = "FLOAT" }
  column { name = "DISCOUNT_PERCENT" type = "FLOAT" }
  column { name = "TAX_PERCENT" type = "FLOAT" }
  column { name = "LINE_TOTAL" type = "FLOAT" }
}

resource "snowflake_table" "fact_payment_b2b_b2d" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_FACT_PAYMENT_B2B_B2D"

  column { name = "PAYMENT_KEY" type = "NUMBER" }
  column { name = "INVOICE_KEY" type = "NUMBER" }
  column { name = "CUSTOMER_KEY" type = "NUMBER" }
  column { name = "PAYMENT_DATE" type = "STRING" }
  column { name = "PAYMENT_MODE" type = "STRING" }
  column { name = "PAID_AMOUNT" type = "FLOAT" }
  column { name = "REFERENCE_NUMBER" type = "STRING" }
  column { name = "STATUS" type = "STRING" }
}

resource "snowflake_table" "fact_payment_b2c" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_FACT_PAYMENT_B2C"

  column { name = "PAYMENT_KEY" type = "NUMBER" }
  column { name = "STORE_KEY" type = "NUMBER" }
  column { name = "PAYMENT_DATE" type = "STRING" }
  column { name = "PAYMENT_MODE" type = "STRING" }
  column { name = "TOTAL_AMOUNT" type = "FLOAT" }
  column { name = "REFERENCE_NUMBER" type = "STRING" }
  column { name = "STATUS" type = "STRING" }
}

resource "snowflake_table" "fact_returns" {
  database = snowflake_database.db.name
  schema   = snowflake_schema.schema.name
  name     = "RAW_FACT_RETURNS"

  column { name = "RETURN_KEY" type = "NUMBER" }
  column { name = "INVOICE_KEY" type = "NUMBER" }
  column { name = "PRODUCT_KEY" type = "NUMBER" }
  column { name = "RETURN_DATE" type = "STRING" }
  column { name = "QUANTITY_RETURNED" type = "NUMBER" }
  column { name = "RETURN_AMOUNT" type = "FLOAT" }
  column { name = "REASON" type = "STRING" }
}
