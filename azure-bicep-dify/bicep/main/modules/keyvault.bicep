// ============================================================================
// Key Vault Module - Key Vault & Managed Identities
// ============================================================================

@description('Environment name (dev/prod)')
param environment string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Common tags for all resources')
param tags object = {}

@description('Tenant ID for Key Vault access policies')
param tenantId string = subscription().tenantId

@description('Object ID of the user/service principal for admin access')
param adminObjectId string = ''

@description('Enable soft delete (recommended for production)')
param enableSoftDelete bool = true

@description('Soft delete retention days (7-90)')
@minValue(7)
@maxValue(90)
param softDeleteRetentionDays int = 90

@description('Enable purge protection (required for production)')
param enablePurgeProtection bool = false

// ============================================================================
// Variables
// ============================================================================

var resourceNamePrefix = 'dify-${environment}'

// Key Vault name must be globally unique and max 24 characters
var keyVaultName = take('${resourceNamePrefix}-kv-${uniqueString(resourceGroup().id)}', 24)

// ============================================================================
// Managed Identities
// ============================================================================

// Managed Identity for Application Gateway (for certificate access)
resource appGatewayIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${resourceNamePrefix}-appgateway-identity'
  location: location
  tags: tags
}

// Managed Identity for Container Apps (for resource access)
resource containerAppsIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${resourceNamePrefix}-containerapps-identity'
  location: location
  tags: tags
}

// ============================================================================
// Key Vault
// ============================================================================

resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: union({
    tenantId: tenantId
    sku: {
      family: 'A'
      name: environment == 'prod' ? 'premium' : 'standard'
    }
    enabledForDeployment: true
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: true
    enableSoftDelete: enableSoftDelete
    softDeleteRetentionInDays: softDeleteRetentionDays
    enableRbacAuthorization: true
    publicNetworkAccess: 'Enabled' // Will be restricted via Private Endpoint
    networkAcls: {
      defaultAction: 'Allow' // Changed to Deny after Private Endpoint setup
      bypass: 'AzureServices'
      ipRules: []
      virtualNetworkRules: []
    }
  }, enablePurgeProtection ? { enablePurgeProtection: true } : {})
}

// ============================================================================
// Outputs
// ============================================================================

@description('Key Vault ID')
output keyVaultId string = keyVault.id

@description('Key Vault Name')
output keyVaultName string = keyVault.name

@description('Key Vault URI')
output keyVaultUri string = keyVault.properties.vaultUri

@description('Application Gateway Managed Identity ID')
output appGatewayIdentityId string = appGatewayIdentity.id

@description('Application Gateway Managed Identity Principal ID')
output appGatewayIdentityPrincipalId string = appGatewayIdentity.properties.principalId

@description('Application Gateway Managed Identity Client ID')
output appGatewayIdentityClientId string = appGatewayIdentity.properties.clientId

@description('Container Apps Managed Identity ID')
output containerAppsIdentityId string = containerAppsIdentity.id

@description('Container Apps Managed Identity Principal ID')
output containerAppsIdentityPrincipalId string = containerAppsIdentity.properties.principalId

@description('Container Apps Managed Identity Client ID')
output containerAppsIdentityClientId string = containerAppsIdentity.properties.clientId
