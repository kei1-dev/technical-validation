// ============================================================================
// Azure Container Registry Module
// ============================================================================

@description('Environment name (dev/prod)')
param environment string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Common tags for all resources')
param tags object = {}

@description('ACR SKU name')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param skuName string = 'Basic'

@description('Enable admin user')
param adminUserEnabled bool = true

// ============================================================================
// Variables
// ============================================================================

var acrName = 'difyacr${environment}${uniqueString(resourceGroup().id)}'

// ============================================================================
// Azure Container Registry
// ============================================================================

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  properties: {
    adminUserEnabled: adminUserEnabled
    publicNetworkAccess: 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('ACR ID')
output acrId string = containerRegistry.id

@description('ACR name')
output acrName string = containerRegistry.name

@description('ACR login server')
output acrLoginServer string = containerRegistry.properties.loginServer

@description('ACR admin username')
output acrAdminUsername string = adminUserEnabled ? containerRegistry.listCredentials().username : ''

@description('ACR admin password')
@secure()
output acrAdminPassword string = adminUserEnabled ? containerRegistry.listCredentials().passwords[0].value : ''
