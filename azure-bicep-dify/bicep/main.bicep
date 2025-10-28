// ============================================================================
// Main Orchestration - Dify on Azure Infrastructure
// ============================================================================

targetScope = 'resourceGroup'

// ============================================================================
// Parameters
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
param tags object = {
  Environment: environment
  Project: 'Dify'
  ManagedBy: 'Bicep'
}

// Network Parameters
@description('Virtual Network address prefix')
param vnetAddressPrefix string = '10.0.0.0/16'

@description('Application Gateway subnet address prefix')
param appGatewaySubnetPrefix string = '10.0.0.0/24'

@description('Container Apps subnet address prefix')
param containerAppsSubnetPrefix string = '10.0.1.0/24'

@description('Private Endpoint subnet address prefix')
param privateEndpointSubnetPrefix string = '10.0.2.0/24'

// Database Parameters
@description('PostgreSQL administrator username')
param postgresqlAdminUsername string

@description('PostgreSQL administrator password')
@secure()
param postgresqlAdminPassword string

@description('PostgreSQL SKU name')
param postgresqlSkuName string = environment == 'prod' ? 'Standard_D2s_v3' : 'Standard_B1ms'

@description('PostgreSQL storage size in GB')
param postgresqlStorageSizeGB int = environment == 'prod' ? 128 : 32

@description('Enable PostgreSQL high availability')
param enablePostgresqlHA bool = environment == 'prod'

// Redis Parameters
@description('Redis SKU name')
param redisSkuName string = environment == 'prod' ? 'Standard' : 'Basic'

@description('Redis SKU capacity')
param redisSkuCapacity int = environment == 'prod' ? 2 : 1

// Storage Parameters
@description('Storage SKU name')
param storageSkuName string = environment == 'prod' ? 'Standard_ZRS' : 'Standard_LRS'

@description('Enable storage versioning')
param enableStorageVersioning bool = environment == 'prod'

// Key Vault Parameters
@description('Object ID of the admin user for Key Vault access')
param keyVaultAdminObjectId string = ''

// Application Gateway Parameters
@description('Application Gateway SKU')
param appGatewaySkuName string = environment == 'prod' ? 'WAF_v2' : 'Standard_v2'

@description('Enable WAF')
param enableWaf bool = environment == 'prod'

@description('SSL certificate secret ID in Key Vault (optional)')
param sslCertificateSecretId string = ''

// Container Apps Parameters
@description('Dify Web container image')
param difyWebImage string = 'langgenius/dify-web:latest'

@description('Dify API container image')
param difyApiImage string = 'langgenius/dify-api:latest'

@description('Dify Worker container image')
param difyWorkerImage string = 'langgenius/dify-api:latest'

@description('Min replicas for Container Apps')
param containerAppMinReplicas int = environment == 'prod' ? 2 : 0

@description('Max replicas for Container Apps')
param containerAppMaxReplicas int = environment == 'prod' ? 10 : 5

// ============================================================================
// Module Deployments
// ============================================================================

// 1. Monitoring (Foundation)
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring-deployment'
  params: {
    environment: environment
    location: location
    tags: tags
    logAnalyticsRetentionDays: environment == 'prod' ? 90 : 30
    appInsightsSamplingPercentage: environment == 'prod' ? 100 : 50
  }
}

// 2. Network (Foundation)
module network 'modules/network.bicep' = {
  name: 'network-deployment'
  params: {
    environment: environment
    location: location
    tags: tags
    vnetAddressPrefix: vnetAddressPrefix
    appGatewaySubnetPrefix: appGatewaySubnetPrefix
    containerAppsSubnetPrefix: containerAppsSubnetPrefix
    privateEndpointSubnetPrefix: privateEndpointSubnetPrefix
  }
}

// 3. Key Vault & Managed Identities
module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault-deployment'
  params: {
    environment: environment
    location: location
    tags: tags
    adminObjectId: keyVaultAdminObjectId
    enableSoftDelete: true
    softDeleteRetentionDays: environment == 'prod' ? 90 : 30
    enablePurgeProtection: environment == 'prod'
  }
}

// 4. Data Layer - PostgreSQL
module postgresql 'modules/postgresql.bicep' = {
  name: 'postgresql-deployment'
  params: {
    environment: environment
    location: location
    tags: tags
    administratorLogin: postgresqlAdminUsername
    administratorPassword: postgresqlAdminPassword
    skuName: postgresqlSkuName
    storageSizeGB: postgresqlStorageSizeGB
    enableHighAvailability: enablePostgresqlHA
    backupRetentionDays: environment == 'prod' ? 30 : 7
    enableGeoRedundantBackup: environment == 'prod'
  }
}

