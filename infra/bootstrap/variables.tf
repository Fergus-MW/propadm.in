variable "project_id" {
  type = string
}
variable "billing_account" {
  type    = string
  default = null
}
variable "create_project" {
  type    = bool
  default = true
}
variable "create_dns_zone" {
  type    = bool
  default = true
}
variable "org_id" {
  type    = string
  default = null
}
variable "folder_id" {
  type    = string
  default = null
}
variable "region" {
  type    = string
  default = "europe-west1"
}
variable "domain" {
  type    = string
  default = "withproperly.com"
}
variable "github_repository_url" {
  type    = string
  default = null
}
variable "github_app_installation_id" {
  type    = number
  default = 0
}
variable "github_token_secret_version" {
  type    = string
  default = null
}
