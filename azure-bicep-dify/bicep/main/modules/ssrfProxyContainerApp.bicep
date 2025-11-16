// ============================================================================
// SSRF Proxy Container App Module - Security Layer for External Requests
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

@description('SSRF Proxy container image')
param ssrfProxyImage string = 'ubuntu/squid:latest'

@description('Sandbox internal FQDN (for reverse proxy configuration)')
param sandboxFqdn string = ''

@description('Container CPU')
param cpu string = '0.25'

@description('Container memory')
param memory string = '0.5Gi'

@description('Minimum replicas')
@minValue(0)
@maxValue(30)
param minReplicas int = 0

@description('Maximum replicas')
@minValue(1)
@maxValue(30)
param maxReplicas int = 3

// ============================================================================
// Variables
// ============================================================================

var proxyPort = 3128
var sandboxPort = 8194

// ============================================================================
// SSRF Proxy Container App
// ============================================================================

resource ssrfProxyContainerApp 'Microsoft.App/containerApps@2023-05-01' = {
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
        targetPort: proxyPort
        transport: 'http'
        allowInsecure: true
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      secrets: []
      registries: []
    }
    template: {
      containers: [
        {
          name: 'ssrf-proxy'
          image: ssrfProxyImage
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: [
            {
              name: 'HTTP_PORT'
              value: string(proxyPort)
            }
            {
              name: 'COREDUMP_DIR'
              value: '/var/spool/squid'
            }
            {
              name: 'REVERSE_PROXY_PORT'
              value: ''  // Empty = reverse proxy disabled (forward proxy only)
            }
            {
              name: 'SANDBOX_HOST'
              value: sandboxFqdn
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

@description('SSRF Proxy Container App ID')
output ssrfProxyContainerAppId string = ssrfProxyContainerApp.id

@description('SSRF Proxy Container App Name')
output ssrfProxyContainerAppName string = ssrfProxyContainerApp.name

@description('SSRF Proxy Container App FQDN')
output ssrfProxyContainerAppFqdn string = ssrfProxyContainerApp.properties.configuration.ingress.fqdn

@description('SSRF Proxy Container App Latest Revision Name')
output ssrfProxyContainerAppLatestRevisionName string = ssrfProxyContainerApp.properties.latestRevisionName
