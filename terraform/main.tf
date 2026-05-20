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
  username          = var.snowflake_user
  password          = var.snowflake_password
  role              = var.snowflake_role
}

resource "snowflake_database" "finance" {
  name = "FINANCE_DATA_DB"
}

resource "snowflake_warehouse" "compute" {
  name           = "COMPUTE_WH"
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
