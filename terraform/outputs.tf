output "storage_connection_string" {
  description = "Value for AZURE_STORAGE_CONNECTION_STRING in .env"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

output "container_name" {
  description = "Value for AZURE_CONTAINER_NAME in .env"
  value       = azurerm_storage_container.raw_filings.name
}

output "app_url" {
  description = "Public URL of the deployed container app"
  value       = "https://${azurerm_container_app.main.ingress[0].fqdn}"
}
