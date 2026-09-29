resource "azurerm_log_analytics_workspace" "main" {
  name                = "financial-rag-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_container_app_environment" "main" {
  name                       = "financial-rag-env"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  logs_destination           = "log-analytics"
}

resource "azurerm_container_app" "main" {
  name                         = "financial-rag-api"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  template {
    container {
      name   = "financial-rag-api"
      image  = var.container_image
      cpu    = 0.5
      memory = "1Gi"

      dynamic "env" {
        for_each = var.app_env_vars
        content {
          name        = env.key
          secret_name = lower(replace(env.key, "_", "-"))
        }
      }
    }
  }

  dynamic "secret" {
    for_each = var.app_env_vars
    content {
      name  = lower(replace(secret.key, "_", "-"))
      value = secret.value
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport         = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}
