# AWS Infrastructure Configuration
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    # Configure with your actual S3 backend
    bucket         = "qenergyz-terraform-state"
    key            = "aws/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "qenergyz-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "qenergyz"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "qenergyz.com"
}

# Local values
locals {
  project_name = "qenergyz"
  
  secrets = {
    db_password     = var.db_password
    jwt_secret      = random_password.jwt_secret.result
    redis_password  = random_password.redis_password.result
    sentry_dsn      = var.sentry_dsn
    stripe_api_key  = var.stripe_api_key
  }
}

# Random passwords for secrets
resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "random_password" "redis_password" {
  length  = 32
  special = true
}

variable "sentry_dsn" {
  description = "Sentry DSN for error tracking"
  type        = string
  default     = ""
}

variable "stripe_api_key" {
  description = "Stripe API key for payments"
  type        = string
  default     = ""
  sensitive   = true
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alerts"
  type        = string
  default     = ""
  sensitive   = true
}

variable "pagerduty_service_key" {
  description = "PagerDuty service key for critical alerts"
  type        = string
  default     = ""
  sensitive   = true
}

# Networking Module
module "networking" {
  source = "../modules/networking"
  
  cloud_provider = "aws"
  environment    = var.environment
  project_name   = local.project_name
  vpc_cidr       = var.vpc_cidr
}

# Database Module
module "database" {
  source = "../modules/database"
  
  cloud_provider      = "aws"
  environment         = var.environment
  project_name        = local.project_name
  vpc_id              = module.networking.vpc_id
  private_subnet_ids  = module.networking.private_subnet_ids
  db_password         = var.db_password
  db_instance_class   = var.environment == "production" ? "db.r5.xlarge" : "db.t3.medium"
}

# Secrets Management Module
module "secrets" {
  source = "../modules/secrets"
  
  cloud_provider = "aws"
  environment    = var.environment
  project_name   = local.project_name
  secrets        = local.secrets
}

# Monitoring Module
module "monitoring" {
  source = "../modules/monitoring"
  
  cloud_provider         = "aws"
  environment           = var.environment
  project_name          = local.project_name
  sentry_dsn           = var.sentry_dsn
  slack_webhook_url    = var.slack_webhook_url
  pagerduty_service_key = var.pagerduty_service_key
  health_check_url     = "https://${aws_lb.main.dns_name}/health"
}

# Application Load Balancer
resource "aws_security_group" "alb" {
  name_prefix = "${local.project_name}-${var.environment}-alb-"
  vpc_id      = module.networking.vpc_id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${local.project_name}-${var.environment}-alb-sg"
  }
}

resource "aws_lb" "main" {
  name               = "${local.project_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = module.networking.public_subnet_ids
  
  enable_deletion_protection = var.environment == "production"
  
  tags = {
    Name = "${local.project_name}-${var.environment}-alb"
  }
}

# S3 Buckets for storage
resource "aws_s3_bucket" "app_storage" {
  bucket = "${local.project_name}-${var.environment}-app-storage"
  
  tags = {
    Name = "${local.project_name}-${var.environment}-app-storage"
  }
}

resource "aws_s3_bucket_versioning" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "app_storage" {
  bucket = aws_s3_bucket.app_storage.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ECR Repository for Docker images
resource "aws_ecr_repository" "backend" {
  name                 = "${local.project_name}/backend"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = {
    Name = "${local.project_name}-backend-ecr"
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${local.project_name}/frontend"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  tags = {
    Name = "${local.project_name}-frontend-ecr"
  }
}

# ECS Cluster for container orchestration
resource "aws_ecs_cluster" "main" {
  name = "${local.project_name}-${var.environment}"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = {
    Name = "${local.project_name}-${var.environment}-cluster"
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${local.project_name}-${var.environment}"
  retention_in_days = var.environment == "production" ? 30 : 7
  
  tags = {
    Name = "${local.project_name}-${var.environment}-logs"
  }
}

# ElastiCache for Redis
resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.project_name}-${var.environment}-cache-subnet"
  subnet_ids = module.networking.private_subnet_ids
}

resource "aws_security_group" "redis" {
  name_prefix = "${local.project_name}-${var.environment}-redis-"
  vpc_id      = module.networking.vpc_id
  
  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
  
  tags = {
    Name = "${local.project_name}-${var.environment}-redis-sg"
  }
}

resource "aws_elasticache_replication_group" "main" {
  description            = "Redis cluster for ${local.project_name} ${var.environment}"
  replication_group_id   = "${local.project_name}-${var.environment}-redis"
  port                   = 6379
  parameter_group_name   = "default.redis7"
  node_type              = var.environment == "production" ? "cache.r6g.large" : "cache.t3.micro"
  num_cache_clusters     = var.environment == "production" ? 3 : 1
  engine_version         = "7.0"
  subnet_group_name      = aws_elasticache_subnet_group.main.name
  security_group_ids     = [aws_security_group.redis.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token             = random_password.redis_password.result
  
  tags = {
    Name = "${local.project_name}-${var.environment}-redis"
  }
}

# Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.networking.vpc_id
}

output "alb_dns_name" {
  description = "DNS name of the application load balancer"
  value       = aws_lb.main.dns_name
}

output "ecr_backend_url" {
  description = "URL of the backend ECR repository"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_url" {
  description = "URL of the frontend ECR repository"
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = aws_elasticache_replication_group.main.configuration_endpoint_address
  sensitive   = true
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.app_storage.id
}

output "monitoring_dashboard_url" {
  description = "URL of the monitoring dashboard"
  value       = module.monitoring.dashboard_url
}

output "alert_topic_arn" {
  description = "ARN of the alert topic"
  value       = module.monitoring.alert_topic_arn
}