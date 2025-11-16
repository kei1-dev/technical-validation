// ============================================================================
// Storage Module - Azure Blob Storage
// ============================================================================

@description('Environment name (dev/prod)')
param environment string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Common tags for all resources')
param tags object = {}

@description('Storage SKU name')
@allowed([
  'Standard_LRS'
  'Standard_GRS'
  'Standard_RAGRS'
  'Standard_ZRS'
  'Premium_LRS'
  'Premium_ZRS'
])
param skuName string = 'Standard_LRS'

@description('Storage account kind')
@allowed([
  'Storage'
  'StorageV2'
  'BlobStorage'
])
param kind string = 'StorageV2'

@description('Enable blob versioning (recommended for production)')
param enableVersioning bool = false

@description('Enable blob soft delete (recommended for production)')
param enableBlobSoftDelete bool = false

@description('Blob soft delete retention days (1-365)')
@minValue(1)
@maxValue(365)
param blobSoftDeleteRetentionDays int = 7

@description('Enable container soft delete (recommended for production)')
param enableContainerSoftDelete bool = false

@description('Container soft delete retention days (1-365)')
@minValue(1)
@maxValue(365)
param containerSoftDeleteRetentionDays int = 7

@description('Enable hierarchical namespace (Data Lake Gen2)')
param enableHierarchicalNamespace bool = false

// ============================================================================
// Variables
// ============================================================================

var resourceNamePrefix = 'dify${environment}'

// Storage account name must be globally unique and lowercase, no hyphens
var storageAccountName = take('${toLower(resourceNamePrefix)}st${uniqueString(resourceGroup().id)}', 24)

// Container names
var containerNames = [
  'dify-app-storage'    // Application files
  'dify-dataset'        // Datasets and documents
  'dify-tools'          // Tool assets
  'dify-plugins'        // Plugin packages (for Plugin Daemon)
]

// ============================================================================
// Storage Account
// ============================================================================

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  kind: kind
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    defaultToOAuthAuthentication: false
    publicNetworkAccess: 'Enabled' // Will be restricted after Private Endpoint setup
    networkAcls: {
      defaultAction: 'Allow' // Changed to Deny after Private Endpoint setup
      bypass: 'AzureServices'
      ipRules: []
      virtualNetworkRules: []
    }
    encryption: {
      services: {
        blob: {
          enabled: true
          keyType: 'Account'
        }
        file: {
          enabled: true
          keyType: 'Account'
        }
      }
      keySource: 'Microsoft.Storage'
    }
    accessTier: 'Hot'
    isHnsEnabled: enableHierarchicalNamespace
  }
}

// ============================================================================
// Blob Service Configuration
// ============================================================================

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    cors: {
      corsRules: [
        {
          allowedOrigins: [
            '*'
          ]
          allowedMethods: [
            'GET'
            'HEAD'
            'POST'
            'PUT'
            'DELETE'
            'OPTIONS'
          ]
          maxAgeInSeconds: 3600
          exposedHeaders: [
            '*'
          ]
          allowedHeaders: [
            '*'
          ]
        }
      ]
    }
    deleteRetentionPolicy: {
      enabled: enableBlobSoftDelete
      days: blobSoftDeleteRetentionDays
    }
    containerDeleteRetentionPolicy: {
      enabled: enableContainerSoftDelete
      days: containerSoftDeleteRetentionDays
    }
    isVersioningEnabled: enableVersioning
    changeFeed: {
      enabled: false
    }
  }
}

// ============================================================================
// Blob Containers
// ============================================================================

resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = [for containerName in containerNames: {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: 'None'
    metadata: {}
  }
}]

// ============================================================================
// Outputs
// ============================================================================

@description('Storage Account ID')
output storageAccountId string = storageAccount.id

@description('Storage Account Name')
output storageAccountName string = storageAccount.name

@description('Storage Account Primary Endpoints')
output storageAccountPrimaryEndpoints object = storageAccount.properties.primaryEndpoints

@description('Blob Service Primary Endpoint')
output blobServicePrimaryEndpoint string = storageAccount.properties.primaryEndpoints.blob

@description('Storage Account Primary Access Key')
#disable-next-line outputs-should-not-contain-secrets
output storageAccountPrimaryKey string = storageAccount.listKeys().keys[0].value

@description('Storage Account Secondary Access Key')
#disable-next-line outputs-should-not-contain-secrets
output storageAccountSecondaryKey string = storageAccount.listKeys().keys[1].value

@description('Blob Connection String')
#disable-next-line outputs-should-not-contain-secrets
output blobConnectionString string = 'DefaultEndpointsProtocol=https;AccountName=${storageAccount.name};AccountKey=${storageAccount.listKeys().keys[0].value};EndpointSuffix=${az.environment().suffixes.storage}'

@description('Container Names')
output containerNames array = containerNames
