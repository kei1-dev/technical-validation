targetScope = 'subscription'

@description('Azure region for all resources.')
param location string = 'japaneast'

@description('Name of the resource group for Load Balancer resources.')
param rgLbName string = 'rg-lb-bastion'

@description('Name of the resource group for VM resources.')
param rgVmName string = 'rg-vm-bastion'

@description('Allowed source IP address for SSH access from Internet (CIDR or * for all).')
param allowedSshSourceIp string = '*'

@description('Name of the VNet for Load Balancer.')
param lbVnetName string = 'vnet-lb'

@description('Address prefix for LB VNet.')
param lbVnetAddressPrefix string = '10.1.0.0/16'

@description('Address prefix for LB subnet.')
param lbSubnetPrefix string = '10.1.1.0/24'


@description('Name of the VNet for VMs.')
param vmVnetName string = 'vnet-vm'

@description('Address prefix for VM VNet.')
param vmVnetAddressPrefix string = '10.2.0.0/16'

@description('Address prefix for VM subnet.')
param vmSubnetPrefix string = '10.2.1.0/24'


@description('Number of bastion VMs to deploy.')
@minValue(1)
@maxValue(10)
param vmCount int = 3

@description('VM size for bastion VMs.')
param vmSize string = 'Standard_B2s'

@description('Admin username for VMs.')
@secure()
param adminUsername string

@description('Name of the SSH Public Key resource to be created.')
param sshKeyName string = 'ssh-bastion'

@description('Starting port for SSH NAT rules.')
param natStartPort int = 2201


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

// SSH Public Key (Azure-managed)
module sshKey 'modules/ssh-key.bicep' = {
  name: 'ssh-key-bastion'
  scope: rgVm
  params: {
    location: location
    sshKeyName: sshKeyName
  }
}

// NSG for VM subnet (Public access)
module nsgVm 'modules/nsg.bicep' = {
  name: 'nsg-vm'
  scope: rgVm
  params: {
    location: location
    nsgName: 'nsg-vm'
    nsgType: 'vm-public'
    sshSourceAddressPrefix: allowedSshSourceIp
  }
}


// VNet for VMs
module vmVnet 'modules/vm-vnet.bicep' = {
  name: 'vnet-vm'
  scope: rgVm
  params: {
    location: location
    vnetName: vmVnetName
    vnetAddressPrefix: vmVnetAddressPrefix
    vmSubnetPrefix: vmSubnetPrefix
    vmNsgId: nsgVm.outputs.nsgId
  }
}

// Public IP for Load Balancer
module publicIp 'modules/public-ip.bicep' = {
  name: 'public-ip-lb'
  scope: rgLb
  params: {
    location: location
    publicIpName: 'pip-lb-bastion'
    dnsLabel: ''
  }
}

// Public Load Balancer
module plb 'modules/public-lb.bicep' = {
  name: 'plb-bastion'
  scope: rgLb
  params: {
    location: location
    lbName: 'plb-bastion'
    publicIpId: publicIp.outputs.publicIpId
    vmCount: vmCount
    natStartPort: natStartPort
  }
  dependsOn: [
    publicIp
  ]
}

// Bastion VMs
module bastionVms 'modules/bastion-vm.bicep' = [for i in range(0, vmCount): {
  name: 'bastion-vm-${i + 1}'
  scope: rgVm
  params: {
    location: location
    vmNamePrefix: 'vm-bastion'
    vmIndex: i + 1
    vmSize: vmSize
    adminUsername: adminUsername
    sshPublicKey: sshKey.outputs.publicKey
    subnetId: vmVnet.outputs.vmSubnetId
    backendPoolId: plb.outputs.backendPoolId
    natRuleId: plb.outputs.natRuleIds[i]
  }
  dependsOn: [
    plb
    sshKey
  ]
}]

// Outputs
@description('Resource ID of the Load Balancer resource group.')
output rgLbId string = rgLb.id

@description('Resource ID of the VM resource group.')
output rgVmId string = rgVm.id

@description('Public IP address of the Load Balancer.')
output publicIpAddress string = publicIp.outputs.publicIpAddress

@description('SSH connection information for each VM.')
output sshConnectionInfo array = [for i in range(0, vmCount): {
  vmName: 'vm-bastion-${i + 1}'
  sshCommand: 'ssh ${adminUsername}@${publicIp.outputs.publicIpAddress} -p ${natStartPort + i}'
  natPort: natStartPort + i
}]

@description('Name of the SSH Key resource.')
output sshKeyName string = sshKey.outputs.sshKeyName

@description('Resource group of the SSH Key.')
output sshKeyResourceGroup string = rgVmName

@description('Instructions for SSH connection.')
output sshInstructions string = 'Connect via: ssh ${adminUsername}@${publicIp.outputs.publicIpAddress} -p 2201 (or 2202, 2203...)\nDownload private key from Azure Portal: ${rgVmName} → ${sshKeyName} → Download private key'
