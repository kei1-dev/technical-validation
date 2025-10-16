@description('Azure region for the VNet.')
param location string = resourceGroup().location

@description('Name of the VNet for VMs.')
param vnetName string

@description('Address prefix for the VNet.')
param vnetAddressPrefix string = '10.2.0.0/16'

@description('Name of the subnet for VMs.')
param vmSubnetName string = 'snet-vm'

@description('Address prefix for the VM subnet.')
param vmSubnetPrefix string = '10.2.1.0/24'

@description('Resource ID of the NSG for VM subnet.')
param vmNsgId string

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
        name: vmSubnetName
        properties: {
          addressPrefix: vmSubnetPrefix
          networkSecurityGroup: {
            id: vmNsgId
          }
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
    ]
  }
}

@description('Resource ID of the VNet.')
output vnetId string = vnet.id

@description('Name of the VNet.')
output vnetName string = vnet.name

@description('Resource ID of the VM subnet.')
output vmSubnetId string = vnet.properties.subnets[0].id

@description('Name of the VM subnet.')
output vmSubnetName string = vnet.properties.subnets[0].name
