// ============================================================================
// Plugin Daemon Container App Module - Plugin Management and Execution
// ============================================================================

@description('Container App name')
param containerAppName string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Common tags for all resources')
param tags object = {}

@description('Container Apps Environment ID')
param containerAppsEnvironmentId string

@description('Managed Identity ID for the Container App')
param managedIdentityId string

@description('Plugin Daemon container image')
param pluginDaemonImage string = 'langgenius/dify-plugin-daemon:0.4.0'

@description('PostgreSQL server FQDN')
param postgresServerFqdn string

@description('PostgreSQL admin username')
param postgresAdminUsername string

@description('PostgreSQL admin password')
@secure()
param postgresAdminPassword string

@description('Redis hostname')
param redisHostname string

@description('Redis port')
param redisPort string

@description('Redis password')
@secure()
param redisPassword string

@description('Redis use SSL')
param redisUseSsl bool = true

@description('Plugin Daemon server key for authentication')
@secure()
param pluginDaemonKey string

@description('Plugin inner API key for communication with Dify API')
@secure()
param pluginInnerApiKey string

@description('Dify API internal FQDN')
param difyApiFqdn string

@description('Azure Blob Storage connection string')
@secure()
param storageConnectionString string

@description('Container CPU')
param cpu string = '1.0'

@description('Container memory')
param memory string = '2.0Gi'

@description('Minimum replicas')
@minValue(0)
@maxValue(30)
param minReplicas int = 0

@description('Maximum replicas')
@minValue(1)
@maxValue(30)
param maxReplicas int = 5

// ============================================================================
// Variables
// ============================================================================

var pluginDaemonPort = 5002
var pluginDebugPort = 5003
var pluginDatabaseName = 'dify_plugin'

// ============================================================================
// Plugin Daemon Container App
// ============================================================================

resource pluginDaemonContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: containerAppName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false  // Internal only
        targetPort: pluginDaemonPort
        transport: 'http'
        allowInsecure: true
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
        // exposedPort can only be used with external: true and transport: tcp
        // Disabled for now as plugin daemon is internal-only
        // exposedPort: pluginDebugPort  // Remote debugging port
      }
      secrets: [
        {
          name: 'db-password'
          value: postgresAdminPassword
        }
        {
          name: 'redis-password'
          value: redisPassword
        }
        {
          name: 'plugin-daemon-key'
          value: pluginDaemonKey
        }
        {
          name: 'plugin-inner-api-key'
          value: pluginInnerApiKey
        }
        {
          name: 'storage-connection-string'
          value: storageConnectionString
        }
      ]
      registries: []
    }
    template: {
      containers: [
        {
          name: 'plugin-daemon'
          image: pluginDaemonImage
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: [
            // Database configuration (separate database)
            {
              name: 'DB_HOST'
              value: postgresServerFqdn
            }
            {
              name: 'DB_PORT'
              value: '5432'
            }
            {
              name: 'DB_USERNAME'
              value: postgresAdminUsername
            }
            {
              name: 'DB_PASSWORD'
              secretRef: 'db-password'
            }
            {
              name: 'DB_DATABASE'
              value: pluginDatabaseName
            }
            // Redis configuration
            {
              name: 'REDIS_HOST'
              value: redisHostname
            }
            {
              name: 'REDIS_PORT'
              value: redisPort
            }
            {
              name: 'REDIS_PASSWORD'
              secretRef: 'redis-password'
            }
            {
              name: 'REDIS_USE_SSL'
              value: string(redisUseSsl)
            }
            // Plugin Daemon configuration
            {
              name: 'SERVER_PORT'
              value: string(pluginDaemonPort)
            }
            {
              name: 'SERVER_KEY'
              secretRef: 'plugin-daemon-key'
            }
            {
              name: 'MAX_PLUGIN_PACKAGE_SIZE'
              value: '52428800'  // 50MB
            }
            {
              name: 'PPROF_ENABLED'
              value: 'false'
            }
            // Dify API integration
            {
              name: 'DIFY_INNER_API_URL'
              value: 'http://${difyApiFqdn}'
            }
            {
              name: 'DIFY_INNER_API_KEY'
              secretRef: 'plugin-inner-api-key'
            }
            // Remote debugging
            {
              name: 'PLUGIN_REMOTE_INSTALLING_HOST'
              value: '0.0.0.0'
            }
            {
              name: 'PLUGIN_REMOTE_INSTALLING_PORT'
              value: string(pluginDebugPort)
            }
            // Plugin storage (Azure Blob)
            {
              name: 'PLUGIN_STORAGE_TYPE'
              value: 'azure_blob'
            }
            {
              name: 'AZURE_BLOB_STORAGE_CONNECTION_STRING'
              secretRef: 'storage-connection-string'
            }
            {
              name: 'AZURE_BLOB_STORAGE_CONTAINER_NAME'
              value: 'dify-plugins'
            }
            // Plugin execution
            {
              name: 'PLUGIN_WORKING_PATH'
              value: '/app/storage/cwd'
            }
            {
              name: 'FORCE_VERIFYING_SIGNATURE'
              value: 'true'
            }
            {
              name: 'PYTHON_ENV_INIT_TIMEOUT'
              value: '120'
            }
            {
              name: 'PLUGIN_MAX_EXECUTION_TIMEOUT'
              value: '600'
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('Plugin Daemon Container App ID')
output pluginDaemonContainerAppId string = pluginDaemonContainerApp.id

@description('Plugin Daemon Container App Name')
output pluginDaemonContainerAppName string = pluginDaemonContainerApp.name

@description('Plugin Daemon Container App FQDN')
output pluginDaemonContainerAppFqdn string = pluginDaemonContainerApp.properties.configuration.ingress.fqdn

@description('Plugin Daemon Container App Latest Revision Name')
output pluginDaemonContainerAppLatestRevisionName string = pluginDaemonContainerApp.properties.latestRevisionName
