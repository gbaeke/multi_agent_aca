# AI Foundry with Private Network Access - Deployment Guide

This Bicep template deploys an Azure AI Foundry account with private network access, including all necessary networking components and a GPT-4o-mini model deployment.

## What Gets Deployed

- **AI Foundry Account** with public network access disabled
- **Virtual Network** with dedicated subnets for private endpoints and Azure Container Apps
- **Private Endpoint** for secure access to AI Services
- **Private DNS Zones** for proper name resolution
- **GPT-4o-mini Model Deployment** 
- **AI Foundry Project**
- **Azure Container Apps Environment**

## Prerequisites

### 1. Azure CLI Installation

You need the Azure CLI installed on your machine. 

**Install Azure CLI:**
- **Windows**: Download from [Azure CLI for Windows](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows)
- **macOS**: `brew install azure-cli`
- **Linux**: Follow instructions at [Azure CLI for Linux](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-linux)

**Verify installation:**
```bash
az --version
```

### 2. Azure Authentication

**Login to Azure:**
```bash
az login
```

This will open a browser window for authentication.

**Check your current subscription:**
```bash
az account show
```

**List all available subscriptions:**
```bash
az account list --output table
```

**Set a specific subscription (if needed):**
```bash
az account set --subscription "<subscription-id-or-name>"
```

**Verify you're using the correct subscription:**
```bash
az account show --query "name" --output tsv
```

## Configuration

### 3. Modify Parameters

Edit the `main.bicepparam` file to customize your deployment:

```bicep
using './main.bicep'

param aiFoundryName = 'fndry-a2a'           # Change to your preferred name
param location = 'swedencentral'            # Change to your preferred region
param defaultProjectName = '${aiFoundryName}-proj'
param vnetName = 'vnet-a2a'                 # Change VNet name if needed
param peSubnetName = 'sn-pe'                # Change subnet name if needed
```

### 4. Update Resource Group (Optional)

If you want to use a different resource group, edit the `deploy.sh` script:

```bash
# Change this line in deploy.sh
RESOURCE_GROUP_NAME="rg-a2a"  # Change to your preferred resource group name
```

## Deployment

### 5. Run the Deployment Script

Make the script executable and run it:

```bash
chmod +x deploy.sh
./deploy.sh
```

The script will:
1. Check if Azure CLI is installed
2. Verify you're logged in to Azure
3. Validate or create the resource group
4. Confirm deployment parameters
5. Deploy the Bicep template
6. Show deployment outputs and status

### 6. Manual Deployment (Alternative)

If you prefer to run the deployment manually:

```bash
# Set variables
RESOURCE_GROUP_NAME="rg-a2a"
DEPLOYMENT_NAME="ai-foundry-deployment-$(date +%Y%m%d-%H%M%S)"

# Create resource group (if it doesn't exist)
az group create --name $RESOURCE_GROUP_NAME --location swedencentral

# Deploy the template
az deployment group create \
    --resource-group $RESOURCE_GROUP_NAME \
    --name $DEPLOYMENT_NAME \
    --template-file main.bicep \
    --parameters main.bicepparam \
    --verbose
```

## Post-Deployment

### Verify Deployment

**Check deployment status:**
```bash
az deployment group show \
    --resource-group rg-a2a \
    --name <deployment-name> \
    --query "properties.provisioningState"
```

**View deployment outputs:**
```bash
az deployment group show \
    --resource-group rg-a2a \
    --name <deployment-name> \
    --query "properties.outputs"
```

**List created resources:**
```bash
az resource list --resource-group rg-a2a --output table
```

### Access Your AI Foundry

1. Navigate to the [Azure Portal](https://portal.azure.com)
2. Go to your resource group
3. Find the AI Foundry account (named according to your `aiFoundryName` parameter)
4. Note that public access is disabled - you'll need to access it from within the VNet or through a VPN/ExpressRoute connection

## Troubleshooting

### Common Issues

**1. Authentication Errors**
```bash
# Re-login if needed
az login
az account set --subscription "<your-subscription>"
```

**2. Permission Errors**
- Ensure you have Contributor or Owner role on the subscription/resource group
- Some AI services may require additional permissions

**3. Region Availability**
- Ensure the selected region supports AI Foundry and GPT-4o models
- Check [Azure AI services availability](https://azure.microsoft.com/en-us/global-infrastructure/services/?products=cognitive-services)

**4. Resource Name Conflicts**
- AI Foundry names must be globally unique
- Change the `aiFoundryName` parameter if you get naming conflicts

**5. Quota Limitations**
- Check your subscription quotas for AI services
- Some regions may have capacity limitations

### Getting Help

**View deployment logs:**
```bash
az deployment group show \
    --resource-group rg-a2a \
    --name <deployment-name> \
    --query "properties.error"
```

**Check activity logs:**
```bash
az monitor activity-log list \
    --resource-group rg-a2a \
    --max-events 50
```

## Security Considerations

- The AI Foundry account has public network access disabled
- Access is only possible through the private endpoint within the VNet
- Consider setting up VPN or ExpressRoute for secure access from on-premises
- Review and adjust the IP rules in the Bicep template if needed (currently set to `89.137.116.202`)

## Cost Optimization

- The deployment uses S0 pricing tier for AI Services
- GPT-4o-mini model is deployed with minimal capacity (1 unit)
- Consider scaling based on your actual usage requirements
- Monitor costs through Azure Cost Management

## Next Steps

After successful deployment:
1. Set up VPN or ExpressRoute for secure access
2. Configure AI Foundry projects and models as needed
3. Deploy applications to the Azure Container Apps environment
4. Set up monitoring and logging
5. Configure backup and disaster recovery if required
