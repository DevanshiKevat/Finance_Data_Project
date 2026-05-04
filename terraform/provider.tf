provider "snowflake" {
  account  = var.snowflake_account
  username = var.snowflake_user
  password = var.snowflake_password
  role     = var.snowflake_role
  region   = var.snowflake_region
}
