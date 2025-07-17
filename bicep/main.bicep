/*
  AI Foundry account and project - with public network access disabled
  
  Description: 
  - Creates an AI Foundry (previously known as Azure AI Services) account and public network access disabled.
  - Creates a gpt-4o model deployment
*/
@description('That name is the name of our application. It has to be unique. Type a name followed by your resource group name. (<name>-<resourceGroupName>)')
param aiFoundryName string = 'foundrypnadisabled'

@description('Location for all resources.')
param location string = 'eastus'

@description('Name of the first project')
param defaultProjectName string = '${aiFoundryName}-proj'

@description('Name of the virtual network')
param vnetName string = 'private-vnet'

@description('Name of the private endpoint subnet')
param peSubnetName string = 'pe-subnet'

/*
  Step 1: Create an Account 
*/ 
resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = {
  name: aiFoundryName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    publicNetworkAccess: 'Enabled'

    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
      ipRules: [
        {
          value: '89.137.116.202'
        }
      ]
    }

    // Specifies whether this resource support project management as child resources, used as containers for access management, data isolation, and cost in AI Foundry.
    allowProjectManagement: true

    // Defines developer API endpoint subdomain
    customSubDomainName: aiFoundryName

    // Auth
    disableLocalAuth: false
  }
}

/* 
Step 2: Create a virtual network and private endpoint to access your private resource
*/

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '192.168.0.0/16'
      ]
    }
    subnets: [
      {
        name: peSubnetName
        properties: {
          addressPrefix: '192.168.0.0/24'
        }
      }
      {
        name: 'sn-aca'
        properties: {
          addressPrefix: '192.168.2.0/23'
        }
      }

    ]
  }
}

resource peSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: virtualNetwork
  name: peSubnetName
  properties: {
    addressPrefix: '192.168.0.0/24'
  }
}

resource acaSubnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: virtualNetwork
  name: 'sn-aca'
  properties: {
    addressPrefix: '192.168.2.0/23'
  }
}

/* 
Step 3: Create a private endpoint to access your private resource
*/

// Private endpoint for AI Services account
// - Creates network interface in customer hub subnet
// - Establishes private connection to AI Services account
resource aiAccountPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: '${aiFoundryName}-private-endpoint'
  location: resourceGroup().location
  properties: {
    subnet: {
      id: peSubnet.id                    // Deploy in customer hub subnet
    }
    privateLinkServiceConnections: [
      {
        name: '${aiFoundryName}-private-link-service-connection'
        properties: {
          privateLinkServiceId: account.id
          groupIds: [
            'account'                     // Target AI Services account
          ]
        }
      }
    ]
  }
}

/* 
  Step 5: Create a private DNS zone for the private endpoint
*/
resource aiServicesPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.services.ai.azure.com'
  location: 'global'
}

resource openAiPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.openai.azure.com'
  location: 'global'
}

resource cognitiveServicesPrivateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: 'privatelink.cognitiveservices.azure.com'
  location: 'global'
}

// 2) Link AI Services and Azure OpenAI and Cognitive Services DNS Zone to VNet
resource aiServicesLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: aiServicesPrivateDnsZone
  location: 'global'
  name: 'aiServices-link'
  properties: {
    virtualNetwork: {
      id: virtualNetwork.id                        // Link to specified VNet
    }
    registrationEnabled: false           // Don't auto-register VNet resources
  }
}

resource aiOpenAILink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: openAiPrivateDnsZone
  location: 'global'
  name: 'aiServicesOpenAI-link'
  properties: {
    virtualNetwork: {
      id: virtualNetwork.id                        // Link to specified VNet
    }
    registrationEnabled: false           // Don't auto-register VNet resources
  }
}

resource cognitiveServicesLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: cognitiveServicesPrivateDnsZone
  location: 'global'
  name: 'aiServicesCognitiveServices-link'
  properties: {
    virtualNetwork: {
      id: virtualNetwork.id                      // Link to specified VNet
    }
    registrationEnabled: false           // Don't auto-register VNet resources
  }
}

// 3) DNS Zone Group for AI Services
resource aiServicesDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: aiAccountPrivateEndpoint
  name: '${aiFoundryName}-dns-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: '${aiFoundryName}-dns-aiserv-config'
        properties: {
          privateDnsZoneId: aiServicesPrivateDnsZone.id
        }
      }
      {
        name: '${aiFoundryName}-dns-openai-config'
        properties: {
          privateDnsZoneId: openAiPrivateDnsZone.id
        }
      }
      {
        name: '${aiFoundryName}-dns-cogserv-config'
        properties: {
          privateDnsZoneId: cognitiveServicesPrivateDnsZone.id
        }
      }
    ]
  }
  dependsOn: [
    aiServicesLink 
    cognitiveServicesLink
    aiOpenAILink
  ]
}


/*
  Step 6: Deploy gpt-4o model
*/
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01'= {
  parent: account
  name: 'gpt-4o-mini'
  sku : {
    capacity: 30
    name: 'GlobalStandard'
  }
  properties: {
    model:{
      name: 'gpt-4o-mini'
      format: 'OpenAI'
      version: '2024-07-18'
    }
  }
}

/*
  Step 4: Create a Project
*/
resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  name: defaultProjectName
  parent: account
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

/*
  Step 7: Create Azure Container Apps Environment using the ACA subnet
*/
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'acae-a2a'
  location: location
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: acaSubnet.id
    }
    workloadProfiles: []
    zoneRedundant: true

  }

  
}

/*
  Step 8: Deploy azure container registry
*/
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2025-04-01' = {
  name: 'acr${uniqueString(subscription().id)}'
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// create user assigned identity
resource userAssignedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: 'uami-${uniqueString(subscription().id)}'
  location: location
}

// Role assignment to grant AcrPull permission to the managed identity
resource acrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(containerRegistry.id, userAssignedIdentity.id, 'AcrPull')
  scope: containerRegistry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: userAssignedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Role assignment to grant Azure AI Developer permission to the managed identity
resource aiDeveloperRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(account.id, userAssignedIdentity.id, 'AzureAIDeveloper')
  scope: account
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '64702f94-c441-49e6-a78b-ef80e0188fee')
    principalId: userAssignedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}


output accountId string = account.id
output accountName string = account.name
output project string = project.name
