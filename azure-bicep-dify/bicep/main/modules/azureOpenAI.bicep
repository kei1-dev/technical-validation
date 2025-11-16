// ============================================================================
// Azure OpenAI Service Module - GPT-4.1 Model Deployment
// ============================================================================

@description('Environment name (dev/prod)')
@allowed([
  'dev'
  'prod'
])
param environment string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Common tags for all resources')
param tags object = {}

@description('Azure OpenAI Service SKU')
@allowed([
  'S0'
])
param skuName string = 'S0'

@description('Model deployment name for GPT-4.1')
param modelDeploymentName string = 'gpt-41-deployment'

@description('Model name')
param modelName string = 'gpt-4.1'

@description('Model version')
param modelVersion string = '2025-04-14'

@description('Model capacity (Tokens Per Minute)')
param modelCapacity int = 10

@description('Enable public network access')
param publicNetworkAccess bool = false

// ============================================================================
// Variables
// ============================================================================

var uniqueSuffix = uniqueString(resourceGroup().id)
var openAIAccountName = 'dify-${environment}-openai-${uniqueSuffix}'

// ============================================================================
// Azure OpenAI Service
// ============================================================================

resource openAIAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAIAccountName
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: {
    name: skuName
  }
  properties: {
    customSubDomainName: openAIAccountName
    publicNetworkAccess: publicNetworkAccess ? 'Enabled' : 'Disabled'
    networkAcls: {
      defaultAction: publicNetworkAccess ? 'Allow' : 'Deny'
      virtualNetworkRules: []
      ipRules: []
    }
  }
}

// ============================================================================
// GPT-4.1 Model Deployment
// ============================================================================

resource gpt41Deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openAIAccount
  name: modelDeploymentName
  sku: {
    name: 'Standard'
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: modelName
      version: modelVersion
    }
    versionUpgradeOption: 'OnceNewDefaultVersionAvailable'
    raiPolicyName: 'Microsoft.Default'
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('Azure OpenAI Account ID')
output openAIAccountId string = openAIAccount.id

@description('Azure OpenAI Account Name')
output openAIAccountName string = openAIAccount.name

@description('Azure OpenAI Endpoint')
output openAIEndpoint string = openAIAccount.properties.endpoint

@description('Azure OpenAI Deployment Name')
output openAIDeploymentName string = gpt41Deployment.name

@description('Azure OpenAI API Key (use with caution)')
output openAIApiKey string = openAIAccount.listKeys().key1

@description('Azure OpenAI Account Location')
output openAILocation string = openAIAccount.location
