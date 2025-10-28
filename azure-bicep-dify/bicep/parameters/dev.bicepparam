// ============================================================================
// Development Environment Parameters
// ============================================================================

using '../main.bicep'

// ============================================================================
// Basic Parameters
// ============================================================================

param environment = 'dev'
param location = 'japaneast'

param tags = {
  Environment: 'Development'
  Project: 'Dify'
  ManagedBy: 'Bicep'
  CostCenter: 'Engineering'
}

// ============================================================================
// Network Parameters
// ============================================================================

param vnetAddressPrefix = '10.0.0.0/16'
param appGatewaySubnetPrefix = '10.0.0.0/24'
param containerAppsSubnetPrefix = '10.0.1.0/24'
param privateEndpointSubnetPrefix = '10.0.2.0/24'

// ============================================================================
// Database Parameters
// ============================================================================

// IMPORTANT: Change these values before deployment
param postgresqlAdminUsername = 'difydbadmin'
param postgresqlAdminPassword = 'DifyDev2025!Secure#Pass'

// Dev environment uses Burstable tier for cost optimization
param postgresqlSkuName = 'Standard_B1ms'
param postgresqlStorageSizeGB = 32
param enablePostgresqlHA = false

// ============================================================================
// Redis Parameters
// ============================================================================

// Dev environment uses Basic tier
param redisSkuName = 'Basic'
param redisSkuCapacity = 1

// ============================================================================
// Storage Parameters
// ============================================================================

// Dev environment uses LRS (Locally Redundant Storage)
param storageSkuName = 'Standard_LRS'
param enableStorageVersioning = false

// ============================================================================
// Key Vault Parameters
// ============================================================================

// IMPORTANT: Set your Azure AD user/service principal Object ID
// You can get this by running: az ad signed-in-user show --query id -o tsv
param keyVaultAdminObjectId = '4f9f1e37-e388-4537-a414-aa967b145350'

// ============================================================================
// Application Gateway Parameters
// ============================================================================

// Dev environment uses Standard_v2 (no WAF)
param appGatewaySkuName = 'Standard_v2'
param enableWaf = false

// SSL Certificate (optional, leave empty for HTTP-only)
param sslCertificateSecretId = ''

// ============================================================================
// Container Apps Parameters
// ============================================================================

param difyWebImage = 'langgenius/dify-web:latest'
param difyApiImage = 'langgenius/dify-api:latest'
param difyWorkerImage = 'langgenius/dify-api:latest'

// Dev environment: min=0 for cost savings (scale to zero)
param containerAppMinReplicas = 0
param containerAppMaxReplicas = 5
