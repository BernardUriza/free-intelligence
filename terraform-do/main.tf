# DigitalOcean Infrastructure for Free Intelligence
# Simple, cost-effective, and PayPal-friendly!

terraform {
  required_version = ">= 1.0"

  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.34"
    }
  }
}

# Configure the DigitalOcean Provider
provider "digitalocean" {
  token = var.do_token
}

# Variables
variable "do_token" {
  description = "DigitalOcean API Token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "nyc3"  # New York (closest to Mexico)
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

# Create a VPC
resource "digitalocean_vpc" "main" {
  name     = "fi-vpc"
  region   = var.region
  ip_range = "10.10.10.0/24"
}

# Create SSH Key
resource "digitalocean_ssh_key" "main" {
  name       = "fi-ssh-key"
  public_key = file("~/.ssh/id_rsa.pub")
}

# Create Database Cluster (PostgreSQL)
resource "digitalocean_database_cluster" "postgres" {
  name       = "fi-postgres"
  engine     = "pg"
  version    = "15"
  size       = "db-s-1vcpu-1gb"  # $15/month
  region     = var.region
  node_count = 1
}

# Create Database
resource "digitalocean_database_db" "main" {
  cluster_id = digitalocean_database_cluster.postgres.id
  name       = "free_intelligence"
}

# Create Spaces (S3-compatible storage)
resource "digitalocean_spaces_bucket" "audio" {
  name   = "fi-audio-${var.environment}"
  region = var.region
  acl    = "private"

  lifecycle_rule {
    id      = "archive-old-audio"
    enabled = true

    expiration {
      days = 90
    }
  }
}

# Create App Platform deployment (Serverless containers)
resource "digitalocean_app" "backend" {
  spec {
    name   = "fi-backend"
    region = var.region

    service {
      name               = "api"
      instance_count     = 1
      instance_size_slug = "basic-xxs"  # $5/month

      git {
        repo_clone_url = "https://github.com/yourusername/free-intelligence.git"
        branch         = "main"
      }

      dockerfile_path = "Dockerfile"

      env {
        key   = "PORT"
        value = "7001"
      }

      env {
        key   = "DATABASE_URL"
        value = digitalocean_database_cluster.postgres.uri
        type  = "SECRET"
      }

      env {
        key   = "SPACES_ACCESS_KEY"
        value = digitalocean_spaces_bucket_object.config.access_key
        type  = "SECRET"
      }

      http_port = 7001

      health_check {
        http_path       = "/api/health"
        initial_delay_seconds = 30
        period_seconds        = 10
      }
    }

    # Static site for frontend
    static_site {
      name          = "frontend"
      build_command = "pnpm build"
      output_dir    = "apps/aurity/.next"

      git {
        repo_clone_url = "https://github.com/yourusername/free-intelligence.git"
        branch         = "main"
      }

      env {
        key   = "NEXT_PUBLIC_BACKEND_URL"
        value = "${digitalocean_app.backend.default_ingress}"
      }
    }

    # Custom domain (optional)
    # domain {
    #   name = "yourdomain.com"
    #   type = "PRIMARY"
    # }
  }
}

# Alternative: Traditional Droplet (if you prefer VPS)
resource "digitalocean_droplet" "backend_alternative" {
  count = 0  # Set to 1 to create a droplet instead of App Platform

  name     = "fi-backend"
  region   = var.region
  size     = "s-1vcpu-1gb"  # $6/month
  image    = "docker-20-04"
  vpc_uuid = digitalocean_vpc.main.id
  ssh_keys = [digitalocean_ssh_key.main.fingerprint]

  user_data = templatefile("${path.module}/cloud-init.yaml", {
    database_url = digitalocean_database_cluster.postgres.uri
    spaces_key   = digitalocean_spaces_bucket.audio.name
  })
}

# Firewall rules
resource "digitalocean_firewall" "web" {
  name = "fi-firewall"

  droplet_ids = digitalocean_droplet.backend_alternative[*].id

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0"]  # Restrict to your IP in production
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "7001"
    source_addresses = ["0.0.0.0/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0"]
  }
}

# Outputs
output "app_url" {
  value       = digitalocean_app.backend.default_ingress
  description = "URL of the deployed application"
}

output "database_uri" {
  value       = digitalocean_database_cluster.postgres.uri
  sensitive   = true
  description = "PostgreSQL connection string"
}

output "spaces_endpoint" {
  value       = "https://${var.region}.digitaloceanspaces.com"
  description = "Spaces (S3) endpoint"
}

output "monthly_cost" {
  value       = "$20-25/month (App Platform + Database)"
  description = "Estimated monthly cost"
}
