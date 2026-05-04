resource "snowflake_database" "db" {
  name = "DEMO_DB"
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
