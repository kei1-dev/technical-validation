@description('Azure region for the Load Balancer.')
param location string = resourceGroup().location

@description('Name of the Public Load Balancer.')
param lbName string

@description('Resource ID of the Public IP Address.')
param publicIpId string

@description('Frontend port for SSH NAT rule (e.g., 2201).')
param natStartPort int = 2201

resource loadBalancer 'Microsoft.Network/loadBalancers@2023-11-01' = {
  name: lbName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  properties: {
    frontendIPConfigurations: [
      {
        name: 'LoadBalancerFrontEnd'
        properties: {
          publicIPAddress: {
            id: publicIpId
          }
        }
      }
    ]
    backendAddressPools: [
      {
        name: 'BackendPool'
      }
    ]
    loadBalancingRules: []
    probes: [
      {
        name: 'ssh-probe'
        properties: {
          protocol: 'Tcp'
          port: 22
          intervalInSeconds: 5
          numberOfProbes: 2
        }
      }
    ]
    inboundNatRules: [
      {
        name: 'ssh-vm-1'
        properties: {
          frontendIPConfiguration: {
            id: resourceId('Microsoft.Network/loadBalancers/frontendIPConfigurations', lbName, 'LoadBalancerFrontEnd')
          }
          protocol: 'Tcp'
          frontendPort: natStartPort
          backendPort: 22
          enableFloatingIP: false
          enableTcpReset: true
          idleTimeoutInMinutes: 4
        }
      }
    ]
  }
}

@description('Resource ID of the Public Load Balancer.')
output lbId string = loadBalancer.id

@description('Name of the Public Load Balancer.')
output lbName string = loadBalancer.name

@description('Resource ID of the backend pool.')
output backendPoolId string = loadBalancer.properties.backendAddressPools[0].id

@description('Resource ID of the NAT rule.')
output natRuleId string = loadBalancer.properties.inboundNatRules[0].id

@description('Resource ID of the frontend IP configuration.')
output frontendIpConfigId string = loadBalancer.properties.frontendIPConfigurations[0].id
