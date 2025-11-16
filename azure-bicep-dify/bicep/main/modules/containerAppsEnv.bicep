// ============================================================================
// Container Apps Environment Module
// ============================================================================

@description('Environment name (dev/prod)')
param environment string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Common tags for all resources')
param tags object = {}

@description('Log Analytics Workspace ID')
param logAnalyticsWorkspaceId string

@description('Log Analytics Workspace Customer ID')
param logAnalyticsCustomerId string

@description('Log Analytics Workspace Primary Shared Key')
@secure()
param logAnalyticsWorkspaceKey string

@description('Virtual Network Subnet ID for Container Apps')
param subnetId string

@description('Enable VNet internal mode (recommended for security)')
param vnetInternal bool = true

@description('Enable zone redundancy (prod only)')
param enableZoneRedundancy bool = false

// ============================================================================
// Variables
// ============================================================================

var resourceNamePrefix = 'dify-${environment}'

// ============================================================================
// Container Apps Environment
// ============================================================================

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${resourceNamePrefix}-containerapp-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsWorkspaceKey
      }
    }
    vnetConfiguration: {
      internal: vnetInternal
      infrastructureSubnetId: subnetId
    }
    zoneRedundant: enableZoneRedundancy
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('Container Apps Environment ID')
output containerAppsEnvironmentId string = containerAppsEnvironment.id

@description('Container Apps Environment Name')
output containerAppsEnvironmentName string = containerAppsEnvironment.name

@description('Container Apps Environment Default Domain')
output containerAppsEnvironmentDefaultDomain string = containerAppsEnvironment.properties.defaultDomain

@description('Container Apps Environment Static IP')
output containerAppsEnvironmentStaticIp string = containerAppsEnvironment.properties.staticIp
