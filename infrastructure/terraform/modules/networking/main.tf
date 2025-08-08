# Multi-cloud networking module
variable "cloud_provider" {
  description = "Cloud provider (aws, gcp, azure)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
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

# AWS VPC Configuration
resource "aws_vpc" "main" {
  count      = var.cloud_provider == "aws" ? 1 : 0
  cidr_block = var.vpc_cidr

  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-vpc"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_subnet" "public" {
  count             = var.cloud_provider == "aws" ? 2 : 0
  vpc_id            = aws_vpc.main[0].id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = data.aws_availability_zones.available[0].names[count.index]

  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-public-${count.index + 1}"
    Type        = "public"
    Environment = var.environment
  }
}

resource "aws_subnet" "private" {
  count             = var.cloud_provider == "aws" ? 2 : 0
  vpc_id            = aws_vpc.main[0].id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 2)
  availability_zone = data.aws_availability_zones.available[0].names[count.index]

  tags = {
    Name        = "${var.project_name}-${var.environment}-private-${count.index + 1}"
    Type        = "private"
    Environment = var.environment
  }
}

resource "aws_internet_gateway" "main" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  vpc_id = aws_vpc.main[0].id

  tags = {
    Name        = "${var.project_name}-${var.environment}-igw"
    Environment = var.environment
  }
}

resource "aws_route_table" "public" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  vpc_id = aws_vpc.main[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main[0].id
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-public-rt"
    Environment = var.environment
  }
}

resource "aws_route_table_association" "public" {
  count          = var.cloud_provider == "aws" ? 2 : 0
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public[0].id
}

# GCP VPC Configuration
resource "google_compute_network" "main" {
  count                   = var.cloud_provider == "gcp" ? 1 : 0
  name                    = "${var.project_name}-${var.environment}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "public" {
  count         = var.cloud_provider == "gcp" ? 1 : 0
  name          = "${var.project_name}-${var.environment}-public-subnet"
  ip_cidr_range = cidrsubnet(var.vpc_cidr, 8, 0)
  region        = "us-central1"
  network       = google_compute_network.main[0].id
}

resource "google_compute_subnetwork" "private" {
  count         = var.cloud_provider == "gcp" ? 1 : 0
  name          = "${var.project_name}-${var.environment}-private-subnet"
  ip_cidr_range = cidrsubnet(var.vpc_cidr, 8, 1)
  region        = "us-central1"
  network       = google_compute_network.main[0].id
}

# Azure VNet Configuration
resource "azurerm_virtual_network" "main" {
  count               = var.cloud_provider == "azure" ? 1 : 0
  name                = "${var.project_name}-${var.environment}-vnet"
  address_space       = [var.vpc_cidr]
  location            = "East US"
  resource_group_name = var.resource_group_name
}

resource "azurerm_subnet" "public" {
  count                = var.cloud_provider == "azure" ? 1 : 0
  name                 = "${var.project_name}-${var.environment}-public-subnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main[0].name
  address_prefixes     = [cidrsubnet(var.vpc_cidr, 8, 0)]
}

resource "azurerm_subnet" "private" {
  count                = var.cloud_provider == "azure" ? 1 : 0
  name                 = "${var.project_name}-${var.environment}-private-subnet"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.main[0].name
  address_prefixes     = [cidrsubnet(var.vpc_cidr, 8, 1)]
}

# Data sources
data "aws_availability_zones" "available" {
  count = var.cloud_provider == "aws" ? 1 : 0
  state = "available"
}

variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
  default     = ""
}

# Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value = var.cloud_provider == "aws" ? aws_vpc.main[0].id : (
    var.cloud_provider == "gcp" ? google_compute_network.main[0].id :
    var.cloud_provider == "azure" ? azurerm_virtual_network.main[0].id : null
  )
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value = var.cloud_provider == "aws" ? aws_subnet.public[*].id : (
    var.cloud_provider == "gcp" ? [google_compute_subnetwork.public[0].id] :
    var.cloud_provider == "azure" ? [azurerm_subnet.public[0].id] : []
  )
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value = var.cloud_provider == "aws" ? aws_subnet.private[*].id : (
    var.cloud_provider == "gcp" ? [google_compute_subnetwork.private[0].id] :
    var.cloud_provider == "azure" ? [azurerm_subnet.private[0].id] : []
  )
}