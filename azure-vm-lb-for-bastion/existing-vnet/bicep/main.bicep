targetScope = 'subscription'

@description('Azure region for all resources.')
param location string = 'japaneast'

@description('Name of the resource group for Load Balancer resources.')
param rgLbName string = 'rg-lb-bastion'

@description('Name of the resource group for VM resources.')
param rgVmName string = 'rg-vm-bastion'

@description('Resource group name of the existing VNet.')
param vnetResourceGroup string

@description('Name of the existing VNet.')
param vnetName string

@description('Address prefix for LB subnet (new subnet to create).')
param lbSubnetPrefix string = '10.1.1.0/24'

@description('Address prefix for PLS subnet (new subnet to create).')
param plsSubnetPrefix string = '10.1.2.0/24'

@description('Address prefix for VM subnet (new subnet to create).')
param vmSubnetPrefix string = '10.1.3.0/24'

@description('Private IP address for Internal Load Balancer.')
param ilbPrivateIp string = '10.1.1.4'

@description('VM size for bastion VMs.')
param vmSize string = 'Standard_B2s'

@description('Admin username for VMs.')
param adminUsername string

@description('Admin password for VMs.')
@secure()
@minLength(12)
param adminPassword string

@description('Starting port for SSH NAT rules.')
param natStartPort int = 2201

@description('Auto-approval subscription IDs for Private Link (optional).')
param plsAutoApprovalSubscriptions array = []

// Resource Group for Load Balancer
resource rgLb 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: rgLbName
  location: location
}

// Resource Group for VMs
resource rgVm 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: rgVmName
  location: location
}

// NSG for Load Balancer subnet
module nsgLb 'modules/nsg.bicep' = {
  name: 'nsg-lb'
  scope: rgLb
  params: {
    location: location
    nsgName: 'nsg-lb'
    nsgType: 'lb'
  }
}

// NSG for Private Link Service subnet
module nsgPls 'modules/nsg.bicep' = {
  name: 'nsg-pls'
  scope: rgLb
  params: {
    location: location
    nsgName: 'nsg-pls'
    nsgType: 'pls'
  }
}

// NSG for VM subnet
module nsgVm 'modules/nsg.bicep' = {
  name: 'nsg-vm'
  scope: rgVm
  params: {
    location: location
    nsgName: 'nsg-vm'
    nsgType: 'vm'
    sshSourceAddressPrefix: lbSubnetPrefix
  }
}

// Subnet for Load Balancer
module subnetLb 'modules/subnet.bicep' = {
  name: 'subnet-lb'
  scope: resourceGroup(vnetResourceGroup)
  params: {
    vnetName: vnetName
    subnetName: 'snet-lb'
    addressPrefix: lbSubnetPrefix
    nsgId: nsgLb.outputs.nsgId
    disablePrivateLinkServiceNetworkPolicies: false
  }
}

// Subnet for Private Link Service
module subnetPls 'modules/subnet.bicep' = {
  name: 'subnet-pls'
  scope: resourceGroup(vnetResourceGroup)
  params: {
    vnetName: vnetName
    subnetName: 'snet-pls'
    addressPrefix: plsSubnetPrefix
    nsgId: nsgPls.outputs.nsgId
    disablePrivateLinkServiceNetworkPolicies: true
  }
}

// Subnet for VMs
module subnetVm 'modules/subnet.bicep' = {
  name: 'subnet-vm'
  scope: resourceGroup(vnetResourceGroup)
  params: {
    vnetName: vnetName
    subnetName: 'snet-vm'
    addressPrefix: vmSubnetPrefix
    nsgId: nsgVm.outputs.nsgId
    disablePrivateLinkServiceNetworkPolicies: false
  }
}

// Internal Load Balancer
module ilb 'modules/internal-lb.bicep' = {
  name: 'ilb-bastion'
  scope: rgLb
  params: {
    location: location
    lbName: 'ilb-bastion'
    subnetId: subnetLb.outputs.subnetId
    privateIpAddress: ilbPrivateIp
    natStartPort: natStartPort
  }
}

// Private Link Service
module pls 'modules/private-link-service.bicep' = {
  name: 'pls-bastion'
  scope: rgLb
  params: {
    location: location
    plsName: 'pls-bastion'
    subnetId: subnetPls.outputs.subnetId
    loadBalancerFrontendIpConfigId: ilb.outputs.frontendIpConfigId
    autoApprovalSubscriptions: plsAutoApprovalSubscriptions
  }
}

// Bastion VM (single VM)
module bastionVm 'modules/bastion-vm.bicep' = {
  name: 'bastion-vm-1'
  scope: rgVm
  params: {
    location: location
    vmNamePrefix: 'vm-bastion'
    vmIndex: 1
    vmSize: vmSize
    adminUsername: adminUsername
    adminPassword: adminPassword
    subnetId: subnetVm.outputs.subnetId
    backendPoolId: ilb.outputs.backendPoolId
    natRuleId: ilb.outputs.natRuleId
  }
}

// Outputs
@description('Resource ID of the Load Balancer resource group.')
output rgLbId string = rgLb.id

@description('Resource ID of the VM resource group.')
output rgVmId string = rgVm.id

@description('Private IP address of the Internal Load Balancer.')
output ilbPrivateIp string = ilb.outputs.lbPrivateIp

@description('Alias of the Private Link Service for external connection.')
output plsAlias string = pls.outputs.plsAlias

@description('Resource ID of the Private Link Service.')
output plsId string = pls.outputs.plsId

@description('SSH connection information (via ILB within same VNet).')
output sshConnectionInfo object = {
  vmName: 'vm-bastion-1'
  sshCommand: 'ssh ${adminUsername}@${ilb.outputs.lbPrivateIp} -p ${natStartPort}'
  natPort: natStartPort
  ilbPrivateIp: ilb.outputs.lbPrivateIp
}

@description('Instructions for SSH connection.')
output connectionInstructions string = '''
# Within same VNet:
ssh ${adminUsername}@${ilb.outputs.lbPrivateIp} -p ${natStartPort}

# From another VNet (create Private Endpoint first):
1. Create Private Endpoint in your Hub VNet using PLS Alias: ${pls.outputs.plsAlias}
2. Connect via: ssh ${adminUsername}@<Private-Endpoint-IP> -p ${natStartPort}

Password authentication is enabled. Add SSH keys after deployment via Azure Portal if needed.
'''
