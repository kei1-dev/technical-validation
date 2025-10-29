// ============================================================================
// Application Gateway Module - App Gateway, Public IP, WAF Policy
// ============================================================================

@description('Environment name (dev/prod)')
param environment string

@description('Azure region for resources')
param location string = resourceGroup().location

@description('Common tags for all resources')
param tags object = {}

@description('Application Gateway Subnet ID')
param subnetId string

@description('Application Gateway SKU name')
@allowed([
  'Standard_v2'
  'WAF_v2'
])
param skuName string = 'Standard_v2'

@description('Enable WAF (prod only)')
param enableWaf bool = false

@description('Application Gateway capacity (1-10 for auto-scale)')
@minValue(1)
@maxValue(10)
param minCapacity int = 1

@description('Application Gateway max capacity (2-125)')
@minValue(2)
@maxValue(125)
param maxCapacity int = 10

@description('Managed Identity ID for certificate access')
param managedIdentityId string

@description('Backend FQDN - nginx')
param backendFqdnNginx string

@description('Container Apps Environment Static IP (for internal VNet)')
param containerAppsStaticIp string

@description('Key Vault SSL Certificate Secret ID (optional, for HTTPS)')
param sslCertificateSecretId string = ''

// ============================================================================
// Variables
// ============================================================================

var resourceNamePrefix = 'dify-${environment}'
var publicIpName = '${resourceNamePrefix}-appgateway-pip'
var appGatewayName = '${resourceNamePrefix}-appgateway'
var wafPolicyName = '${resourceNamePrefix}-waf-policy'

// Backend pool name
var backendPoolNameNginx = 'dify-nginx-pool'

// Backend HTTP settings name
var backendHttpSettingsNameNginx = 'dify-nginx-http-settings'

// HTTP listener names
var httpListenerNameHttp = 'http-listener'
var httpListenerNameHttps = 'https-listener'

// Frontend port names
var frontendPortNameHttp = 'port-80'
var frontendPortNameHttps = 'port-443'

// Probe name
var probeNameNginx = 'dify-nginx-probe'

// ============================================================================
// Public IP Address
// ============================================================================

resource publicIp 'Microsoft.Network/publicIPAddresses@2023-05-01' = {
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
    dnsSettings: {
      domainNameLabel: '${resourceNamePrefix}-${uniqueString(resourceGroup().id)}'
    }
  }
}

// ============================================================================
// WAF Policy (Prod only)
// ============================================================================

resource wafPolicy 'Microsoft.Network/ApplicationGatewayWebApplicationFirewallPolicies@2023-05-01' = if (enableWaf) {
  name: wafPolicyName
  location: location
  tags: tags
  properties: {
    policySettings: {
      requestBodyCheck: true
      maxRequestBodySizeInKb: 128
      fileUploadLimitInMb: 100
      state: 'Enabled'
      mode: 'Prevention'
    }
    managedRules: {
      managedRuleSets: [
        {
          ruleSetType: 'OWASP'
          ruleSetVersion: '3.2'
        }
      ]
    }
  }
}

// ============================================================================
// Application Gateway
// ============================================================================

