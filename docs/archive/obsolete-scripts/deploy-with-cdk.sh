#!/bin/bash
#
# 🚀 CDK Deployment Script for Free Intelligence
# One command to rule them all!
#

set -e

echo "╔════════════════════════════════════════════╗"
echo "║   Free Intelligence - CDK Auto Deploy      ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 not found. Please install it first.${NC}"
        echo "   Install with: $2"
        exit 1
    else
        echo -e "${GREEN}✓${NC} $1 found"
    fi
}

echo "📋 Checking prerequisites..."
check_command "aws" "brew install awscli"
check_command "cdk" "npm install -g aws-cdk"
check_command "python3" "brew install python@3.11"
check_command "docker" "Download from docker.com"

# Check AWS credentials
echo ""
echo "🔐 Checking AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    REGION=$(aws configure get region || echo "us-east-1")
    echo -e "${GREEN}✓${NC} AWS configured (Account: $ACCOUNT_ID, Region: $REGION)"
else
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "   Run: aws configure"
    exit 1
fi

# Bootstrap CDK (if needed)
echo ""
echo "🏗️  Checking CDK bootstrap..."
if ! aws cloudformation describe-stacks --stack-name CDKToolkit &> /dev/null 2>&1; then
    echo -e "${YELLOW}→${NC} Bootstrapping CDK (first time setup)..."
    cdk bootstrap aws://$ACCOUNT_ID/$REGION
else
    echo -e "${GREEN}✓${NC} CDK already bootstrapped"
fi

# Setup Python environment
echo ""
echo "🐍 Setting up Python environment..."
cd cdk/
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓${NC} Dependencies installed"

# Build Docker image
echo ""
echo "🐳 Building Docker image..."
cd ..
docker build -f Dockerfile.aws -t fi-backend:latest . > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Docker image built"

# CDK Synth (validate)
echo ""
echo "🔍 Validating CDK stack..."
cd cdk/
cdk synth > /dev/null
echo -e "${GREEN}✓${NC} Stack validation passed"

# Show what will be created
echo ""
echo "📊 Resources to be created:"
echo "   • VPC with 4 subnets"
echo "   • ECS Fargate cluster"
echo "   • Application Load Balancer"
echo "   • RDS PostgreSQL database"
echo "   • S3 bucket for audio files"
echo "   • Auto-scaling (1-4 containers)"
echo ""

# Ask for confirmation
read -p "🚀 Ready to deploy? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Deploy!
echo ""
echo "🚀 Deploying stack..."
cdk deploy --require-approval never --outputs-file outputs.json

# Parse outputs
if [ -f "outputs.json" ]; then
    echo ""
    echo "╔════════════════════════════════════════════╗"
    echo "║         ✅ DEPLOYMENT SUCCESSFUL!          ║"
    echo "╚════════════════════════════════════════════╝"
    echo ""

    # Extract URLs from outputs.json
    LB_URL=$(python3 -c "import json; data=json.load(open('outputs.json')); print(data['FI-Dev']['LoadBalancerURL'])" 2>/dev/null || echo "Check outputs.json")

    echo "🌐 Backend URL: ${GREEN}$LB_URL${NC}"
    echo "📊 Health Check: ${GREEN}$LB_URL/api/health${NC}"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Update frontend .env.local:"
    echo "      NEXT_PUBLIC_BACKEND_URL=$LB_URL"
    echo ""
    echo "   2. Check deployment status:"
    echo "      aws ecs list-services --cluster FI-Cluster"
    echo ""
    echo "   3. View logs:"
    echo "      aws logs tail /ecs/fi-backend --follow"
    echo ""
    echo "   4. To destroy stack (careful!):"
    echo "      cdk destroy"
else
    echo -e "${YELLOW}⚠️  Deployment completed but couldn't parse outputs${NC}"
fi

# Cleanup
deactivate 2>/dev/null || true
