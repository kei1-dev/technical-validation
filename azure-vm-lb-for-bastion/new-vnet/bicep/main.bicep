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
    natStartPort: natStartPort
  }
  dependsOn: [
    publicIp
  ]
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
    subnetId: vmVnet.outputs.vmSubnetId
    backendPoolId: plb.outputs.backendPoolId
    natRuleId: plb.outputs.natRuleId
  }
  dependsOn: [
    plb
  ]
}

// Outputs
@description('Resource ID of the Load Balancer resource group.')
output rgLbId string = rgLb.id

@description('Resource ID of the VM resource group.')
output rgVmId string = rgVm.id

@description('Public IP address of the Load Balancer.')
output publicIpAddress string = publicIp.outputs.publicIpAddress

@description('SSH connection information.')
output sshConnectionInfo object = {
  vmName: 'vm-bastion-1'
  sshCommand: 'ssh ${adminUsername}@${publicIp.outputs.publicIpAddress} -p ${natStartPort}'
  natPort: natStartPort
}

@description('Instructions for SSH connection.')
output connectionInstructions string = 'Connect via: ssh ${adminUsername}@${publicIp.outputs.publicIpAddress} -p ${natStartPort}\nPassword authentication is enabled. Add SSH keys after deployment via Azure Portal if needed.'
