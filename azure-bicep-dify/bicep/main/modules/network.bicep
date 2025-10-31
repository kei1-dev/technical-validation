// ============================================================================
// Network Module - VNet, Subnets, NSGs
// ============================================================================

@description('Environment name (dev/prod)')
param environment string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Common tags for all resources')
param tags object = {}

@description('Virtual Network address prefix')
param vnetAddressPrefix string = '10.0.0.0/16'

@description('Application Gateway subnet address prefix')
param appGatewaySubnetPrefix string = '10.0.0.0/24'

@description('Container Apps subnet address prefix')
param containerAppsSubnetPrefix string = '10.0.1.0/24'

@description('Private Endpoint subnet address prefix')
param privateEndpointSubnetPrefix string = '10.0.2.0/24'

// ============================================================================
// Variables
// ============================================================================

var resourceNamePrefix = 'dify-${environment}'

// Subnet names
var appGatewaySubnetName = 'appgateway-subnet'
var containerAppsSubnetName = 'containerapps-subnet'
var privateEndpointSubnetName = 'privateendpoint-subnet'

// NSG names
var appGatewayNsgName = '${resourceNamePrefix}-appgateway-nsg'
var containerAppsNsgName = '${resourceNamePrefix}-containerapps-nsg'
var privateEndpointNsgName = '${resourceNamePrefix}-privateendpoint-nsg'

// ============================================================================
// Network Security Groups
// ============================================================================

// NSG for Application Gateway subnet
resource appGatewayNsg 'Microsoft.Network/networkSecurityGroups@2023-05-01' = {
  name: appGatewayNsgName
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'Allow-Internet-HTTPS-Inbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
          description: 'Allow HTTPS traffic from Internet'
        }
      }
      {
        name: 'Allow-Internet-HTTP-Inbound'
        properties: {
          priority: 110
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '80'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
          description: 'Allow HTTP traffic from Internet (redirect to HTTPS)'
        }
      }
      {
        name: 'Allow-GatewayManager-Inbound'
        properties: {
          priority: 120
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '65200-65535'
          sourceAddressPrefix: 'GatewayManager'
          destinationAddressPrefix: '*'
          description: 'Allow Azure infrastructure for Application Gateway management'
        }
      }
      {
        name: 'Allow-AzureLoadBalancer-Inbound'
        properties: {
          priority: 130
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'AzureLoadBalancer'
          destinationAddressPrefix: '*'
          description: 'Allow Azure Load Balancer health probes'
        }
      }
    ]
  }
}

// NSG for Container Apps subnet
resource containerAppsNsg 'Microsoft.Network/networkSecurityGroups@2023-05-01' = {
  name: containerAppsNsgName
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'Allow-AppGateway-Inbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRanges: [
            '80'
            '443'
          ]
          sourceAddressPrefix: appGatewaySubnetPrefix
          destinationAddressPrefix: '*'
          description: 'Allow traffic from Application Gateway'
        }
      }
      {
        name: 'Allow-ContainerApps-Control-Plane'
        properties: {
          priority: 110
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'AzureCloud'
          destinationAddressPrefix: '*'
          description: 'Allow Container Apps control plane traffic'
        }
      }
    ]
  }
}

// NSG for Private Endpoint subnet
resource privateEndpointNsg 'Microsoft.Network/networkSecurityGroups@2023-05-01' = {
  name: privateEndpointNsgName
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'Allow-VNet-Inbound'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Allow'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'VirtualNetwork'
          description: 'Allow traffic from VNet to Private Endpoints'
        }
      }
    ]
  }
}

// ============================================================================
// Virtual Network
// ============================================================================

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: '${resourceNamePrefix}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: appGatewaySubnetName
        properties: {
          addressPrefix: appGatewaySubnetPrefix
          networkSecurityGroup: {
            id: appGatewayNsg.id
          }
          privateEndpointNetworkPolicies: 'Enabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
      {
        name: containerAppsSubnetName
        properties: {
          addressPrefix: containerAppsSubnetPrefix
          networkSecurityGroup: {
            id: containerAppsNsg.id
          }
          delegations: [
            {
              name: 'Microsoft.App.environments'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
          privateEndpointNetworkPolicies: 'Enabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
      {
        name: privateEndpointSubnetName
        properties: {
          addressPrefix: privateEndpointSubnetPrefix
          networkSecurityGroup: {
            id: privateEndpointNsg.id
          }
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
    ]
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('Virtual Network ID')
output vnetId string = vnet.id

@description('Virtual Network Name')
output vnetName string = vnet.name

@description('Application Gateway Subnet ID')
output appGatewaySubnetId string = vnet.properties.subnets[0].id

@description('Application Gateway Subnet Name')
output appGatewaySubnetName string = appGatewaySubnetName

@description('Container Apps Subnet ID')
output containerAppsSubnetId string = vnet.properties.subnets[1].id

@description('Container Apps Subnet Name')
output containerAppsSubnetName string = containerAppsSubnetName

@description('Private Endpoint Subnet ID')
output privateEndpointSubnetId string = vnet.properties.subnets[2].id

@description('Private Endpoint Subnet Name')
output privateEndpointSubnetName string = privateEndpointSubnetName

@description('Application Gateway NSG ID')
output appGatewayNsgId string = appGatewayNsg.id

@description('Container Apps NSG ID')
output containerAppsNsgId string = containerAppsNsg.id

@description('Private Endpoint NSG ID')
output privateEndpointNsgId string = privateEndpointNsg.id
