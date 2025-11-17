#!/bin/bash
# Quick deploy script - NO VENV NEEDED!

cd /Users/bernardurizaorozco/Documents/free-intelligence/pulumi-do

# Initialize if needed
if [ ! -f "Pulumi.dev.yaml" ]; then
    pulumi stack init dev
fi

# Set config
# IMPORTANT: Set your DigitalOcean token first:
# export DIGITALOCEAN_TOKEN="your_token_here"
pulumi config set digitalocean:token "${DIGITALOCEAN_TOKEN}" --secret
pulumi config set region nyc3
pulumi config set environment dev

# Deploy!
echo "🚀 Deploying to DigitalOcean..."
pulumi up
