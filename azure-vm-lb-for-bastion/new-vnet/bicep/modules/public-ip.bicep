@description('Azure region for the Public IP.')
param location string = resourceGroup().location

@description('Name of the Public IP Address.')
param publicIpName string

@description('DNS label for the Public IP (optional).')
param dnsLabel string = ''

@description('Tags for the Public IP resource.')
param tags object = {}

resource publicIp 'Microsoft.Network/publicIPAddresses@2023-11-01' = {
  name: publicIpName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  properties: {
    publicIPAllocationMethod: 'Static'
    publicIPAddressVersion: 'IPv4'
    dnsSettings: !empty(dnsLabel) ? {
      domainNameLabel: dnsLabel
    } : null
    idleTimeoutInMinutes: 4
  }
}

@description('Resource ID of the Public IP.')
output publicIpId string = publicIp.id

@description('Name of the Public IP.')
output publicIpName string = publicIp.name

@description('Public IP address.')
output publicIpAddress string = publicIp.properties.ipAddress

@description('FQDN of the Public IP (if DNS label is set).')
output fqdn string = !empty(dnsLabel) ? publicIp.properties.dnsSettings.fqdn : ''