resource applicationGateway 'Microsoft.Network/applicationGateways@2023-05-01' = {
  name: appGatewayName
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    sku: {
      name: skuName
      tier: skuName
    }
    autoscaleConfiguration: {
      minCapacity: minCapacity
      maxCapacity: maxCapacity
    }
    firewallPolicy: enableWaf ? {
      id: wafPolicy.id
    } : null
    gatewayIPConfigurations: [
      {
        name: 'appGatewayIpConfig'
        properties: {
          subnet: {
            id: subnetId
          }
        }
      }
    ]
    frontendIPConfigurations: [
      {
        name: 'appGatewayFrontendIP'
        properties: {
          publicIPAddress: {
            id: publicIp.id
          }
        }
      }
    ]
    frontendPorts: [
      {
        name: frontendPortNameHttp
        properties: {
          port: 80
        }
      }
      {
        name: frontendPortNameHttps
        properties: {
          port: 443
        }
      }
    ]
    backendAddressPools: [
      {
        name: backendPoolNameNginx
        properties: {
          backendAddresses: [
            {
              fqdn: backendFqdnNginx
            }
          ]
        }
      }
    ]
    backendHttpSettingsCollection: [
      {
        name: backendHttpSettingsNameNginx
        properties: {
          port: 80
          protocol: 'Http'
          cookieBasedAffinity: 'Disabled'
          pickHostNameFromBackendAddress: true
          requestTimeout: 300
          connectionDraining: {
            enabled: true
            drainTimeoutInSec: 60
          }
          probe: {
            id: resourceId('Microsoft.Network/applicationGateways/probes', appGatewayName, probeNameNginx)
          }
        }
      }
    ]
    httpListeners: [
      {
        name: httpListenerNameHttp
        properties: {
          frontendIPConfiguration: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendIPConfigurations', appGatewayName, 'appGatewayFrontendIP')
          }
          frontendPort: {
            id: resourceId('Microsoft.Network/applicationGateways/frontendPorts', appGatewayName, frontendPortNameHttp)
          }
          protocol: 'Http'
        }
      }
      // HTTPS listener (only if SSL certificate is provided)
      // Uncomment when SSL certificate is available in Key Vault
      // {
      //   name: httpListenerNameHttps
      //   properties: {
      //     frontendIPConfiguration: {
      //       id: resourceId('Microsoft.Network/applicationGateways/frontendIPConfigurations', appGatewayName, 'appGatewayFrontendIP')
      //     }
      //     frontendPort: {
      //       id: resourceId('Microsoft.Network/applicationGateways/frontendPorts', appGatewayName, frontendPortNameHttps)
      //     }
      //     protocol: 'Https'
      //     sslCertificate: {
      //       id: resourceId('Microsoft.Network/applicationGateways/sslCertificates', appGatewayName, 'appGatewaySslCert')
      //     }
      //   }
      // }
    ]
    requestRoutingRules: [
      {
        name: 'http-to-nginx-rule'
        properties: {
          ruleType: 'Basic'
          priority: 100
          httpListener: {
            id: resourceId('Microsoft.Network/applicationGateways/httpListeners', appGatewayName, httpListenerNameHttp)
          }
          backendAddressPool: {
            id: resourceId('Microsoft.Network/applicationGateways/backendAddressPools', appGatewayName, backendPoolNameNginx)
          }
          backendHttpSettings: {
            id: resourceId('Microsoft.Network/applicationGateways/backendHttpSettingsCollection', appGatewayName, backendHttpSettingsNameNginx)
          }
        }
      }
    ]
    probes: [
      {
        name: probeNameNginx
        properties: {
          protocol: 'Http'
          path: '/health'
          interval: 60
          timeout: 60
          unhealthyThreshold: 3
          pickHostNameFromBackendHttpSettings: true
          minServers: 0
          match: {
            statusCodes: [
              '200-399'
            ]
          }
        }
      }
    ]
    sslCertificates: []
    // SSL certificate from Key Vault (uncomment when certificate is available)
    // sslCertificates: !empty(sslCertificateSecretId) ? [
    //   {
    //     name: 'appGatewaySslCert'
    //     properties: {
    //       keyVaultSecretId: sslCertificateSecretId
    //     }
    //   }
    // ] : []
  }
}

// ============================================================================
// Outputs
// ============================================================================

@description('Application Gateway ID')
output applicationGatewayId string = applicationGateway.id

@description('Application Gateway Name')
output applicationGatewayName string = applicationGateway.name

@description('Public IP Address ID')
output publicIpId string = publicIp.id

@description('Public IP Address')
output publicIpAddress string = publicIp.properties.ipAddress

@description('Public IP FQDN')
output publicIpFqdn string = publicIp.properties.dnsSettings.fqdn

@description('WAF Policy ID (if enabled)')
output wafPolicyId string = enableWaf ? wafPolicy.id : ''
