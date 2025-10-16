targetScope = 'subscription'

@description('Azure region for all resources.')
param location string = 'japaneast'

@description('Name of the resource group for Load Balancer resources.')
param rgLbName string = 'rg-lb-bastion'

@description('Name of the resource group for VM resources.')
param rgVmName string = 'rg-vm-bastion'

@description('Name of the resource group for Hub VNet (existing).')
param rgHubName string = 'rg-hub'

@description('Resource ID of the existing Hub VNet subnet for Private Endpoint.')
param hubPeSubnetId string

@description('Resource ID of the existing LB subnet.')
param lbSubnetId string

@description('Resource ID of the existing Private Link Service subnet.')
param plsSubnetId string

@description('Resource ID of the existing VM subnet.')
param vmSubnetId string

@description('Address prefix of the LB subnet (for NSG rules).')
param lbSubnetPrefix string = '10.1.1.0/24'

@description('Private IP address for Internal Load Balancer.')
param ilbPrivateIp string = '10.1.1.4'

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

@description('Auto-approval subscription IDs for Private Link (optional).')
param plsAutoApprovalSubscriptions array = []

@description('Deploy NSGs for subnets (set to false if NSGs already exist).')
param deployNsgs bool = true

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

// NSG for Private Link Service subnet (optional)
module nsgPls 'modules/nsg.bicep' = if (deployNsgs) {
  name: 'nsg-pls'
  scope: rgLb
  params: {
    location: location
    nsgName: 'nsg-pls'
    nsgType: 'pls'
  }
}

// NSG for VM subnet (optional)
module nsgVm 'modules/nsg.bicep' = if (deployNsgs) {
  name: 'nsg-vm'
  scope: rgVm
  params: {
    location: location
    nsgName: 'nsg-vm'
    nsgType: 'vm'
    sshSourceAddressPrefix: lbSubnetPrefix
  }
}

// Internal Load Balancer
module ilb 'modules/internal-lb.bicep' = {
  name: 'ilb-bastion'
  scope: rgLb
  params: {
    location: location
    lbName: 'ilb-bastion'
    subnetId: lbSubnetId
    privateIpAddress: ilbPrivateIp
    vmCount: vmCount
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
    subnetId: plsSubnetId
    loadBalancerFrontendIpConfigId: ilb.outputs.frontendIpConfigId
    autoApprovalSubscriptions: plsAutoApprovalSubscriptions
  }
  dependsOn: [
    ilb
  ]
}

// Private Endpoint in Hub VNet
module pe 'modules/private-endpoint.bicep' = {
  name: 'pe-bastion'
  scope: resourceGroup(rgHubName)
  params: {
    location: location
    peName: 'pe-bastion-pls'
    subnetId: hubPeSubnetId
    privateLinkServiceId: pls.outputs.plsId
  }
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
    subnetId: vmSubnetId
    backendPoolId: ilb.outputs.backendPoolId
    natRuleId: ilb.outputs.natRuleIds[i]
  }
  dependsOn: [
    ilb
    sshKey
  ]
}]

// Outputs
@description('Resource ID of the Load Balancer resource group.')
output rgLbId string = rgLb.id

@description('Resource ID of the VM resource group.')
output rgVmId string = rgVm.id

@description('Private IP address of the Internal Load Balancer.')
output ilbPrivateIp string = ilb.outputs.lbPrivateIp

@description('Alias of the Private Link Service.')
output plsAlias string = pls.outputs.plsAlias

@description('Private IP address of the Private Endpoint.')
output pePrivateIp string = pe.outputs.pePrivateIp

@description('SSH connection information for each VM.')
output sshConnectionInfo array = [for i in range(0, vmCount): {
  vmName: 'vm-bastion-${i + 1}'
  sshCommand: 'ssh ${adminUsername}@${pe.outputs.pePrivateIp} -p ${natStartPort + i}'
  natPort: natStartPort + i
}]

@description('Name of the SSH Key resource.')
output sshKeyName string = sshKey.outputs.sshKeyName

@description('Resource group of the SSH Key.')
output sshKeyResourceGroup string = rgVmName

@description('Instructions for downloading the private key.')
output privateKeyInstructions string = 'IMPORTANT: Download the private key immediately after deployment using:\naz ssh config --ip ${pe.outputs.pePrivateIp} --file ~/.ssh/config --name ${sshKeyName} --resource-group ${rgVmName} --local-user ${adminUsername}\nOR generate key file:\naz sshkey show --resource-group ${rgVmName} --name ${sshKeyName} --query "publicKey" -o tsv > ~/.ssh/${sshKeyName}.pub'
