@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Globally unique name for the Storage account.')
param storageAccountName string

@description('Globally unique name for the Function App.')
param functionAppName string

@allowed([
  'dotnet-isolated'
  'node'
  'powershell'
  'python'
  'java'
])
@description('Azure Functions worker runtime.')
param functionsWorkerRuntime string = 'python'

@description('Maximum instance count for scaling.')
param maximumInstanceCount int = 100

@description('Instance memory in MB (2048, 4096).')
param instanceMemoryMB int = 2048

@description('Always ready instances.')
param alwaysReadyInstances int = 0

var storageSku = 'Standard_LRS'
var hostingPlanName = '${functionAppName}-plan'

module storageModule 'modules/storageAccount.bicep' = {
  name: 'storage'
  params: {
    location: location
    name: storageAccountName
    skuName: storageSku
  }
}

resource hostingPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: hostingPlanName
  location: location
  kind: 'functionapp'
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
  }
  properties: {
    reserved: true
  }
}

module functionModule 'modules/functionAppFlexConsumption.bicep' = {
  name: 'function'
  params: {
    name: functionAppName
    location: location
    serverFarmId: hostingPlan.id
    storageConnectionString: storageModule.outputs.connectionString
    workerRuntime: functionsWorkerRuntime
    maximumInstanceCount: maximumInstanceCount
    instanceMemoryMB: instanceMemoryMB
    alwaysReadyInstances: alwaysReadyInstances
  }
}

@description('Name of the Function App.')
output functionAppName string = functionModule.outputs.functionAppName

@description('Endpoint for the Function App.')
output functionAppDefaultHostname string = functionModule.outputs.defaultHostName

@description('Storage account name.')
output storageAccountName string = storageModule.outputs.storageName
