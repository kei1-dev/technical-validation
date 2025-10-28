// ============================================================================
// Private DNS Zone Module - Reusable Private DNS Zone Configuration
// ============================================================================

@description('Private DNS Zone name (e.g., privatelink.postgres.database.azure.com)')
param privateDnsZoneName string

@description('Virtual Network ID to link with the Private DNS Zone')
param vnetId string

@description('Common tags for all resources')
param tags object = {}

@description('Enable auto-registration of VM DNS records')
param enableAutoRegistration bool = false

// ============================================================================
// Variables
// ============================================================================

// Extract VNet name from the resource ID for the link name
var vnetName = last(split(vnetId, '/'))

// ============================================================================
// Private DNS Zone
// ============================================================================

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: privateDnsZoneName
  location: 'global'
  tags: tags
  properties: {}
}

// ============================================================================
// Virtual Network Link
// ============================================================================

resource privateDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: privateDnsZone
  name: '${vnetName}-link'
  location: 'global'
  tags: tags
  properties: {
    registrationEnabled: enableAutoRegistration
    virtualNetwork: {
      id: vnetId
    }
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('Private DNS Zone ID')
output privateDnsZoneId string = privateDnsZone.id

@description('Private DNS Zone Name')
output privateDnsZoneName string = privateDnsZone.name
