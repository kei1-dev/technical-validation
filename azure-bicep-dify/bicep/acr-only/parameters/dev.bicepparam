// ============================================================================
// ACR Development Environment Parameters
// ============================================================================

using '../main.bicep'

// ============================================================================
// Basic Parameters
// ============================================================================

param environment = 'dev'
param location = 'japaneast'

param tags = {
  Environment: 'Development'
  Project: 'Dify'
  ManagedBy: 'Bicep'
  CostCenter: 'Engineering'
}
