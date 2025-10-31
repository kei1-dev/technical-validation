// ============================================================================
// Monitoring Module - Log Analytics Workspace & Application Insights
// ============================================================================

@description('Environment name (dev/prod)')
param environment string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Common tags for all resources')
param tags object = {}

@description('Log Analytics Workspace retention in days (30-730)')
@minValue(30)
@maxValue(730)
param logAnalyticsRetentionDays int = 30

@description('Application Insights sampling percentage (0-100)')
@minValue(0)
@maxValue(100)
param appInsightsSamplingPercentage int = 100

// ============================================================================
// Variables
// ============================================================================

var resourceNamePrefix = 'dify-${environment}'

// Log Analytics SKU based on environment
var logAnalyticsSku = environment == 'prod' ? 'PerGB2018' : 'PerGB2018'

// ============================================================================
// Resources
// ============================================================================

// Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${resourceNamePrefix}-law'
  location: location
  tags: tags
  properties: {
    sku: {
      name: logAnalyticsSku
    }
    retentionInDays: logAnalyticsRetentionDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {
      dailyQuotaGb: environment == 'prod' ? -1 : 5 // 5GB daily cap for dev
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// Application Insights
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${resourceNamePrefix}-appinsights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
    SamplingPercentage: appInsightsSamplingPercentage
    RetentionInDays: logAnalyticsRetentionDays
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('Log Analytics Workspace ID')
output logAnalyticsWorkspaceId string = logAnalyticsWorkspace.id

@description('Log Analytics Workspace Name')
output logAnalyticsWorkspaceName string = logAnalyticsWorkspace.name

@description('Log Analytics Workspace Customer ID')
output logAnalyticsCustomerId string = logAnalyticsWorkspace.properties.customerId

@description('Application Insights ID')
output applicationInsightsId string = applicationInsights.id

@description('Application Insights Name')
output applicationInsightsName string = applicationInsights.name

@description('Application Insights Instrumentation Key')
output applicationInsightsInstrumentationKey string = applicationInsights.properties.InstrumentationKey

@description('Application Insights Connection String')
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString

@description('Log Analytics Workspace Primary Shared Key')
#disable-next-line outputs-should-not-contain-secrets
output logAnalyticsWorkspaceKey string = logAnalyticsWorkspace.listKeys().primarySharedKey
