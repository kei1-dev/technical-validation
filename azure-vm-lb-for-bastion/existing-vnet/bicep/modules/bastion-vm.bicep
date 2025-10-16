@description('Azure region for the VM.')
param location string = resourceGroup().location

@description('Name prefix for the VM.')
param vmNamePrefix string = 'vm-bastion'

@description('VM instance number (e.g., 1, 2, 3).')
param vmIndex int

@description('VM size.')
param vmSize string = 'Standard_B2s'

@description('Admin username.')
@secure()
param adminUsername string

@description('SSH public key for authentication.')
param sshPublicKey string

@description('OS disk type.')
@allowed([
  'Standard_LRS'
  'StandardSSD_LRS'
  'Premium_LRS'
])
param osDiskType string = 'Standard_LRS'

@description('Ubuntu OS version.')
param ubuntuOsVersion string = '22_04-lts-gen2'

@description('Resource ID of the subnet.')
param subnetId string

@description('Resource ID of the Load Balancer backend pool.')
param backendPoolId string

@description('Resource ID of the NAT rule for this VM.')
param natRuleId string

@description('Static private IP address (optional, leave empty for dynamic).')
param staticPrivateIp string = ''

var vmName = '${vmNamePrefix}-${vmIndex}'
var nicName = '${vmName}-nic'

resource nic 'Microsoft.Network/networkInterfaces@2023-11-01' = {
  name: nicName
  location: location
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          subnet: {
            id: subnetId
          }
          privateIPAllocationMethod: empty(staticPrivateIp) ? 'Dynamic' : 'Static'
          privateIPAddress: empty(staticPrivateIp) ? null : staticPrivateIp
          loadBalancerBackendAddressPools: [
            {
              id: backendPoolId
            }
          ]
          loadBalancerInboundNatRules: [
            {
              id: natRuleId
            }
          ]
        }
      }
    ]
    enableAcceleratedNetworking: false
    enableIPForwarding: false
  }
}

resource vm 'Microsoft.Compute/virtualMachines@2023-09-01' = {
  name: vmName
  location: location
  properties: {
    hardwareProfile: {
      vmSize: vmSize
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: '0001-com-ubuntu-server-jammy'
        sku: ubuntuOsVersion
        version: 'latest'
      }
      osDisk: {
        name: '${vmName}-osdisk'
        createOption: 'FromImage'
        managedDisk: {
          storageAccountType: osDiskType
        }
        deleteOption: 'Delete'
      }
    }
    osProfile: {
      computerName: vmName
      adminUsername: adminUsername
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: {
          publicKeys: [
            {
              path: '/home/${adminUsername}/.ssh/authorized_keys'
              keyData: sshPublicKey
            }
          ]
        }
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: nic.id
          properties: {
            deleteOption: 'Delete'
          }
        }
      ]
    }
    diagnosticsProfile: {
      bootDiagnostics: {
        enabled: true
      }
    }
  }
}

@description('Resource ID of the VM.')
output vmId string = vm.id

@description('Name of the VM.')
output vmName string = vm.name

@description('Resource ID of the NIC.')
output nicId string = nic.id

@description('Private IP address of the VM.')
output privateIp string = nic.properties.ipConfigurations[0].properties.privateIPAddress