// 5. Data Layer - Redis
module redis 'modules/redis.bicep' = {
  name: 'redis-deployment'
  params: {
    environment: environment
    location: location
    tags: tags
    skuFamily: redisSkuName == 'Premium' ? 'P' : 'C'
    skuName: redisSkuName
    skuCapacity: redisSkuCapacity
    enableNonSslPort: false
  }
}

// 6. Data Layer - Storage
module storage 'modules/storage.bicep' = {
  name: 'storage-deployment'
  params: {
    environment: environment
    location: location
    tags: tags
    skuName: storageSkuName
    enableVersioning: enableStorageVersioning
    enableBlobSoftDelete: environment == 'prod'
    blobSoftDeleteRetentionDays: environment == 'prod' ? 30 : 7
    enableContainerSoftDelete: environment == 'prod'
    containerSoftDeleteRetentionDays: environment == 'prod' ? 30 : 7
  }
}

// 7. Private DNS Zones
module privateDnsZonePostgres 'modules/privateDnsZone.bicep' = {
  name: 'privateDnsZonePostgres-deployment'
  params: {
    privateDnsZoneName: 'privatelink.postgres.database.azure.com'
    vnetId: network.outputs.vnetId
    tags: tags
  }
}

module privateDnsZoneRedis 'modules/privateDnsZone.bicep' = {
  name: 'privateDnsZoneRedis-deployment'
  params: {
    privateDnsZoneName: 'privatelink.redis.cache.windows.net'
    vnetId: network.outputs.vnetId
    tags: tags
  }
}

module privateDnsZoneBlob 'modules/privateDnsZone.bicep' = {
  name: 'privateDnsZoneBlob-deployment'
  params: {
    privateDnsZoneName: 'privatelink.blob.${az.environment().suffixes.storage}'
    vnetId: network.outputs.vnetId
    tags: tags
  }
}

module privateDnsZoneKeyVault 'modules/privateDnsZone.bicep' = {
  name: 'privateDnsZoneKeyVault-deployment'
  params: {
    privateDnsZoneName: 'privatelink.vaultcore.azure.net'
    vnetId: network.outputs.vnetId
    tags: tags
  }
}

module privateDnsZoneContainerApps 'modules/privateDnsZone.bicep' = {
  name: 'privateDnsZoneContainerApps-deployment'
  params: {
    privateDnsZoneName: containerAppsEnv.outputs.containerAppsEnvironmentDefaultDomain
    vnetId: network.outputs.vnetId
    tags: tags
  }
  dependsOn: [
    containerAppsEnv
  ]
}

// Wildcard DNS A Record for Container Apps (enables name resolution for all apps)
module containerAppsDnsRecord 'modules/privateDnsRecord.bicep' = {
  name: 'containerAppsDnsRecord-deployment'
  params: {
    privateDnsZoneName: containerAppsEnv.outputs.containerAppsEnvironmentDefaultDomain
    recordName: '*'
    ipAddress: containerAppsEnv.outputs.containerAppsEnvironmentStaticIp
    tags: tags
  }
  dependsOn: [
    privateDnsZoneContainerApps
  ]
}

// 8. Private Endpoints
module privateEndpointPostgres 'modules/privateEndpoint.bicep' = {
  name: 'privateEndpointPostgres-deployment'
  params: {
    privateEndpointName: 'dify-${environment}-postgres-pe'
    location: location
    tags: tags
    subnetId: network.outputs.privateEndpointSubnetId
    privateLinkServiceId: postgresql.outputs.postgresqlServerId
    groupIds: ['postgresqlServer']
    privateDnsZoneIds: [privateDnsZonePostgres.outputs.privateDnsZoneId]
  }
  dependsOn: [
    postgresql
    privateDnsZonePostgres
  ]
}

module privateEndpointRedis 'modules/privateEndpoint.bicep' = {
  name: 'privateEndpointRedis-deployment'
  params: {
    privateEndpointName: 'dify-${environment}-redis-pe'
    location: location
    tags: tags
    subnetId: network.outputs.privateEndpointSubnetId
    privateLinkServiceId: redis.outputs.redisId
    groupIds: ['redisCache']
    privateDnsZoneIds: [privateDnsZoneRedis.outputs.privateDnsZoneId]
  }
  dependsOn: [
    redis
    privateDnsZoneRedis
  ]
}

