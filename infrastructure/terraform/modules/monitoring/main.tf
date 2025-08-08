# Monitoring Configuration
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

variable "sentry_dsn" {
  description = "Sentry DSN for error tracking"
  type        = string
  sensitive   = true
}

variable "slack_webhook_url" {
  description = "Slack webhook URL for alerts"
  type        = string
  sensitive   = true
}

variable "pagerduty_service_key" {
  description = "PagerDuty service key for critical alerts"
  type        = string
  sensitive   = true
  default     = ""
}

# AWS CloudWatch Configuration
resource "aws_cloudwatch_dashboard" "main" {
  count          = var.cloud_provider == "aws" ? 1 : 0
  dashboard_name = "${var.project_name}-${var.environment}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ServiceName", "${var.project_name}-backend"],
            [".", "MemoryUtilization", ".", "."],
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "${var.project_name}-${var.environment}-alb"],
            [".", "HTTPCode_Target_5XX_Count", ".", "."]
          ]
          period = 300
          stat   = "Average"
          region = "us-east-1"
          title  = "Application Performance"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", "${var.project_name}-${var.environment}-db"],
            [".", "DatabaseConnections", ".", "."],
            [".", "ReadLatency", ".", "."],
            [".", "WriteLatency", ".", "."]
          ]
          period = 300
          stat   = "Average"
          region = "us-east-1"
          title  = "Database Performance"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", "CacheClusterId", "${var.project_name}-${var.environment}-redis"],
            [".", "NetworkBytesIn", ".", "."],
            [".", "NetworkBytesOut", ".", "."],
            [".", "CurrConnections", ".", "."]
          ]
          period = 300
          stat   = "Average"
          region = "us-east-1"
          title  = "Cache Performance"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  count               = var.cloud_provider == "aws" ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    ServiceName = "${var.project_name}-backend"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "high_memory" {
  count               = var.cloud_provider == "aws" ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "This metric monitors ECS memory utilization"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    ServiceName = "${var.project_name}-backend"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  count               = var.cloud_provider == "aws" ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors 5XX error rate"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    LoadBalancer = "${var.project_name}-${var.environment}-alb"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  count               = var.cloud_provider == "aws" ? 1 : 0
  alarm_name          = "${var.project_name}-${var.environment}-db-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "75"
  alarm_description   = "This metric monitors RDS CPU utilization"
  alarm_actions       = [aws_sns_topic.alerts[0].arn]

  dimensions = {
    DBInstanceIdentifier = "${var.project_name}-${var.environment}-db"
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# SNS Topics for Alerts
resource "aws_sns_topic" "alerts" {
  count = var.cloud_provider == "aws" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-alerts"

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_sns_topic_subscription" "slack" {
  count     = var.cloud_provider == "aws" && var.slack_webhook_url != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts[0].arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.slack_notifier[0].arn
}

# Lambda function for Slack notifications
resource "aws_lambda_function" "slack_notifier" {
  count            = var.cloud_provider == "aws" && var.slack_webhook_url != "" ? 1 : 0
  filename         = "slack_notifier.zip"
  function_name    = "${var.project_name}-${var.environment}-slack-notifier"
  role            = aws_iam_role.lambda_role[0].arn
  handler         = "index.handler"
  source_code_hash = data.archive_file.slack_notifier[0].output_base64sha256
  runtime         = "python3.11"
  timeout         = 30

  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

data "archive_file" "slack_notifier" {
  count       = var.cloud_provider == "aws" && var.slack_webhook_url != "" ? 1 : 0
  type        = "zip"
  output_path = "slack_notifier.zip"
  source {
    content = templatefile("${path.module}/slack_notifier.py", {
      webhook_url = var.slack_webhook_url
    })
    filename = "index.py"
  }
}

resource "aws_iam_role" "lambda_role" {
  count = var.cloud_provider == "aws" && var.slack_webhook_url != "" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  count      = var.cloud_provider == "aws" && var.slack_webhook_url != "" ? 1 : 0
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_role[0].name
}

# GCP Monitoring Configuration
resource "google_monitoring_dashboard" "main" {
  count        = var.cloud_provider == "gcp" ? 1 : 0
  display_name = "${var.project_name}-${var.environment}-dashboard"

  dashboard_json = jsonencode({
    displayName = "${var.project_name}-${var.environment} Dashboard"
    mosaicLayout = {
      tiles = [
        {
          width  = 6
          height = 4
          widget = {
            title = "GKE CPU Utilization"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"k8s_container\""
                    aggregation = {
                      alignmentPeriod  = "60s"
                      perSeriesAligner = "ALIGN_RATE"
                    }
                  }
                }
              }]
            }
          }
        }
      ]
    }
  })
}

