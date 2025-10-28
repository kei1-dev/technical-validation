// ============================================================================
// PostgreSQL Module - Azure Database for PostgreSQL Flexible Server
// ============================================================================

@description('Environment name (dev/prod)')
param environment string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Common tags for all resources')
param tags object = {}

@description('PostgreSQL administrator username')
@minLength(1)
@maxLength(63)
param administratorLogin string

@description('PostgreSQL administrator password')
@secure()
@minLength(8)
@maxLength(128)
param administratorPassword string

@description('PostgreSQL version')
@allowed([
  '11'
  '12'
  '13'
  '14'
  '15'
  '16'
])
param postgresqlVersion string = '15'

@description('PostgreSQL SKU name (e.g., Standard_B1ms, Standard_D2s_v3)')
param skuName string = 'Standard_B1ms'

@description('Storage size in GB (32-16384)')
@minValue(32)
@maxValue(16384)
param storageSizeGB int = 32

@description('Enable high availability (prod only)')
param enableHighAvailability bool = false

@description('Backup retention days (7-35)')
@minValue(7)
@maxValue(35)
param backupRetentionDays int = 7

@description('Enable geo-redundant backup (prod only)')
param enableGeoRedundantBackup bool = false

// ============================================================================
// Variables
// ============================================================================

var resourceNamePrefix = 'dify-${environment}'

// PostgreSQL server name must be globally unique
var postgresqlServerName = '${resourceNamePrefix}-postgres-${uniqueString(resourceGroup().id)}'
var databaseName = 'dify'

// High Availability mode
var haMode = enableHighAvailability ? 'ZoneRedundant' : 'Disabled'

// ============================================================================
// PostgreSQL Flexible Server
// ============================================================================

resource postgresqlServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: postgresqlServerName
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: startsWith(skuName, 'Standard_B') ? 'Burstable' : 'GeneralPurpose'
  }
  properties: {
    version: postgresqlVersion
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorPassword
    storage: {
      storageSizeGB: storageSizeGB
      autoGrow: 'Enabled'
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: enableGeoRedundantBackup ? 'Enabled' : 'Disabled'
    }
    highAvailability: {
      mode: haMode
    }
    availabilityZone: enableHighAvailability ? '' : '1'
  }
}

// ============================================================================
// PostgreSQL Configurations
// ============================================================================

// Enable Azure extensions
resource postgresqlConfigExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-03-01-preview' = {
  parent: postgresqlServer
  name: 'azure.extensions'
  properties: {
    value: 'vector,pg_stat_statements,pg_trgm,uuid-ossp'
    source: 'user-override'
  }
}

// Set max connections based on environment
resource postgresqlConfigMaxConnections 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-03-01-preview' = {
  parent: postgresqlServer
  name: 'max_connections'
  properties: {
    value: environment == 'prod' ? '200' : '100'
    source: 'user-override'
  }
}

// Set shared buffers
resource postgresqlConfigSharedBuffers 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-03-01-preview' = {
  parent: postgresqlServer
  name: 'shared_buffers'
  properties: {
    value: environment == 'prod' ? '524288' : '262144' // 512MB for prod, 256MB for dev (in 8KB blocks)
    source: 'user-override'
  }
}

// Enable log statements
resource postgresqlConfigLogStatement 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-03-01-preview' = {
  parent: postgresqlServer
  name: 'log_statement'
  properties: {
    value: environment == 'prod' ? 'none' : 'all'
    source: 'user-override'
  }
}

// ============================================================================
// PostgreSQL Database
// ============================================================================

resource postgresqlDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresqlServer
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// ============================================================================
// Firewall Rules (Temporary - Remove after Private Endpoint setup)
// ============================================================================

// Allow Azure services (for initial setup)
resource postgresqlFirewallAllowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  parent: postgresqlServer
  name: 'AllowAllAzureServicesAndResourcesWithinAzureIps'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('PostgreSQL Server ID')
output postgresqlServerId string = postgresqlServer.id

@description('PostgreSQL Server Name')
output postgresqlServerName string = postgresqlServer.name

@description('PostgreSQL Server FQDN')
output postgresqlServerFqdn string = postgresqlServer.properties.fullyQualifiedDomainName

@description('PostgreSQL Database Name')
output postgresqlDatabaseName string = databaseName

@description('PostgreSQL Connection String (without password)')
output postgresqlConnectionStringTemplate string = 'postgresql://${administratorLogin}@${postgresqlServer.name}:PASSWORD_HERE@${postgresqlServer.properties.fullyQualifiedDomainName}:5432/${databaseName}?sslmode=require'

@description('PostgreSQL Administrator Username')
output postgresqlAdminUsername string = administratorLogin
