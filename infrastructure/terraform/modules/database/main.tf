# Multi-cloud database module
variable "cloud_provider" {
  description = "Cloud provider (aws, gcp, azure)"
  type        = string
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "qenergyz"
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "qenergyladmin"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "Database instance class"
  type        = string
  default     = "db.t3.medium"
}

# AWS RDS Configuration
resource "aws_db_subnet_group" "main" {
  count      = var.cloud_provider == "aws" ? 1 : 0
  name       = "${var.project_name}-${var.environment}-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-subnet-group"
    Environment = var.environment
  }
}

resource "aws_security_group" "rds" {
  count       = var.cloud_provider == "aws" ? 1 : 0
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Security group for RDS database"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-sg"
    Environment = var.environment
  }
}

resource "aws_db_instance" "main" {
  count                   = var.cloud_provider == "aws" ? 1 : 0
  identifier              = "${var.project_name}-${var.environment}-db"
  engine                  = "postgres"
  engine_version          = "15.4"
  instance_class          = var.db_instance_class
  allocated_storage       = 100
  max_allocated_storage   = 1000
  storage_type            = "gp2"
  storage_encrypted       = true
  
  db_name  = "qenergyz"
  username = var.db_username
  password = var.db_password
  
  db_subnet_group_name   = aws_db_subnet_group.main[0].name
  vpc_security_group_ids = [aws_security_group.rds[0].id]
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = var.environment == "staging"
  deletion_protection = var.environment == "production"
  
  enabled_cloudwatch_logs_exports = ["postgresql"]
  
  tags = {
    Name        = "${var.project_name}-${var.environment}-db"
    Environment = var.environment
  }
}

# GCP Cloud SQL Configuration
resource "google_sql_database_instance" "main" {
  count            = var.cloud_provider == "gcp" ? 1 : 0
  name             = "${var.project_name}-${var.environment}-db"
  database_version = "POSTGRES_15"
  region           = "us-central1"
  
  settings {
    tier = "db-n1-standard-2"
    
    backup_configuration {
      enabled    = true
      start_time = "03:00"
      location   = "us-central1"
      
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }
    
    ip_configuration {
      ipv4_enabled                                  = false
      private_network                               = var.vpc_id
      enable_private_path_for_google_cloud_services = true
    }
    
    database_flags {
      name  = "log_checkpoints"
      value = "on"
    }
    
    database_flags {
      name  = "log_connections"
      value = "on"
    }
    
    database_flags {
      name  = "log_disconnections"
      value = "on"
    }
  }
  
  deletion_protection = var.environment == "production"
}

resource "google_sql_database" "main" {
  count    = var.cloud_provider == "gcp" ? 1 : 0
  name     = "qenergyz"
  instance = google_sql_database_instance.main[0].name
}

resource "google_sql_user" "main" {
  count    = var.cloud_provider == "gcp" ? 1 : 0
  name     = var.db_username
  instance = google_sql_database_instance.main[0].name
  password = var.db_password
}

# Azure SQL Configuration
resource "azurerm_postgresql_flexible_server" "main" {
  count                  = var.cloud_provider == "azure" ? 1 : 0
  name                   = "${var.project_name}-${var.environment}-db"
  resource_group_name    = var.resource_group_name
  location               = "East US"
  version                = "15"
  administrator_login    = var.db_username
  administrator_password = var.db_password
  zone                   = "1"
  
  storage_mb = 102400
  
  sku_name = "B_Standard_B2s"
  
  backup_retention_days = 7
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  count     = var.cloud_provider == "azure" ? 1 : 0
  name      = "qenergyz"
  server_id = azurerm_postgresql_flexible_server.main[0].id
  collation = "en_US.utf8"
  charset   = "utf8"
}

variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
  default     = ""
}

# Outputs
output "db_endpoint" {
  description = "Database endpoint"
  value = var.cloud_provider == "aws" ? aws_db_instance.main[0].endpoint : (
    var.cloud_provider == "gcp" ? google_sql_database_instance.main[0].connection_name :
    var.cloud_provider == "azure" ? azurerm_postgresql_flexible_server.main[0].fqdn : null
  )
  sensitive = true
}

output "db_name" {
  description = "Database name"
  value = var.cloud_provider == "aws" ? aws_db_instance.main[0].db_name : (
    var.cloud_provider == "gcp" ? google_sql_database.main[0].name :
    var.cloud_provider == "azure" ? azurerm_postgresql_flexible_server_database.main[0].name : null
  )
}

output "db_port" {
  description = "Database port"
  value = var.cloud_provider == "aws" ? aws_db_instance.main[0].port : (
    var.cloud_provider == "gcp" ? 5432 :
    var.cloud_provider == "azure" ? 5432 : null
  )
}