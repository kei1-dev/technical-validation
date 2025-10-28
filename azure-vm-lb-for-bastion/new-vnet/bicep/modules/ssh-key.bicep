@description('Azure region for the SSH Key resource.')
param location string = resourceGroup().location

@description('Name of the SSH Public Key resource.')
param sshKeyName string

@description('Tags for the SSH Key resource.')
param tags object = {}

resource sshKey 'Microsoft.Compute/sshPublicKeys@2023-09-01' = {
  name: sshKeyName
  location: location
  tags: tags
  properties: {
    // Azure will generate the key pair automatically when publicKey is not provided
  }
}

@description('Resource ID of the SSH Public Key.')
output sshKeyId string = sshKey.id

@description('Name of the SSH Public Key.')
output sshKeyName string = sshKey.name

@description('Generated public key data.')
output publicKey string = sshKey.properties.publicKey

@description('Instructions for downloading the private key.')
output privateKeyDownloadInstructions string = 'Use Azure CLI: az sshkey show --resource-group ${resourceGroup().name} --name ${sshKeyName} --query "privateKey" -o tsv > ${sshKeyName}.pem'
