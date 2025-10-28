@description('Name of the existing VNet.')
param vnetName string

@description('Name of the subnet to create.')
param subnetName string

@description('Address prefix for the subnet (e.g., 10.1.1.0/24).')
param addressPrefix string

@description('Resource ID of the NSG to associate (optional).')
param nsgId string = ''

@description('Disable private link service network policies (required for PLS subnet).')
param disablePrivateLinkServiceNetworkPolicies bool = false

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' existing = {
  name: vnetName
}

resource subnet 'Microsoft.Network/virtualNetworks/subnets@2023-11-01' = {
  name: subnetName
  parent: vnet
  properties: {
    addressPrefix: addressPrefix
    networkSecurityGroup: empty(nsgId) ? null : {
      id: nsgId
    }
    privateLinkServiceNetworkPolicies: disablePrivateLinkServiceNetworkPolicies ? 'Disabled' : 'Enabled'
  }
}

@description('Resource ID of the created subnet.')
output subnetId string = subnet.id

@description('Name of the created subnet.')
output subnetName string = subnet.name
