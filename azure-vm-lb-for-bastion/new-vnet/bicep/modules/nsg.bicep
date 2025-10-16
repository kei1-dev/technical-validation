@description('Azure region for the NSG.')
param location string = resourceGroup().location

@description('Name of the NSG.')
param nsgName string

@description('Type of NSG: vm, pls, or vm-public.')
@allowed([
  'vm'
  'pls'
  'vm-public'
])
param nsgType string

@description('Source address prefix for SSH access (for VM NSG). e.g., LB subnet CIDR or Internet IP.')
param sshSourceAddressPrefix string = ''

@description('Allowed SSH port range for public access (e.g., "2201-2210").')
param allowedSshPortRange string = '2201-2210'

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

// VM Subnet用のNSG（Public LB経由、インターネットからのアクセス）
resource nsgVmPublic 'Microsoft.Network/networkSecurityGroups@2023-11-01' = if (nsgType == 'vm-public') {
  name: nsgName
  location: location
  properties: {
    securityRules: [
      {
        name: 'Allow-SSH-from-Internet'
        properties: {
          description: 'Allow SSH from Internet (via Public Load Balancer)'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '22'
          sourceAddressPrefix: empty(sshSourceAddressPrefix) ? '*' : sshSourceAddressPrefix
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
output nsgId string = nsgType == 'vm' ? nsgVm.id : (nsgType == 'vm-public' ? nsgVmPublic.id : nsgPls.id)

@description('Name of the NSG.')
output nsgName string = nsgType == 'vm' ? nsgVm.name : (nsgType == 'vm-public' ? nsgVmPublic.name : nsgPls.name)
