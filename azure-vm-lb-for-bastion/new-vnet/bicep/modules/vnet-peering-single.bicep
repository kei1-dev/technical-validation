@description('Name of the local VNet.')
param localVnetName string

@description('Name of the remote VNet.')
param remoteVnetName string

@description('Resource ID of the remote VNet.')
param remoteVnetId string

@description('Allow forwarded traffic.')
param allowForwardedTraffic bool = true

@description('Use remote gateways.')
param useRemoteGateways bool = false

resource peering 'Microsoft.Network/virtualNetworks/virtualNetworkPeerings@2023-11-01' = {
  name: '${localVnetName}/peer-${localVnetName}-to-${remoteVnetName}'
  properties: {
    allowVirtualNetworkAccess: true
    allowForwardedTraffic: allowForwardedTraffic
    allowGatewayTransit: false
    useRemoteGateways: useRemoteGateways
    remoteVirtualNetwork: {
      id: remoteVnetId
    }
  }
}

@description('Status of the peering.')
output peeringStatus string = peering.properties.peeringState
