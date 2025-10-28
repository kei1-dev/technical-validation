// ============================================================================
// Private Endpoint Module - Reusable Private Endpoint Configuration
// ============================================================================

@description('Private Endpoint name')
param privateEndpointName string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Common tags for all resources')
param tags object = {}

@description('Subnet ID for the Private Endpoint')
param subnetId string

@description('Resource ID of the service to connect via Private Endpoint')
param privateLinkServiceId string

@description('Group IDs for the Private Endpoint (e.g., [\'blob\'], [\'postgresqlServer\'])')
param groupIds array

@description('Private DNS Zone IDs for DNS integration')
param privateDnsZoneIds array

// ============================================================================
// Private Endpoint
// ============================================================================

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2023-05-01' = {
  name: privateEndpointName
  location: location
  tags: tags
  properties: {
    subnet: {
      id: subnetId
    }
    privateLinkServiceConnections: [
      {
        name: privateEndpointName
        properties: {
          privateLinkServiceId: privateLinkServiceId
          groupIds: groupIds
        }
      }
    ]
  }
}

// ============================================================================
// Private DNS Zone Group
// ============================================================================

resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-05-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [for (privateDnsZoneId, index) in privateDnsZoneIds: {
      name: 'config${index + 1}'
      properties: {
        privateDnsZoneId: privateDnsZoneId
      }
    }]
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('Private Endpoint ID')
output privateEndpointId string = privateEndpoint.id

@description('Private Endpoint Name')
output privateEndpointName string = privateEndpoint.name

@description('Private Endpoint Network Interface IDs')
output privateEndpointNetworkInterfaceIds array = privateEndpoint.properties.networkInterfaces
