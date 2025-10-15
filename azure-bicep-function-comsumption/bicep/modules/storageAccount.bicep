@description('Azure region for the Storage account.')
param location string

@description('Globally unique name for the Storage account.')
param name string

@description('Replication SKU for the Storage account.')
param skuName string = 'Standard_LRS'

var storageApiVersion = '2023-01-01'

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: name
  location: location
  sku: {
    name: skuName
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

var primaryKey = listKeys(storage.id, storageApiVersion).keys[0].value
var connectionString = 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${primaryKey};EndpointSuffix=${environment().suffixes.storage}'

@description('Resource ID of the Storage account.')
output id string = storage.id

@description('Name of the Storage account.')
output storageName string = storage.name

@description('Connection string for the Storage account.')
output connectionString string = connectionString
