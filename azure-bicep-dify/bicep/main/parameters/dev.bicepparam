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
param postgresqlAdminPassword = 'DifyDev2025!b5RvI8kIUfMXafm2#Pass'

// Dify Secret Key for encryption (change this to a random 64-character hex string)
param difySecretKey = '332f9ee17eb1b38d651c6c45281d4440fac1d33c59383b372681ae8f7f07129b'

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

// NOTE: nginxImage, acrName, acrLoginServer, acrAdminUsername, and acrAdminPassword
// are provided by the deployment script and should NOT be set here
// TEMPORARY: Adding these parameters for manual deployment
param acrName = 'difyacrdevenqofxlmd5ei6'
param acrLoginServer = 'difyacrdevenqofxlmd5ei6.azurecr.io'
param acrAdminUsername = 'difyacrdevenqofxlmd5ei6'
param acrAdminPassword = 'temppassword'  // Will be overridden by command line
param nginxImage = 'difyacrdevenqofxlmd5ei6.azurecr.io/dify-nginx:latest'

// Dev environment: min=1 to avoid 502 errors (at least 1 replica always running)
param containerAppMinReplicas = 1
param containerAppMaxReplicas = 5
