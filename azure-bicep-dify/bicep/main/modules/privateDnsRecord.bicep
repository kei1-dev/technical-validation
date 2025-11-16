// ============================================================================
// Private DNS Record Module - Creates A records in Private DNS Zones
// ============================================================================

@description('Private DNS Zone name where the record will be created')
param privateDnsZoneName string

@description('DNS record name (use * for wildcard)')
param recordName string

@description('IP address for the A record')
param ipAddress string

@description('TTL (Time To Live) in seconds')
param ttl int = 3600

@description('Common tags for all resources')
param tags object = {}

// ============================================================================
// Private DNS A Record
// ============================================================================

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' existing = {
  name: privateDnsZoneName
}

resource aRecord 'Microsoft.Network/privateDnsZones/A@2020-06-01' = {
  parent: privateDnsZone
  name: recordName
  properties: {
    ttl: ttl
    aRecords: [
      {
        ipv4Address: ipAddress
      }
    ]
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('DNS A Record ID')
output recordId string = aRecord.id

@description('DNS A Record Name')
output recordName string = aRecord.name

@description('DNS A Record FQDN')
output recordFqdn string = '${recordName == '*' ? '*' : recordName}.${privateDnsZoneName}'
