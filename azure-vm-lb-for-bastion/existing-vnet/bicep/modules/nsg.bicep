@description('Azure region for the NSG.')
param location string = resourceGroup().location

@description('Name of the NSG.')
param nsgName string

@description('Type of NSG: vm or pls.')
@allowed([
  'vm'
  'pls'
])
param nsgType string

@description('Source address prefix for SSH access (for VM NSG). e.g., LB subnet CIDR.')
param sshSourceAddressPrefix string = ''

// VM Subnet用のNSG
resource nsgVm 'Microsoft.Network/networkSecurityGroups@2023-11-01' = if (nsgType == 'vm') {
  name: nsgName
  location: location
  properties: {
    securityRules: [
      {
        name: 'Allow-SSH-from-ILB'
        properties: {
          description: 'Allow SSH from Internal Load Balancer subnet'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '22'
          sourceAddressPrefix: sshSourceAddressPrefix
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
      {
        name: 'Deny-All-Inbound'
        properties: {
          description: 'Deny all other inbound traffic'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Deny'
          priority: 4096
          direction: 'Inbound'
        }
      }
    ]
  }
}

// Private Link Service Subnet用のNSG
resource nsgPls 'Microsoft.Network/networkSecurityGroups@2023-11-01' = if (nsgType == 'pls') {
  name: nsgName
  location: location
  properties: {
    securityRules: [
      {
        name: 'Allow-PrivateLink-Inbound'
        properties: {
          description: 'Allow Private Link Service traffic'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: '*'
          access: 'Allow'
          priority: 100
          direction: 'Inbound'
        }
      }
    ]
  }
}

@description('Resource ID of the NSG.')
output nsgId string = nsgType == 'vm' ? nsgVm.id : nsgPls.id

@description('Name of the NSG.')
output nsgName string = nsgType == 'vm' ? nsgVm.name : nsgPls.name
