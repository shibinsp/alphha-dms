import api from './api'

export type RequestedPermission = 'VIEW' | 'EDIT' | 'DOWNLOAD'
export type AccessRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'REASON_REQUESTED'
export type PermissionLevel = 'OWNER' | 'CO_OWNER' | 'EDITOR' | 'COMMENTER' | 'VIEWER_DOWNLOAD' | 'VIEWER_NO_DOWNLOAD' | 'LINK_ONLY' | 'RESTRICTED_MASKED' | 'NO_ACCESS'

export interface AccessRequest {
  id: string
  document_id: string
  document?: { id: string; title: string; file_name: string }
  requester_id: string
  requester?: { id: string; full_name: string; email: string }
  requested_permission: RequestedPermission
  reason?: string
  status: AccessRequestStatus
  owner_id: string
  owner?: { id: string; full_name: string; email: string }
  granted_permission?: PermissionLevel
  owner_comment?: string
  responded_at?: string
  created_at: string
  updated_at: string
}

export const accessRequestService = {
  async createRequest(documentId: string, permission: RequestedPermission, reason?: string): Promise<AccessRequest> {
    const response = await api.post<AccessRequest>('/access-requests', {
      document_id: documentId,
      requested_permission: permission,
      reason
    })
    return response.data
  },

  async getMyRequests(status?: AccessRequestStatus): Promise<AccessRequest[]> {
    const params = status ? { status_filter: status } : {}
    const response = await api.get<AccessRequest[]>('/access-requests/my-requests', { params })
    return response.data
  },

  async getPendingRequests(): Promise<AccessRequest[]> {
    const response = await api.get<AccessRequest[]>('/access-requests/pending')
    return response.data
  },

  async getProcessedRequests(): Promise<AccessRequest[]> {
    const response = await api.get<AccessRequest[]>('/access-requests/processed')
    return response.data
  },

  async approveRequest(requestId: string, grantedPermission?: PermissionLevel, comment?: string): Promise<AccessRequest> {
    const response = await api.post<AccessRequest>(`/access-requests/${requestId}/approve`, {
      granted_permission: grantedPermission,
      comment
    })
    return response.data
  },

  async rejectRequest(requestId: string, comment?: string): Promise<AccessRequest> {
    const response = await api.post<AccessRequest>(`/access-requests/${requestId}/reject`, { comment })
    return response.data
  },

  async askForReason(requestId: string, comment: string): Promise<AccessRequest> {
    const response = await api.post<AccessRequest>(`/access-requests/${requestId}/ask-reason`, { comment })
    return response.data
  },

  async updateRequest(requestId: string, reason: string): Promise<AccessRequest> {
    const response = await api.patch<AccessRequest>(`/access-requests/${requestId}`, { reason })
    return response.data
  },

  async cancelRequest(requestId: string): Promise<void> {
    await api.delete(`/access-requests/${requestId}`)
  }
}
