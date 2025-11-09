// ============================================================================
// nginx Container App Module
// ============================================================================

@description('Environment name (dev/prod)')
param environment string

@description('Azure region')
param location string = resourceGroup().location

@description('Tags')
param tags object = {}

@description('Container Apps Environment ID')
param containerAppsEnvironmentId string

@description('Managed Identity ID')
param managedIdentityId string

@description('nginx Docker image')
param nginxImage string

@description('ACR login server URL')
param acrLoginServer string

@description('ACR admin username')
param acrAdminUsername string

@description('ACR admin password')
@secure()
param acrAdminPassword string

@description('dify-web app name')
param difyWebAppName string

@description('dify-api app name')
param difyApiAppName string

@description('plugin-daemon app name')
param pluginDaemonAppName string = 'plugin_daemon'

// ============================================================================
// nginx Container App
// ============================================================================

resource nginxContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: 'dify-${environment}-nginx'
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
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: [
        {
          name: 'acr-password'
          value: acrAdminPassword
        }
      ]
      registries: [
        {
          server: acrLoginServer
          username: acrAdminUsername
          passwordSecretRef: 'acr-password'
        }
      ]
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
        allowInsecure: true
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'nginx'
          image: nginxImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'DIFY_WEB_HOST'
              value: difyWebAppName
            }
            {
              name: 'DIFY_WEB_PORT'
              value: '80'
            }
            {
              name: 'DIFY_API_HOST'
              value: difyApiAppName
            }
            {
              name: 'DIFY_API_PORT'
              value: '80'
            }
            {
              name: 'DIFY_PLUGIN_DAEMON_HOST'
              value: pluginDaemonAppName
            }
            {
              name: 'DIFY_PLUGIN_DAEMON_PORT'
              value: '80'
            }
          ]
        }
      ]
      scale: {
        minReplicas: environment == 'prod' ? 2 : 1
        maxReplicas: environment == 'prod' ? 10 : 5
        rules: [
          {
            name: 'http-rule'
            http: {
              metadata: {
                concurrentRequests: '100'
              }
            }
          }
        ]
      }
    }
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('nginx Container App ID')
output containerAppId string = nginxContainerApp.id

@description('nginx Container App Name')
output containerAppName string = nginxContainerApp.name

@description('nginx Container App FQDN')
output containerAppFqdn string = nginxContainerApp.properties.configuration.ingress.fqdn
