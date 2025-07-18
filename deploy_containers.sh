#!/bin/bash

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load environment variables from .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo "📋 Loading environment variables from .env file..."
    set -a  # automatically export all variables
    source "$SCRIPT_DIR/.env"
    set +a  # disable automatic export
    echo "✅ Environment variables loaded from .env"
else
    echo "ℹ️  No .env file found. You can create one with your environment variables."
fi

# Configuration
ACR_NAME="acrgl6d2jnvquq4o"
ACR_URL="acrgl6d2jnvquq4o.azurecr.io"
RESOURCE_GROUP="rg-a2a"
CONTAINER_APP_ENV="acae-a2a"
MANAGED_IDENTITY="uami-gl6d2jnvquq4o"

# get client id from the managed identity
CLIENT_ID=$(az identity show --name $MANAGED_IDENTITY --resource-group $RESOURCE_GROUP --query "clientId" -o tsv)
echo "🔑 Client ID: $CLIENT_ID"

# retrieve default domain of container app environment
DEFAULT_DOMAIN=$(az containerapp env show --name $CONTAINER_APP_ENV --resource-group $RESOURCE_GROUP --query "properties.defaultDomain" -o tsv)
echo "🌐 Default domain: $DEFAULT_DOMAIN"

# Container configurations - simple array approach
CONTAINERS=("rag" "web" "conversation" "mcp")

# Parse command line arguments
SKIP_BUILD=false
TO_BUILD=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build|-s)
            SKIP_BUILD=true
            shift
            ;;
        --to-build)
            TO_BUILD="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 --to-build CONTAINERS [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --to-build CONTAINERS  Specify containers to build and deploy (comma-separated) [REQUIRED]"
            echo "  --skip-build, -s       Skip building containers and use existing images"
            echo "  --help, -h             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --to-build web,rag    Build and deploy web and rag containers"
            echo "  $0 --to-build web --skip-build    Deploy web container using existing image"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if --to-build is provided
if [ -z "$TO_BUILD" ]; then
    echo "❌ Error: --to-build parameter is required"
    echo "Usage: $0 --to-build CONTAINERS [OPTIONS]"
    echo "Available containers: ${CONTAINERS[*]}"
    echo "Example: $0 --to-build web,rag"
    exit 1
fi

# Convert comma-separated list to array
IFS=',' read -ra CONTAINERS_TO_BUILD <<< "$TO_BUILD"

# Validate that specified containers exist
for container in "${CONTAINERS_TO_BUILD[@]}"; do
    if [[ ! " ${CONTAINERS[*]} " =~ " $container " ]]; then
        echo "❌ Error: Container '$container' is not valid."
        echo "   Available containers: ${CONTAINERS[*]}"
        exit 1
    fi
done

echo "📋 Processing containers: ${CONTAINERS_TO_BUILD[*]}"

if [ "$SKIP_BUILD" = true ]; then
    echo "⏭️  Skipping build process - using existing images for deployment..."
else
    echo "🚀 Starting build process for specified containers..."
fi

# Function to build container using ACR task
build_container() {
    local folder=$1
    local image_name=$2
    
    echo "📦 Building container: $image_name from folder: $folder"
    
    az acr build \
        --registry $ACR_NAME \
        --image $image_name:latest \
        --file $folder/Dockerfile \
        $folder/
        
    if [ $? -eq 0 ]; then
        echo "✅ Successfully built $image_name"
    else
        echo "❌ Failed to build $image_name"
        exit 1
    fi
}

# Build containers (if not skipped)
if [ "$SKIP_BUILD" = false ]; then
    echo "🔨 Building containers using ACR tasks..."
    for container in "${CONTAINERS_TO_BUILD[@]}"; do
        build_container $container $container
    done

    echo "⏳ Waiting for builds to complete..."
    sleep 10
    echo "🎉 Specified containers built successfully!"
else
    echo "✅ Container images are ready for deployment!"
fi

echo ""
echo "📋 Processing Images:"
for container in "${CONTAINERS_TO_BUILD[@]}"; do
    echo "  $ACR_URL/$container:latest"
done

echo ""
echo "🚢 Deploying specified containers..."

