// User types
export interface User {
  id: string
  email: string
  full_name: string
  department?: string
  region?: string
  clearance_level: string
  phone?: string
  avatar_url?: string
  is_active: boolean
  is_superuser: boolean
  mfa_enabled: boolean
  last_login?: string
  tenant_id: string
  created_at: string
  updated_at: string
  roles: Role[]
}

export interface Role {
  id: string
  name: string
  description?: string
  permissions: string[]
  is_system_role: boolean
  tenant_id?: string
  created_at: string
}

// Tenant types
export interface Tenant {
  id: string
  name: string
  subdomain: string
  logo_url?: string
  primary_color?: string
  config: Record<string, unknown>
  license_expires?: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// Document types
export type SourceType = 'CUSTOMER' | 'VENDOR' | 'INTERNAL'
export type Classification = 'PUBLIC' | 'INTERNAL' | 'CONFIDENTIAL' | 'RESTRICTED'
export type LifecycleStatus = 'DRAFT' | 'REVIEW' | 'APPROVED' | 'ARCHIVED' | 'DELETED'
export type OCRStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'

export interface Document {
  id: string
  title: string
  file_name: string
  file_size: number
  mime_type: string
  page_count?: number
  source_type: SourceType
  customer_id?: string
  vendor_id?: string
  department_id?: string
  document_type_id: string
  folder_id?: string
  classification: Classification
  lifecycle_status: LifecycleStatus
  is_worm_locked: boolean
  legal_hold: boolean
  ocr_status: OCRStatus
  ocr_text?: string
  extracted_metadata?: Record<string, unknown>
  custom_metadata: Record<string, unknown>
  tenant_id: string
  created_by: string
  updated_by: string
  created_at: string
  updated_at: string
  document_type?: DocumentType
  folder?: Folder
  department?: Department
}

export interface DocumentType {
  id: string
  name: string
  description?: string
  icon?: string
  retention_days?: number
  approval_flow_type: 'AUTO' | 'MANUAL' | 'NONE'
  auto_approvers?: string[]
  tenant_id: string
  created_at: string
}

export interface Folder {
  id: string
  name: string
  parent_id?: string
  path: string
  tenant_id: string
  created_at: string
}

export interface Department {
  id: string
  name: string
  code: string
  tenant_id: string
  created_at: string
}

export interface DocumentVersion {
  id: string
  document_id: string
  version_number: number
  file_size: number
  checksum_sha256: string
  change_reason?: string
  is_current: boolean
  created_by: string
  created_at: string
}

// API response types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ApiError {
  detail: string
  status_code?: number
}

// Auth types
export interface LoginRequest {
  email: string
  password: string
  mfa_code?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

// Audit types
export interface AuditEvent {
  id: string
  sequence_number: number
  event_type: string
  entity_type: string
  entity_id: string
  user_id: string
  ip_address?: string
  user_agent?: string
  old_values?: Record<string, unknown>
  new_values?: Record<string, unknown>
  metadata?: Record<string, unknown>
  event_hash: string
  previous_hash: string
  tenant_id: string
  created_at: string
}