# GCP Alerting Policies
resource "google_monitoring_alert_policy" "high_cpu" {
  count        = var.cloud_provider == "gcp" ? 1 : 0
  display_name = "${var.project_name}-${var.environment}-high-cpu"
  combiner     = "OR"
  
  conditions {
    display_name = "High CPU Usage"
    
    condition_threshold {
      filter         = "resource.type=\"gce_instance\""
      duration       = "300s"
      comparison     = "COMPARISON_GREATER_THAN"
      threshold_value = 0.8
      
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  notification_channels = var.slack_webhook_url != "" ? [google_monitoring_notification_channel.slack[0].id] : []
}

resource "google_monitoring_notification_channel" "slack" {
  count        = var.cloud_provider == "gcp" && var.slack_webhook_url != "" ? 1 : 0
  display_name = "Slack Notifications"
  type         = "slack"

  labels = {
    url = var.slack_webhook_url
  }
}

# Azure Monitor Configuration
resource "azurerm_monitor_action_group" "main" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${var.project_name}-${var.environment}-alerts"
  resource_group_name = var.resource_group_name
  short_name          = "qenergyz"

  webhook_receiver {
    name        = "slack"
    service_uri = var.slack_webhook_url
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "azurerm_monitor_metric_alert" "high_cpu" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${var.project_name}-${var.environment}-high-cpu"
  resource_group_name = var.resource_group_name
  scopes              = [var.app_service_id]
  description         = "Action will be triggered when CPU is higher than 80%"

  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "CpuPercentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action {
    action_group_id = azurerm_monitor_action_group.main[0].id
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Uptime monitoring with external service simulation
resource "aws_cloudwatch_event_rule" "health_check" {
  count               = var.cloud_provider == "aws" ? 1 : 0
  name                = "${var.project_name}-${var.environment}-health-check"
  description         = "Trigger health check every 5 minutes"
  schedule_expression = "rate(5 minutes)"

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_event_target" "health_check_lambda" {
  count     = var.cloud_provider == "aws" ? 1 : 0
  rule      = aws_cloudwatch_event_rule.health_check[0].name
  target_id = "HealthCheckTarget"
  arn       = aws_lambda_function.health_check[0].arn
}

resource "aws_lambda_function" "health_check" {
  count            = var.cloud_provider == "aws" ? 1 : 0
  filename         = "health_check.zip"
  function_name    = "${var.project_name}-${var.environment}-health-check"
  role            = aws_iam_role.health_check_role[0].arn
  handler         = "index.handler"
  source_code_hash = data.archive_file.health_check[0].output_base64sha256
  runtime         = "python3.11"
  timeout         = 30

  environment {
    variables = {
      HEALTH_CHECK_URL = var.health_check_url
      SNS_TOPIC_ARN    = aws_sns_topic.alerts[0].arn
    }
  }

  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

data "archive_file" "health_check" {
  count       = var.cloud_provider == "aws" ? 1 : 0
  type        = "zip"
  output_path = "health_check.zip"
  source {
    content = templatefile("${path.module}/health_check.py", {
      health_check_url = var.health_check_url
    })
    filename = "index.py"
  }
}

resource "aws_iam_role" "health_check_role" {
  count = var.cloud_provider == "aws" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-health-check-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "health_check_policy" {
  count = var.cloud_provider == "aws" ? 1 : 0
  name  = "${var.project_name}-${var.environment}-health-check-policy"
  role  = aws_iam_role.health_check_role[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "sns:Publish",
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_lambda_permission" "allow_eventbridge" {
  count         = var.cloud_provider == "aws" ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.health_check[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.health_check[0].arn
}

# Variables for Azure and additional configuration
variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
  default     = ""
}

variable "app_service_id" {
  description = "Azure App Service ID"
  type        = string
  default     = ""
}

variable "health_check_url" {
  description = "URL for health checks"
  type        = string
  default     = ""
}

# Outputs
output "dashboard_url" {
  description = "URL of the monitoring dashboard"
  value = var.cloud_provider == "aws" ? "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=${aws_cloudwatch_dashboard.main[0].dashboard_name}" : (
    var.cloud_provider == "gcp" ? "https://console.cloud.google.com/monitoring/dashboards/custom/${google_monitoring_dashboard.main[0].id}" :
    var.cloud_provider == "azure" ? "https://portal.azure.com/#@/resource${azurerm_monitor_action_group.main[0].id}" : null
  )
}

output "alert_topic_arn" {
  description = "ARN of the alert topic"
  value = var.cloud_provider == "aws" ? aws_sns_topic.alerts[0].arn : null
}