// ============================================================================
// Production Environment Parameters
// ============================================================================

using '../main.bicep'

// ============================================================================
// Basic Parameters
// ============================================================================

param environment = 'prod'
param location = 'japaneast'

param tags = {
  Environment: 'Production'
  Project: 'Dify'
  ManagedBy: 'Bicep'
  CostCenter: 'Product'
  Criticality: 'High'
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
// Use strong, unique passwords stored in Azure Key Vault or secure password manager
param postgresqlAdminUsername = 'difydbadmin'
param postgresqlAdminPassword = 'CHANGE_ME_VERY_STRONG_PASSWORD_456!'

// Production environment uses General Purpose tier with HA
param postgresqlSkuName = 'Standard_D2s_v3'
param postgresqlStorageSizeGB = 128
param enablePostgresqlHA = true

// ============================================================================
// Redis Parameters
// ============================================================================

// Production environment uses Standard tier with replication
param redisSkuName = 'Standard'
param redisSkuCapacity = 2

// ============================================================================
// Storage Parameters
// ============================================================================

// Production environment uses ZRS (Zone-Redundant Storage)
param storageSkuName = 'Standard_ZRS'
param enableStorageVersioning = true

// ============================================================================
// Key Vault Parameters
// ============================================================================

// IMPORTANT: Set your Azure AD user/service principal Object ID
// You can get this by running: az ad signed-in-user show --query id -o tsv
param keyVaultAdminObjectId = ''

// ============================================================================
// Application Gateway Parameters
// ============================================================================

// Production environment uses WAF_v2 (Web Application Firewall)
param appGatewaySkuName = 'WAF_v2'
param enableWaf = true

// SSL Certificate (required for production)
// IMPORTANT: Upload your SSL certificate to Key Vault first
// Format: https://<keyvault-name>.vault.azure.net/secrets/<secret-name>/<version>
param sslCertificateSecretId = ''

// ============================================================================
// Container Apps Parameters
// ============================================================================

param difyWebImage = 'langgenius/dify-web:0.6.13'
param difyApiImage = 'langgenius/dify-api:0.6.13'
param difyWorkerImage = 'langgenius/dify-api:0.6.13'

// New container images (use specific versions for production)
param sandboxImage = 'langgenius/dify-sandbox:0.2.12'
param ssrfProxyImage = 'ubuntu/squid:latest'
param pluginDaemonImage = 'langgenius/dify-plugin-daemon:0.4.0'

// Security keys for new containers
// IMPORTANT: Generate these keys before deployment using:
// - Sandbox API Key: openssl rand -base64 32
// - Plugin Daemon Key: openssl rand -base64 42
// - Plugin Inner API Key: openssl rand -base64 42
// Store these keys securely in Azure Key Vault or a secure password manager
param sandboxApiKey = 'CHANGE_ME_SANDBOX_API_KEY'
param pluginDaemonKey = 'CHANGE_ME_PLUGIN_DAEMON_KEY'
param pluginInnerApiKey = 'CHANGE_ME_PLUGIN_INNER_API_KEY'

// NOTE: nginxImage, acrName, acrLoginServer, acrAdminUsername, and acrAdminPassword
// are provided by the deployment script and should NOT be set here

// IMPORTANT: Set Dify secret key for production
// Generate a random 64-character hex string
param difySecretKey = 'CHANGE_ME_RANDOM_64_CHAR_HEX_STRING'

// Production environment: min=2 for high availability
param containerAppMinReplicas = 2
param containerAppMaxReplicas = 10