# Function to deploy a container based on its type
deploy_container() {
    local container=$1
    echo ""
    echo "🚢 Deploying $container container..."
    
    case $container in
        "web")
            az containerapp create \
                --name ca-web \
                --resource-group $RESOURCE_GROUP \
                --environment $CONTAINER_APP_ENV \
                --image $ACR_URL/web:latest \
                --registry-server $ACR_URL \
                --user-assigned $MANAGED_IDENTITY \
                --ingress internal \
                --target-port 80 \
                --cpu 0.5 \
                --memory 1Gi \
                --min-replicas 1 \
                --max-replicas 3 \
                --env-vars \
                    "USE_REDIS=${USE_REDIS:-False}" \
                    "WEB_A2A_BASE_URL=http://ca-web" \
                    "INTERNAL_PORT=80" \
                    "OPENAI_API_KEY=secretref:openai-api-key" \
                --secrets \
                    "openai-api-key=${OPENAI_API_KEY:-your-openai-api-key}"
            ;;
        "rag")
            az containerapp create \
                --name ca-rag \
                --resource-group $RESOURCE_GROUP \
                --environment $CONTAINER_APP_ENV \
                --image $ACR_URL/rag:latest \
                --registry-server $ACR_URL \
                --user-assigned $MANAGED_IDENTITY \
                --ingress internal \
                --target-port 80 \
                --cpu 0.5 \
                --memory 1Gi \
                --min-replicas 1 \
                --max-replicas 3 \
                --env-vars \
                    "RAG_A2A_BASE_URL=http://ca-rag" \
                    "INTERNAL_PORT=80" \
                    "FOUNDRY_PROJECT=$FOUNDRY_PROJECT" \
                    "ASSISTANT_ID=$ASSISTANT_ID" \
                    "CLIENT_ID=$CLIENT_ID"
            ;;
        "mcp")
            az containerapp create \
                --name ca-mcp \
                --resource-group $RESOURCE_GROUP \
                --environment $CONTAINER_APP_ENV \
                --image $ACR_URL/mcp:latest \
                --registry-server $ACR_URL \
                --user-assigned $MANAGED_IDENTITY \
                --ingress internal \
                --target-port 80 \
                --cpu 0.5 \
                --memory 1Gi \
                --min-replicas 1 \
                --max-replicas 3 \
                --env-vars \
                    "MCP_PORT=80" \
                    "WEB_A2A_BASE_URL=http://ca-web" \
                    "RAG_A2A_BASE_URL=http://ca-rag"
            ;;
        "conversation")
            az containerapp create \
                --name ca-conversation \
                --resource-group $RESOURCE_GROUP \
                --environment $CONTAINER_APP_ENV \
                --image $ACR_URL/conversation:latest \
                --registry-server $ACR_URL \
                --user-assigned $MANAGED_IDENTITY \
                --ingress external \
                --target-port 8000 \
                --cpu 0.5 \
                --memory 1Gi \
                --min-replicas 1 \
                --max-replicas 3 \
                --env-vars \
                    "OPENAI_API_KEY=secretref:openai-api-key" \
                    "MCP_SERVER_URL=http://ca-mcp/mcp" \
                --secrets \
                    "openai-api-key=${OPENAI_API_KEY:-your-openai-api-key}"
            ;;
        *)
            echo "⚠️  No deployment configuration found for '$container'"
            echo "💡 Copy and modify one of the existing deployment commands above"
            return 1
            ;;
    esac
    
    if [ $? -eq 0 ]; then
        # Get the URL for the deployed container
        url=$(az containerapp show --name ca-$container --resource-group $RESOURCE_GROUP --query "properties.configuration.ingress.fqdn" -o tsv)
        echo "✅ Successfully deployed ca-$container"
        echo "🌐 $container app URL: https://$url"
    else
        echo "❌ Failed to deploy ca-$container"
        exit 1
    fi
}

# Deploy each specified container
for container in "${CONTAINERS_TO_BUILD[@]}"; do
    deploy_container $container
done

echo ""
echo "🎉 Deployment completed for: ${CONTAINERS_TO_BUILD[*]}"