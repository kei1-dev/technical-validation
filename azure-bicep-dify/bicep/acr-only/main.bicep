// ============================================================================
// ACR Only Deployment - Dify on Azure Infrastructure
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

// ============================================================================
// Module Deployments
// ============================================================================

// Azure Container Registry
module acr 'modules/acr.bicep' = {
  name: 'acr-deployment'
  params: {
    environment: environment
    location: location
    tags: tags
    skuName: 'Basic'
    adminUserEnabled: true
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('ACR Name')
output acrName string = acr.outputs.acrName

@description('ACR Login Server')
output acrLoginServer string = acr.outputs.acrLoginServer
