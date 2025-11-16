// ============================================================================
// Sandbox Container App Module - Code Execution Environment
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

@description('Sandbox container image')
param sandboxImage string = 'langgenius/dify-sandbox:0.2.12'

@description('Sandbox API key for authentication')
@secure()
param sandboxApiKey string

@description('SSRF Proxy internal FQDN for HTTP proxy')
param ssrfProxyFqdn string

@description('Container CPU')
param cpu string = '0.5'

@description('Container memory')
param memory string = '1.0Gi'

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

var sandboxPort = 8194
var httpProxyUrl = 'http://${ssrfProxyFqdn}:3128'

// ============================================================================
// Sandbox Container App
// ============================================================================

resource sandboxContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
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
        targetPort: sandboxPort
        transport: 'http'
        allowInsecure: true
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      secrets: [
        {
          name: 'sandbox-api-key'
          value: sandboxApiKey
        }
      ]
      registries: []
    }
    template: {
      containers: [
        {
          name: 'sandbox'
          image: sandboxImage
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: [
            {
              name: 'API_KEY'
              secretRef: 'sandbox-api-key'
            }
            {
              name: 'GIN_MODE'
              value: 'release'
            }
            {
              name: 'WORKER_TIMEOUT'
              value: '15'
            }
            {
              name: 'ENABLE_NETWORK'
              value: 'true'
            }
            {
              name: 'HTTP_PROXY'
              value: httpProxyUrl
            }
            {
              name: 'HTTPS_PROXY'
              value: httpProxyUrl
            }
            {
              name: 'SANDBOX_PORT'
              value: string(sandboxPort)
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

@description('Sandbox Container App ID')
output sandboxContainerAppId string = sandboxContainerApp.id

@description('Sandbox Container App Name')
output sandboxContainerAppName string = sandboxContainerApp.name

@description('Sandbox Container App FQDN')
output sandboxContainerAppFqdn string = sandboxContainerApp.properties.configuration.ingress.fqdn

@description('Sandbox Container App Latest Revision Name')
output sandboxContainerAppLatestRevisionName string = sandboxContainerApp.properties.latestRevisionName
