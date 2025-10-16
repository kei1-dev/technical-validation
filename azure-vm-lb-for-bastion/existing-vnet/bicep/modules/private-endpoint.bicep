@description('Azure region for the Private Endpoint.')
param location string = resourceGroup().location

@description('Name of the Private Endpoint.')
param peName string

@description('Resource ID of the subnet for the Private Endpoint.')
param subnetId string

@description('Resource ID of the Private Link Service to connect to.')
param privateLinkServiceId string

@description('Group IDs for the Private Link Service (typically empty for custom PLS).')
param groupIds array = []

@description('Request message for manual approval (optional).')
param requestMessage string = 'Please approve this Private Endpoint connection for bastion access.'

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-11-01' = {
  name: peName
  location: location
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: '${peName}-connection'
        properties: {
          privateLinkServiceId: privateLinkServiceId
          groupIds: groupIds
          requestMessage: requestMessage
        }
      }
    ]
  }
}

@description('Resource ID of the Private Endpoint.')
output peId string = privateEndpoint.id

@description('Name of the Private Endpoint.')
output peName string = privateEndpoint.name

@description('Private IP address of the Private Endpoint.')
output pePrivateIp string = privateEndpoint.properties.customDnsConfigs[0].ipAddresses[0]
