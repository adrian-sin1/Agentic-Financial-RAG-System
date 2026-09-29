variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "East US"
}

variable "storage_account_name" {
  description = "Globally unique name for the storage account (lowercase letters/numbers only)"
  type        = string
}

variable "container_image" {
  description = "Full GHCR image reference to deploy, e.g. ghcr.io/adrian-sin1/agentic-financial-rag-system:latest"
  type        = string
}

variable "app_env_vars" {
  description = "All runtime environment variables the app container needs (Snowflake/Pinecone/OpenAI/etc. credentials)"
  type        = map(string)
  sensitive   = true
}