module privateEndpointBlob 'modules/privateEndpoint.bicep' = {
  name: 'privateEndpointBlob-deployment'
  params: {
    privateEndpointName: 'dify-${environment}-blob-pe'
    location: location
    tags: tags
    subnetId: network.outputs.privateEndpointSubnetId
    privateLinkServiceId: storage.outputs.storageAccountId
    groupIds: ['blob']
    privateDnsZoneIds: [privateDnsZoneBlob.outputs.privateDnsZoneId]
  }
  dependsOn: [
    storage
    privateDnsZoneBlob
  ]
}

module privateEndpointKeyVault 'modules/privateEndpoint.bicep' = {
  name: 'privateEndpointKeyVault-deployment'
  params: {
    privateEndpointName: 'dify-${environment}-keyvault-pe'
    location: location
    tags: tags
    subnetId: network.outputs.privateEndpointSubnetId
    privateLinkServiceId: keyvault.outputs.keyVaultId
    groupIds: ['vault']
    privateDnsZoneIds: [privateDnsZoneKeyVault.outputs.privateDnsZoneId]
  }
  dependsOn: [
    keyvault
    privateDnsZoneKeyVault
  ]
}

// 9. Container Apps Environment
module containerAppsEnv 'modules/containerAppsEnv.bicep' = {
  name: 'containerAppsEnv-deployment'
  params: {
    environment: environment
    location: location
    tags: tags
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    logAnalyticsCustomerId: monitoring.outputs.logAnalyticsCustomerId
    logAnalyticsWorkspaceKey: monitoring.outputs.logAnalyticsWorkspaceKey
    subnetId: network.outputs.containerAppsSubnetId
    vnetInternal: true
    enableZoneRedundancy: environment == 'prod'
  }
}

// 10. Container Apps - Dify Web
module containerAppWeb 'modules/containerApp.bicep' = {
  name: 'containerAppWeb-deployment'
  params: {
    containerAppName: 'dify-${environment}-web'
    location: location
    tags: tags
    containerAppsEnvironmentId: containerAppsEnv.outputs.containerAppsEnvironmentId
    managedIdentityId: keyvault.outputs.containerAppsIdentityId
    containerImage: difyWebImage
    containerPort: 3000
    cpu: '0.5'
    memory: '1.0Gi'
    minReplicas: containerAppMinReplicas
    maxReplicas: containerAppMaxReplicas
    enableIngress: true
    ingressExternal: true
    environmentVariables: [
      {
        name: 'CONSOLE_API_URL'
        value: 'https://dify-${environment}-api.${containerAppsEnv.outputs.containerAppsEnvironmentDefaultDomain}'
      }
      {
        name: 'APP_API_URL'
        value: 'https://dify-${environment}-api.${containerAppsEnv.outputs.containerAppsEnvironmentDefaultDomain}'
      }
    ]
    scaleRules: [
      {
        name: 'http-scale'
        http: {
          metadata: {
            concurrentRequests: '10'
          }
        }
      }
    ]
  }
  dependsOn: [
    containerAppsEnv
    keyvault
  ]
}

// 11. Container Apps - Dify API
module containerAppApi 'modules/containerApp.bicep' = {
  name: 'containerAppApi-deployment'
  params: {
    containerAppName: 'dify-${environment}-api'
    location: location
    tags: tags
    containerAppsEnvironmentId: containerAppsEnv.outputs.containerAppsEnvironmentId
    managedIdentityId: keyvault.outputs.containerAppsIdentityId
    containerImage: difyApiImage
    containerPort: 5001
    cpu: '1.0'
    memory: '2.0Gi'
    minReplicas: containerAppMinReplicas
    maxReplicas: containerAppMaxReplicas
    enableIngress: true
    ingressExternal: true
    environmentVariables: [
      {
        name: 'MODE'
        value: 'api'
      }
      {
        name: 'DB_HOST'
        value: postgresql.outputs.postgresqlServerFqdn
      }
      {
        name: 'DB_PORT'
        value: '5432'
      }
      {
        name: 'DB_USERNAME'
        value: postgresqlAdminUsername
      }
      {
        name: 'DB_DATABASE'
        value: postgresql.outputs.postgresqlDatabaseName
      }
      {
        name: 'REDIS_HOST'
        value: redis.outputs.redisHostName
      }
      {
        name: 'REDIS_PORT'
        value: string(redis.outputs.redisSslPort)
      }
      {
        name: 'REDIS_USE_SSL'
        value: 'true'
      }
      {
        name: 'STORAGE_TYPE'
        value: 'azure-blob'
      }
      {
        name: 'AZURE_BLOB_ACCOUNT_NAME'
        value: storage.outputs.storageAccountName
      }
      {
        name: 'AZURE_BLOB_CONTAINER_NAME'
        value: 'dify-app-storage'
      }
    ]
    scaleRules: [
      {
        name: 'http-scale'
        http: {
          metadata: {
            concurrentRequests: '20'
          }
        }
      }
    ]
  }
  dependsOn: [
    containerAppsEnv
    keyvault
    postgresql
    redis
    storage
    privateEndpointPostgres
    privateEndpointRedis
    privateEndpointBlob
  ]
}

