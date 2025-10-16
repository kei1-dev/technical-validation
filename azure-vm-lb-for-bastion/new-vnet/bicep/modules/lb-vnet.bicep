@description('Azure region for the VNet.')
param location string = resourceGroup().location

@description('Name of the VNet for Load Balancer.')
param vnetName string

@description('Address prefix for the VNet.')
param vnetAddressPrefix string = '10.1.0.0/16'

@description('Name of the subnet for Load Balancer.')
param lbSubnetName string = 'snet-lb'

@description('Address prefix for the Load Balancer subnet.')
param lbSubnetPrefix string = '10.1.1.0/24'

@description('Name of the subnet for Private Link Service.')
param plsSubnetName string = 'snet-pls'

@description('Address prefix for the Private Link Service subnet.')
param plsSubnetPrefix string = '10.1.2.0/24'

@description('Resource ID of the NSG for PLS subnet.')
param plsNsgId string = ''

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: lbSubnetName
        properties: {
          addressPrefix: lbSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Disabled'
        }
      }
      {
        name: plsSubnetName
        properties: {
          addressPrefix: plsSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Disabled'
          networkSecurityGroup: !empty(plsNsgId) ? {
            id: plsNsgId
          } : null
        }
      }
    ]
  }
}

@description('Resource ID of the VNet.')
output vnetId string = vnet.id

@description('Name of the VNet.')
output vnetName string = vnet.name

@description('Resource ID of the Load Balancer subnet.')
output lbSubnetId string = vnet.properties.subnets[0].id

@description('Name of the Load Balancer subnet.')
output lbSubnetName string = vnet.properties.subnets[0].name

@description('Resource ID of the Private Link Service subnet.')
output plsSubnetId string = vnet.properties.subnets[1].id

@description('Name of the Private Link Service subnet.')
output plsSubnetName string = vnet.properties.subnets[1].name
