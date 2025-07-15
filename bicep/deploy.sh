#!/bin/bash

# Deploy AI Foundry with Private Network Access
# This script deploys the Bicep template using the parameters file

set -e  # Exit on any error

# Configuration
RESOURCE_GROUP_NAME="rg-a2a"
DEPLOYMENT_NAME="ai-foundry-deployment-$(date +%Y%m%d-%H%M%S)"
TEMPLATE_FILE="main.bicep"
PARAMETERS_FILE="main.bicepparam"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}AI Foundry Deployment Script${NC}"
echo "=================================="

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is logged in
if ! az account show &> /dev/null; then
    echo -e "${RED}Error: Not logged in to Azure. Please run 'az login' first.${NC}"
    exit 1
fi

# Get resource group name if not set
if [ -z "$RESOURCE_GROUP_NAME" ]; then
    echo -e "${YELLOW}Please enter the resource group name:${NC}"
    read -r RESOURCE_GROUP_NAME
fi

# Validate resource group exists
if ! az group show --name "$RESOURCE_GROUP_NAME" &> /dev/null; then
    echo -e "${RED}Error: Resource group '$RESOURCE_GROUP_NAME' does not exist.${NC}"
    echo -e "${YELLOW}Would you like to create it? (y/n):${NC}"
    read -r CREATE_RG
    if [ "$CREATE_RG" = "y" ] || [ "$CREATE_RG" = "Y" ]; then
        echo -e "${YELLOW}Please enter the location for the new resource group (e.g., swedencentral):${NC}"
        read -r RG_LOCATION
        echo "Creating resource group '$RESOURCE_GROUP_NAME' in '$RG_LOCATION'..."
        az group create --name "$RESOURCE_GROUP_NAME" --location "$RG_LOCATION"
        echo -e "${GREEN}Resource group created successfully.${NC}"
    else
        echo -e "${RED}Deployment cancelled.${NC}"
        exit 1
    fi
fi

# Check if Bicep files exist
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo -e "${RED}Error: Template file '$TEMPLATE_FILE' not found.${NC}"
    exit 1
fi

if [ ! -f "$PARAMETERS_FILE" ]; then
    echo -e "${RED}Error: Parameters file '$PARAMETERS_FILE' not found.${NC}"
    exit 1
fi

echo ""
echo "Deployment Details:"
echo "  Resource Group: $RESOURCE_GROUP_NAME"
echo "  Deployment Name: $DEPLOYMENT_NAME"
echo "  Template File: $TEMPLATE_FILE"
echo "  Parameters File: $PARAMETERS_FILE"
echo ""

# Confirm deployment
echo -e "${YELLOW}Do you want to proceed with the deployment? (y/n):${NC}"
read -r CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo -e "${YELLOW}Deployment cancelled.${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Starting deployment...${NC}"
echo ""

# Deploy the template
az deployment group create \
    --resource-group "$RESOURCE_GROUP_NAME" \
    --name "$DEPLOYMENT_NAME" \
    --template-file "$TEMPLATE_FILE" \
    --parameters "$PARAMETERS_FILE" \
    --verbose

# Check deployment status
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    echo ""
    
    # Get deployment outputs
    echo -e "${YELLOW}Deployment Outputs:${NC}"
    az deployment group show \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --name "$DEPLOYMENT_NAME" \
        --query "properties.outputs" \
        --output table
        
    echo ""
    echo -e "${YELLOW}Resources created:${NC}"
    echo "- AI Foundry Account with private network access"
    echo "- Virtual Network with private endpoint subnet"
    echo "- Private endpoint for AI Services"
    echo "- Private DNS zones and configurations"
    echo "- GPT-4o-mini model deployment"
    echo "- AI Foundry project"
    
else
    echo ""
    echo -e "${RED}❌ Deployment failed!${NC}"
    echo ""
    echo "To debug the deployment, run:"
    echo "az deployment group show --resource-group $RESOURCE_GROUP_NAME --name $DEPLOYMENT_NAME"
    exit 1
fi 