import api from './api'
import type {
  Document,
  DocumentType,
  Folder,
  Department,
  DocumentVersion,
  PaginatedResponse,
  SourceType,
  LifecycleStatus,
} from '@/types'

export interface DocumentFilters {
  page?: number
  page_size?: number
  search?: string
  source_type?: SourceType
  document_type_id?: string
  folder_id?: string
  lifecycle_status?: LifecycleStatus
  customer_id?: string
  vendor_id?: string
}

export interface UploadDocumentRequest {
  file: File
  title: string
  source_type: SourceType
  document_type_id: string
  customer_id?: string
  vendor_id?: string
  department_id?: string
  folder_id?: string
  classification?: string
}

export const documentService = {
  // Documents
  async getDocuments(filters: DocumentFilters = {}): Promise<PaginatedResponse<Document>> {
    const response = await api.get<PaginatedResponse<Document>>('/documents', {
      params: filters,
    })
    return response.data
  },

  async getDocument(id: string): Promise<Document> {
    const response = await api.get<Document>(`/documents/${id}`)
    return response.data
  },

  async uploadDocument(data: UploadDocumentRequest): Promise<Document> {
    const formData = new FormData()
    formData.append('file', data.file)
    formData.append('title', data.title)
    formData.append('source_type', data.source_type)
    formData.append('document_type_id', data.document_type_id)
    if (data.customer_id) formData.append('customer_id', data.customer_id)
    if (data.vendor_id) formData.append('vendor_id', data.vendor_id)
    if (data.department_id) formData.append('department_id', data.department_id)
    if (data.folder_id) formData.append('folder_id', data.folder_id)
    if (data.classification) formData.append('classification', data.classification)

    const response = await api.post<Document>('/documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  async updateDocument(id: string, data: Partial<Document>): Promise<Document> {
    const response = await api.put<Document>(`/documents/${id}`, data)
    return response.data
  },

  async deleteDocument(id: string): Promise<void> {
    await api.delete(`/documents/${id}`)
  },

  async downloadDocument(id: string): Promise<Blob> {
    const response = await api.get(`/documents/${id}/download`, {
      responseType: 'blob',
    })
    return response.data
  },

  async transitionDocument(id: string, toStatus: LifecycleStatus, reason?: string): Promise<Document> {
    const response = await api.post<Document>(`/documents/${id}/transition`, {
      to_status: toStatus,
      reason,
    })
    return response.data
  },

  // Versions
  async getVersions(documentId: string): Promise<DocumentVersion[]> {
    const response = await api.get<DocumentVersion[]>(`/documents/${documentId}/versions`)
    return response.data
  },

  // Document Types
  async getDocumentTypes(): Promise<DocumentType[]> {
    const response = await api.get<DocumentType[]>('/documents/types')
    return response.data
  },

  async createDocumentType(data: Omit<DocumentType, 'id' | 'tenant_id' | 'created_at'>): Promise<DocumentType> {
    const response = await api.post<DocumentType>('/documents/types', data)
    return response.data
  },

  // Folders
  async getFolders(parentId?: string): Promise<Folder[]> {
    const response = await api.get<Folder[]>('/documents/folders', {
      params: parentId ? { parent_id: parentId } : undefined,
    })
    return response.data
  },

  async createFolder(data: { name: string; parent_id?: string }): Promise<Folder> {
    const response = await api.post<Folder>('/documents/folders', data)
    return response.data
  },

  // Departments
  async getDepartments(): Promise<Department[]> {
    const response = await api.get<Department[]>('/documents/departments')
    return response.data
  },

  async createDepartment(data: { name: string; code: string }): Promise<Department> {
    const response = await api.post<Department>('/documents/departments', data)
    return response.data
  },
}