// 12. Container Apps - Dify Worker
module containerAppWorker 'modules/containerApp.bicep' = {
  name: 'containerAppWorker-deployment'
  params: {
    containerAppName: 'dify-${environment}-worker'
    location: location
    tags: tags
    containerAppsEnvironmentId: containerAppsEnv.outputs.containerAppsEnvironmentId
    managedIdentityId: keyvault.outputs.containerAppsIdentityId
    containerImage: difyWorkerImage
    containerPort: 5001
    cpu: '1.0'
    memory: '2.0Gi'
    minReplicas: containerAppMinReplicas
    maxReplicas: containerAppMaxReplicas
    enableIngress: false
    environmentVariables: [
      {
        name: 'MODE'
        value: 'worker'
      }
      {
        name: 'DB_HOST'
        value: postgresql.outputs.postgresqlServerFqdn
      }
      {
        name: 'DB_PORT'
        value: '5432'
      }
      {
        name: 'DB_USERNAME'
        value: postgresqlAdminUsername
      }
      {
        name: 'DB_DATABASE'
        value: postgresql.outputs.postgresqlDatabaseName
      }
      {
        name: 'REDIS_HOST'
        value: redis.outputs.redisHostName
      }
      {
        name: 'REDIS_PORT'
        value: string(redis.outputs.redisSslPort)
      }
      {
        name: 'REDIS_USE_SSL'
        value: 'true'
      }
      {
        name: 'STORAGE_TYPE'
        value: 'azure-blob'
      }
      {
        name: 'AZURE_BLOB_ACCOUNT_NAME'
        value: storage.outputs.storageAccountName
      }
      {
        name: 'AZURE_BLOB_CONTAINER_NAME'
        value: 'dify-app-storage'
      }
    ]
    scaleRules: []
  }
  dependsOn: [
    containerAppsEnv
    keyvault
    postgresql
    redis
    storage
    privateEndpointPostgres
    privateEndpointRedis
    privateEndpointBlob
  ]
}

// 13. Application Gateway
module applicationGateway 'modules/applicationGateway.bicep' = {
  name: 'applicationGateway-deployment'
  params: {
    environment: environment
    location: location
    tags: tags
    subnetId: network.outputs.appGatewaySubnetId
    skuName: appGatewaySkuName
    enableWaf: enableWaf
    minCapacity: environment == 'prod' ? 2 : 1
    maxCapacity: environment == 'prod' ? 10 : 5
    managedIdentityId: keyvault.outputs.appGatewayIdentityId
    backendFqdnWeb: containerAppWeb.outputs.containerAppFqdn
    backendFqdnApi: containerAppApi.outputs.containerAppFqdn
    containerAppsStaticIp: containerAppsEnv.outputs.containerAppsEnvironmentStaticIp
    sslCertificateSecretId: sslCertificateSecretId
  }
  dependsOn: [
    network
    keyvault
    containerAppWeb
    containerAppApi
  ]
}

// ============================================================================
// Outputs
// ============================================================================

@description('Application Gateway Public IP Address')
output applicationGatewayPublicIp string = applicationGateway.outputs.publicIpAddress

@description('Application Gateway FQDN')
output applicationGatewayFqdn string = applicationGateway.outputs.publicIpFqdn

@description('Dify Web App FQDN')
output difyWebFqdn string = containerAppWeb.outputs.containerAppFqdn

@description('Dify API App FQDN')
output difyApiFqdn string = containerAppApi.outputs.containerAppFqdn

@description('PostgreSQL Server FQDN')
output postgresqlServerFqdn string = postgresql.outputs.postgresqlServerFqdn

@description('Redis Host Name')
output redisHostName string = redis.outputs.redisHostName

@description('Storage Account Name')
output storageAccountName string = storage.outputs.storageAccountName

@description('Key Vault Name')
output keyVaultName string = keyvault.outputs.keyVaultName

@description('Log Analytics Workspace Name')
output logAnalyticsWorkspaceName string = monitoring.outputs.logAnalyticsWorkspaceName

@description('Application Insights Name')
output applicationInsightsName string = monitoring.outputs.applicationInsightsName
