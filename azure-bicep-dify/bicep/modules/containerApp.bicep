// ============================================================================
// Container App Module - Reusable Container App Configuration
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

@description('Container image (e.g., langgenius/dify-web:latest)')
param containerImage string

@description('Container port')
param containerPort int = 3000

@description('Container CPU (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)')
param cpu string = '0.5'

@description('Container memory (0.5Gi, 1.0Gi, 1.5Gi, 2.0Gi, 3.0Gi, 4.0Gi)')
param memory string = '1.0Gi'

@description('Minimum replicas (0-30)')
@minValue(0)
@maxValue(30)
param minReplicas int = 0

@description('Maximum replicas (1-30)')
@minValue(1)
@maxValue(30)
param maxReplicas int = 5

@description('Enable ingress')
param enableIngress bool = true

@description('Ingress external mode (false = internal only)')
param ingressExternal bool = false

@description('Environment variables')
param environmentVariables array = []

@description('Secrets for the Container App')
param secrets array = []

@description('Scale rules for auto-scaling')
param scaleRules array = []

// ============================================================================
// Container App
// ============================================================================

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
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
      ingress: enableIngress ? {
        external: ingressExternal
        targetPort: containerPort
        transport: 'http'
        allowInsecure: true
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      } : null
      secrets: secrets
      registries: []
    }
    template: {
      containers: [
        {
          name: containerAppName
          image: containerImage
          resources: {
            cpu: json(cpu)
            memory: memory
          }
          env: environmentVariables
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: scaleRules
      }
    }
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('Container App ID')
output containerAppId string = containerApp.id

@description('Container App Name')
output containerAppName string = containerApp.name

@description('Container App FQDN (if ingress enabled)')
output containerAppFqdn string = enableIngress ? containerApp.properties.configuration.ingress.fqdn : ''

@description('Container App Latest Revision Name')
output containerAppLatestRevisionName string = containerApp.properties.latestRevisionName

@description('Container App Latest Revision FQDN')
output containerAppLatestRevisionFqdn string = containerApp.properties.latestRevisionFqdn
