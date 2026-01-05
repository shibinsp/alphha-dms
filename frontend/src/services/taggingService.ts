import { api } from './api'

export interface Tag {
  id: string
  name: string
  slug: string
  category: string | null
  description: string | null
  color: string | null
  parent_id: string | null
  usage_count: number
  is_controlled: boolean
  requires_approval: boolean
}

export interface DocumentTag {
  id: string
  document_id: string
  tag_id: string
  tag_type: 'MANUAL' | 'AUTO' | 'SUGGESTED'
  confidence_score: number | null
  tag: Tag
}

export interface TagSuggestion {
  id: string
  document_id: string
  suggested_tag_name: string
  suggested_tag_id: string | null
  confidence_score: number
  source: string | null
  status: 'PENDING' | 'APPROVED' | 'REJECTED'
}

export interface CreateTagRequest {
  name: string
  category?: string
  description?: string
  color?: string
  parent_id?: string
  is_controlled?: boolean
  requires_approval?: boolean
}

export const taggingService = {
  // Tag CRUD
  getTags: async (params?: { category?: string; search?: string; parent_id?: string }): Promise<Tag[]> => {
    const response = await api.get('/tags', { params })
    return response.data
  },

  getTag: async (tagId: string): Promise<Tag> => {
    const response = await api.get(`/tags/${tagId}`)
    return response.data
  },

  createTag: async (data: CreateTagRequest): Promise<Tag> => {
    const response = await api.post('/tags', data)
    return response.data
  },

  updateTag: async (tagId: string, data: Partial<CreateTagRequest>): Promise<Tag> => {
    const response = await api.put(`/tags/${tagId}`, data)
    return response.data
  },

  deleteTag: async (tagId: string): Promise<void> => {
    await api.delete(`/tags/${tagId}`)
  },

  getCategories: async (): Promise<string[]> => {
    const response = await api.get('/tags/categories')
    return response.data
  },

  getPopularTags: async (limit = 20): Promise<Tag[]> => {
    const response = await api.get('/tags/popular', { params: { limit } })
    return response.data
  },

  // Document tagging
  getDocumentTags: async (documentId: string): Promise<DocumentTag[]> => {
    const response = await api.get(`/tags/documents/${documentId}/tags`)
    return response.data
  },

  addTagToDocument: async (documentId: string, tagId: string): Promise<DocumentTag> => {
    const response = await api.post(`/tags/documents/${documentId}/tags`, { tag_id: tagId })
    return response.data
  },

  removeTagFromDocument: async (documentId: string, tagId: string): Promise<void> => {
    await api.delete(`/tags/documents/${documentId}/tags/${tagId}`)
  },

  // Auto-tagging
  autoTagDocument: async (documentId: string): Promise<TagSuggestion[]> => {
    const response = await api.post(`/tags/documents/${documentId}/auto-tag`)
    return response.data
  },

  // Suggestions
  getPendingSuggestions: async (documentId?: string, limit = 50): Promise<TagSuggestion[]> => {
    const response = await api.get('/tags/suggestions', { params: { document_id: documentId, limit } })
    return response.data
  },

  approveSuggestion: async (suggestionId: string): Promise<DocumentTag> => {
    const response = await api.post(`/tags/suggestions/${suggestionId}/approve`)
    return response.data
  },

  rejectSuggestion: async (suggestionId: string, reason?: string): Promise<TagSuggestion> => {
    const response = await api.post(`/tags/suggestions/${suggestionId}/reject`, null, {
      params: { reason },
    })
    return response.data
  },

  bulkApproveSuggestions: async (suggestionIds: string[]): Promise<{ approved_count: number }> => {
    const response = await api.post('/tags/suggestions/bulk-approve', { suggestion_ids: suggestionIds })
    return response.data
  },

  // Synonyms
  addSynonym: async (tagId: string, synonym: string): Promise<{ id: string; tag_id: string; synonym: string }> => {
    const response = await api.post(`/tags/${tagId}/synonyms`, { synonym })
    return response.data
  },

  removeSynonym: async (tagId: string, synonymId: string): Promise<void> => {
    await api.delete(`/tags/${tagId}/synonyms/${synonymId}`)
  },
}

export default taggingService
