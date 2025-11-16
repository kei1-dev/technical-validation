// ============================================================================
// ACR Production Environment Parameters
// ============================================================================

using '../main.bicep'

// ============================================================================
// Basic Parameters
// ============================================================================

param environment = 'prod'
param location = 'japaneast'

param tags = {
  Environment: 'Production'
  Project: 'Dify'
  ManagedBy: 'Bicep'
  CostCenter: 'Engineering'
}
