@description('Name of the first VNet.')
param vnet1Name string

@description('Resource ID of the first VNet.')
param vnet1Id string

@description('Name of the second VNet.')
param vnet2Name string

@description('Resource ID of the second VNet.')
param vnet2Id string

@description('Resource group name of the first VNet.')
param vnet1ResourceGroup string

@description('Resource group name of the second VNet.')
param vnet2ResourceGroup string

@description('Allow forwarded traffic from VNet1 to VNet2.')
param allowForwardedTrafficVnet1ToVnet2 bool = true

@description('Allow forwarded traffic from VNet2 to VNet1.')
param allowForwardedTrafficVnet2ToVnet1 bool = true

@description('Use remote gateways for VNet1.')
param useRemoteGatewaysVnet1 bool = false

@description('Use remote gateways for VNet2.')
param useRemoteGatewaysVnet2 bool = false

// Peering from VNet1 to VNet2
resource peeringVnet1ToVnet2 'Microsoft.Network/virtualNetworks/virtualNetworkPeerings@2023-11-01' = {
  name: '${vnet1Name}/peer-${vnet1Name}-to-${vnet2Name}'
  properties: {
    allowVirtualNetworkAccess: true
    allowForwardedTraffic: allowForwardedTrafficVnet1ToVnet2
    allowGatewayTransit: false
    useRemoteGateways: useRemoteGatewaysVnet1
    remoteVirtualNetwork: {
      id: vnet2Id
    }
  }
}

// Peering from VNet2 to VNet1 (deployed in VNet2's resource group)
module peeringVnet2ToVnet1 'vnet-peering-single.bicep' = {
  name: 'peer-${vnet2Name}-to-${vnet1Name}'
  scope: resourceGroup(vnet2ResourceGroup)
  params: {
    localVnetName: vnet2Name
    remoteVnetName: vnet1Name
    remoteVnetId: vnet1Id
    allowForwardedTraffic: allowForwardedTrafficVnet2ToVnet1
    useRemoteGateways: useRemoteGatewaysVnet2
  }
}

@description('Status of the peering from VNet1 to VNet2.')
output peeringVnet1ToVnet2Status string = peeringVnet1ToVnet2.properties.peeringState

@description('Status of the peering from VNet2 to VNet1.')
output peeringVnet2ToVnet1Status string = peeringVnet2ToVnet1.outputs.peeringStatus
