// ============================================================================
// Redis Module - Azure Cache for Redis
// ============================================================================

@description('Environment name (dev/prod)')
param environment string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Common tags for all resources')
param tags object = {}

@description('Redis SKU family (C for Basic/Standard, P for Premium)')
@allowed([
  'C'
  'P'
])
param skuFamily string = 'C'

@description('Redis SKU name')
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param skuName string = 'Basic'

@description('Redis capacity (0-6 for C family, 1-5 for P family)')
@minValue(0)
@maxValue(6)
param skuCapacity int = 1

@description('Enable non-SSL port (not recommended for production)')
param enableNonSslPort bool = false

@description('Redis version')
@allowed([
  '4'
  '6'
])
param redisVersion string = '6'

// ============================================================================
// Variables
// ============================================================================

var resourceNamePrefix = 'dify-${environment}'

// Redis name must be globally unique
var redisName = '${resourceNamePrefix}-redis-${uniqueString(resourceGroup().id)}'

// Redis configuration based on environment
// Note: notify-keyspace-events is not supported on Basic tier
var redisConfiguration = skuName == 'Basic' ? {
  'maxmemory-policy': 'allkeys-lru'
  'maxmemory-reserved': '50'
  'maxfragmentationmemory-reserved': '50'
} : {
  'maxmemory-policy': 'allkeys-lru'
  'maxmemory-reserved': skuName == 'Premium' ? '200' : '50'
  'maxfragmentationmemory-reserved': skuName == 'Premium' ? '200' : '50'
  'notify-keyspace-events': 'Ex' // Enable keyspace notifications for expired keys
}

// ============================================================================
// Redis Cache
// ============================================================================

resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: redisName
  location: location
  tags: tags
  properties: union({
    sku: {
      name: skuName
      family: skuFamily
      capacity: skuCapacity
    }
    enableNonSslPort: enableNonSslPort
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled' // Will be disabled after Private Endpoint setup
    redisConfiguration: redisConfiguration
    redisVersion: redisVersion
  }, (skuName == 'Premium' && environment == 'prod') ? {
    // Zone redundancy (Premium SKU only, prod environment)
    replicasPerMaster: 1
    replicasPerPrimary: 1
    shardCount: 1
  } : {})
}

// ============================================================================
// Redis Firewall Rules (Temporary - Remove after Private Endpoint setup)
// ============================================================================

// Note: Redis firewall rules are configured at the service level
// After Private Endpoint setup, publicNetworkAccess should be set to 'Disabled'

// ============================================================================
// Outputs
// ============================================================================

@description('Redis Cache ID')
output redisId string = redis.id

@description('Redis Cache Name')
output redisName string = redis.name

@description('Redis Cache Host Name')
output redisHostName string = redis.properties.hostName

@description('Redis Cache SSL Port')
output redisSslPort int = redis.properties.sslPort

@description('Redis Cache Port')
output redisPort int = redis.properties.port

@description('Redis Cache Primary Key (for connection strings)')
#disable-next-line outputs-should-not-contain-secrets
output redisPrimaryKey string = redis.listKeys().primaryKey

@description('Redis Cache Secondary Key (for connection strings)')
#disable-next-line outputs-should-not-contain-secrets
output redisSecondaryKey string = redis.listKeys().secondaryKey

@description('Redis Connection String (SSL)')
#disable-next-line outputs-should-not-contain-secrets
output redisConnectionString string = '${redis.properties.hostName}:${redis.properties.sslPort},password=${redis.listKeys().primaryKey},ssl=True,abortConnect=False'

@description('Redis Connection String Template (without password)')
output redisConnectionStringTemplate string = '${redis.properties.hostName}:${redis.properties.sslPort},password=PASSWORD_HERE,ssl=True,abortConnect=False'
