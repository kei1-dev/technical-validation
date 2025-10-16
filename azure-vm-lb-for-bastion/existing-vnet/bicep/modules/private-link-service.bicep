@description('Azure region for the Private Link Service.')
param location string = resourceGroup().location

@description('Name of the Private Link Service.')
param plsName string

@description('Resource ID of the subnet for the Private Link Service.')
param subnetId string

@description('Resource ID of the Load Balancer frontend IP configuration.')
param loadBalancerFrontendIpConfigId string

@description('Enable proxy protocol v2.')
param enableProxyProtocol bool = false

@description('Auto-approval subscription IDs (optional).')
param autoApprovalSubscriptions array = []

@description('Visibility subscription IDs (optional, empty = all).')
param visibilitySubscriptions array = []

resource privateLinkService 'Microsoft.Network/privateLinkServices@2023-11-01' = {
  name: plsName
  location: location
  properties: {
    enableProxyProtocol: enableProxyProtocol
    loadBalancerFrontendIpConfigurations: [
      {
        id: loadBalancerFrontendIpConfigId
      }
    ]
    ipConfigurations: [
      {
        name: 'pls-ipconfig'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          subnet: {
            id: subnetId
          }
          primary: true
          privateIPAddressVersion: 'IPv4'
        }
      }
    ]
    autoApproval: !empty(autoApprovalSubscriptions) ? {
      subscriptions: autoApprovalSubscriptions
    } : null
    visibility: !empty(visibilitySubscriptions) ? {
      subscriptions: visibilitySubscriptions
    } : null
  }
}

@description('Resource ID of the Private Link Service.')
output plsId string = privateLinkService.id

@description('Name of the Private Link Service.')
output plsName string = privateLinkService.name

@description('Alias of the Private Link Service (used for Private Endpoint connection).')
output plsAlias string = privateLinkService.properties.alias
