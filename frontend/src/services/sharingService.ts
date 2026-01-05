import { api } from './api'

export interface Permission {
  id: string
  document_id: string
  user_id: string | null
  role_id: string | null
  department_id: string | null
  permission_level: string
  granted_at: string
  expires_at: string | null
  granted_by_email: string | null
}

export interface ShareLink {
  id: string
  token: string
  link_type: string
  url: string
  expires_at: string | null
  max_downloads: number | null
  download_count: number
  is_active: boolean
  created_at: string
}

export interface MyPermission {
  permission_level: string
  can_view: boolean
  can_download: boolean
  can_edit: boolean
  can_share: boolean
  can_delete: boolean
  is_masked: boolean
}

export interface GrantPermissionRequest {
  user_id?: string
  role_id?: string
  department_id?: string
  permission_level: string
  expires_at?: string
}

export interface CreateShareLinkRequest {
  link_type?: 'VIEW' | 'DOWNLOAD' | 'EDIT'
  password?: string
  max_downloads?: number
  expires_in_days?: number
}

export const PERMISSION_LEVELS = [
  { value: 'OWNER', label: 'Owner', description: 'Full control including delete' },
  { value: 'CO_OWNER', label: 'Co-Owner', description: 'Full control except permissions' },
  { value: 'EDITOR', label: 'Editor', description: 'Edit content and metadata' },
  { value: 'COMMENTER', label: 'Commenter', description: 'View and comment only' },
  { value: 'VIEWER_DOWNLOAD', label: 'Viewer (Download)', description: 'View and download' },
  { value: 'VIEWER_NO_DOWNLOAD', label: 'Viewer (No Download)', description: 'View only' },
  { value: 'LINK_ONLY', label: 'Link Only', description: 'Access via link only' },
  { value: 'RESTRICTED_MASKED', label: 'Restricted', description: 'View masked/redacted' },
  { value: 'NO_ACCESS', label: 'No Access', description: 'Explicitly denied' },
]

export const sharingService = {
  // Permissions
  getPermissions: async (documentId: string): Promise<Permission[]> => {
    const response = await api.get(`/documents/${documentId}/permissions`)
    return response.data
  },

  grantPermission: async (documentId: string, data: GrantPermissionRequest): Promise<{ status: string }> => {
    const response = await api.post(`/documents/${documentId}/permissions`, data)
    return response.data
  },

  revokePermission: async (documentId: string, permissionId: string): Promise<{ status: string }> => {
    const response = await api.delete(`/documents/${documentId}/permissions/${permissionId}`)
    return response.data
  },

  getMyPermission: async (documentId: string): Promise<MyPermission> => {
    const response = await api.get(`/documents/${documentId}/my-permission`)
    return response.data
  },

  // Share Links
  getShareLinks: async (documentId: string): Promise<ShareLink[]> => {
    const response = await api.get(`/documents/${documentId}/share-links`)
    return response.data
  },

  createShareLink: async (documentId: string, data: CreateShareLinkRequest): Promise<ShareLink> => {
    const response = await api.post(`/documents/${documentId}/share-links`, data)
    return response.data
  },

  deactivateShareLink: async (documentId: string, linkId: string): Promise<{ status: string }> => {
    const response = await api.delete(`/documents/${documentId}/share-links/${linkId}`)
    return response.data
  },
}

export default sharingService
