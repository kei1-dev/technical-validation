@description('Name of the Function App.')
param name string

@description('Azure region for the Function App.')
param location string

@description('Resource ID of the hosting plan.')
param serverFarmId string

@description('AzureWebJobsStorage connection string.')
param storageConnectionString string

@allowed([
  'dotnet-isolated'
  'node'
  'powershell'
  'python'
  'java'
])
@description('Azure Functions worker runtime.')
param workerRuntime string

@description('Maximum instance count for scaling.')
param maximumInstanceCount int = 100

@description('Instance memory in MB (2048, 4096).')
param instanceMemoryMB int = 2048

@description('Always ready instances.')
param alwaysReadyInstances int = 0

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: name
  location: location
  kind: 'functionapp,linux'
  properties: {
    serverFarmId: serverFarmId
    httpsOnly: true
    functionAppConfig: {
      deployment: {
        storage: {
          type: 'blobContainer'
          value: storageConnectionString
          authentication: {
            type: 'StorageAccountConnectionString'
            storageAccountConnectionStringName: 'AzureWebJobsStorage'
          }
        }
      }
      scaleAndConcurrency: {
        maximumInstanceCount: maximumInstanceCount
        instanceMemoryMB: instanceMemoryMB
        alwaysReady: [
          {
            name: 'http'
            instanceCount: alwaysReadyInstances
          }
        ]
      }
      runtime: {
        name: workerRuntime
        version: workerRuntime == 'python' ? '3.11' : (workerRuntime == 'node' ? '20' : (workerRuntime == 'dotnet-isolated' ? '8' : '7'))
      }
    }
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: storageConnectionString
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
      ]
    }
  }
}

@description('Name of the Function App.')
output functionAppName string = functionApp.name

@description('Default hostname of the Function App.')
output defaultHostName string = functionApp.properties.defaultHostName

@description('Resource ID of the Function App.')
output id string = functionApp.id
