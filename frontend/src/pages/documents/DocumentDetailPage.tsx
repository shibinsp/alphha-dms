import React, { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Typography,
  Tabs,
  message,
  Spin,
  Breadcrumb,
  Modal,
  Alert,
} from 'antd'
import {
  DownloadOutlined,
  EditOutlined,
  ArrowLeftOutlined,
  CheckCircleOutlined,
  FileOutlined,
  LockOutlined,
  SafetyOutlined,
  EyeOutlined,
  ScanOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { documentService } from '@/services/documentService'
import type { LifecycleStatus } from '@/types'
import dayjs from 'dayjs'
import { LifecycleTimeline } from '@/components/common'
import DocumentViewer from '@/components/common/DocumentViewer'
import DocumentTags from '@/components/documents/DocumentTags'
import SharePermissions from '@/components/documents/SharePermissions'
import ShareLinks from '@/components/documents/ShareLinks'
import VersionHistoryWithDiff from '@/components/documents/VersionHistoryWithDiff'
import { useAuthStore } from '@/store/authStore'

const { Title, Text } = Typography

const DocumentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [viewerOpen, setViewerOpen] = useState(false)
  const [activeTab, setActiveTab] = useState('details')
  const { user } = useAuthStore()

  // Check if user can approve
  const canApprove = useMemo(() => {
    if (!user?.roles) return false
    const roleNames = user.roles.map(r => r.name)
    return roleNames.some(r => ['admin', 'super_admin', 'manager'].includes(r))
  }, [user])

  // Fetch document
  const { data: document, isLoading } = useQuery({
    queryKey: ['document', id],
    queryFn: () => documentService.getDocument(id!),
    enabled: !!id,
  })

  // Fetch versions
  const { data: versions } = useQuery({
    queryKey: ['document-versions', id],
    queryFn: () => documentService.getVersions(id!),
    enabled: !!id,
  })

  // Transition mutation
  const transitionMutation = useMutation({
    mutationFn: ({ toStatus, reason }: { toStatus: LifecycleStatus; reason?: string }) =>
      documentService.transitionDocument(id!, toStatus, reason),
    onSuccess: () => {
      message.success('Status updated successfully')
      queryClient.invalidateQueries({ queryKey: ['document', id] })
    },
    onError: () => {
      message.error('Failed to update status')
    },
  })

  // Submit for approval mutation
  const submitForApprovalMutation = useMutation({
    mutationFn: () => documentService.submitForApproval(id!),
    onSuccess: () => {
      message.success('Document submitted for approval')
      queryClient.invalidateQueries({ queryKey: ['document', id] })
    },
    onError: () => {
      message.error('Failed to submit for approval')
    },
  })

  // OCR extraction mutation
  const ocrMutation = useMutation({
    mutationFn: () => documentService.triggerOCR(id!),
    onSuccess: () => {
      message.success('Data extraction started. This may take a few seconds...')
      // Poll for completion multiple times
      const pollInterval = setInterval(() => {
        queryClient.invalidateQueries({ queryKey: ['document', id] })
      }, 3000)
      // Stop polling after 30 seconds
      setTimeout(() => clearInterval(pollInterval), 30000)
    },
    onError: () => {
      message.error('Failed to start extraction')
    },
  })

  // Restore version mutation
  const restoreVersionMutation = useMutation({
    mutationFn: async (versionNumber: number) => {
      const api = (await import('@/services/api')).default
      return api.post(`/versions/documents/${id}/restore/${versionNumber}`)
    },
    onSuccess: () => {
      message.success('Version restored successfully')
      queryClient.invalidateQueries({ queryKey: ['document', id] })
      queryClient.invalidateQueries({ queryKey: ['document-versions', id] })
    },
    onError: () => {
      message.error('Failed to restore version')
    },
  })

  // Request access mutation (must be before any early returns)
  const requestAccessMutation = useMutation({
    mutationFn: async (permission: 'VIEW' | 'DOWNLOAD' | 'EDIT') => {
      const { data } = await import('@/services/api').then(m => m.api.post('/access-requests', {
        document_id: id,
        requested_permission: permission,
        reason: `Requesting ${permission.toLowerCase()} access to this document`,
      }))
      return data
    },
    onSuccess: () => {
      message.success('Access request sent to document owner')
      queryClient.invalidateQueries({ queryKey: ['document', id] })
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || 'Failed to send request')
    },
  })

  // Permission check helpers - only allow download if explicitly permitted
  const canDownload = useMemo(() => {
    if (!document) return true // Loading state
    if (document.is_owner) return true
    // If user has a permission set, check if it allows download
    if (document.user_permission) {
      return ['VIEWER_DOWNLOAD', 'EDITOR', 'CO_OWNER', 'OWNER'].includes(document.user_permission)
    }
    // No explicit permission means they have general access (not restricted doc)
    return true
  }, [document])
  
  // Check if user has edit permission based on role
  const hasEditRolePermission = useMemo(() => {
    if (!user?.roles) return false
    const permissions = user.roles.flatMap(r => r.permissions)
    return permissions.includes('documents.update') || permissions.includes('documents.create')
  }, [user])
  
  const canEdit = useMemo(() => {
    if (!document) return true // Loading state
    // First check role-based permission
    if (!hasEditRolePermission) return false
    if (document.is_owner) return true
    if (document.user_permission) {
      return ['EDITOR', 'CO_OWNER', 'OWNER'].includes(document.user_permission)
    }
    return true
  }, [document, hasEditRolePermission])

  // Download handler
  const handleDownload = async () => {
    if (!document) return
    
    // Check if user has download permission
    if (!canDownload) {
      Modal.confirm({
        title: 'Download Access Required',
        content: 'You only have VIEW permission for this document. To download, you need to request download access.',
        okText: 'Request Download Access',
        cancelText: 'Cancel',
        onOk: () => requestAccessMutation.mutate('DOWNLOAD'),
      })
      return
    }
    
    try {
      const blob = await documentService.downloadDocument(document.id)
      const url = window.URL.createObjectURL(blob)
      const a = window.document.createElement('a')
      a.href = url
      a.download = document.file_name
      a.click()
      window.URL.revokeObjectURL(url)
    } catch {
      message.error('Failed to download document')
    }
  }

  // Edit handler with permission check
  const handleEdit = () => {
    if (!document) return
    
    if (!canEdit) {
      Modal.confirm({
        title: 'Edit Access Required',
        content: 'You only have VIEW permission for this document. To edit, you need to request edit access.',
        okText: 'Request Edit Access',
        cancelText: 'Cancel',
        onOk: () => requestAccessMutation.mutate('EDIT'),
      })
      return
    }
    
    navigate(`/documents/${id}/edit`)
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  if (!document) {
    return (
      <div className="text-center py-12">
        <Title level={4}>Document not found</Title>
        <Button onClick={() => navigate('/documents')}>Back to Documents</Button>
      </div>
    )
  }

  // Handle restricted document that requires access
  if ((document as any).access_required) {
    return (
      <div className="p-6">
        <Breadcrumb className="mb-4">
          <Breadcrumb.Item>
            <a onClick={() => navigate('/documents')}>Documents</a>
          </Breadcrumb.Item>
          <Breadcrumb.Item>{document.title}</Breadcrumb.Item>
        </Breadcrumb>
        
        <Card>
          <div className="text-center py-12">
            <LockOutlined style={{ fontSize: 64, color: '#faad14' }} />
            <Title level={3} className="mt-4">Restricted Document</Title>
            <Text type="secondary" className="block mb-4">
              This document is restricted. You need to request access from the document owner.
            </Text>
            
            <Descriptions column={1} bordered className="max-w-md mx-auto mb-6">
              <Descriptions.Item label="Title">{document.title}</Descriptions.Item>
              <Descriptions.Item label="File Name">{document.file_name}</Descriptions.Item>
              <Descriptions.Item label="Classification">
                <Tag color="red">RESTRICTED</Tag>
              </Descriptions.Item>
            </Descriptions>
            
            {(document as any).has_pending_request ? (
              <div>
                <Tag color="processing" icon={<ClockCircleOutlined />} className="text-base px-4 py-2">
                  Access Request Pending - Waiting for owner approval
                </Tag>
              </div>
            ) : (
              <Space direction="vertical" size="middle">
                <Text>Select the type of access you need:</Text>
                <Space>
                  <Button 
                    type="primary"
                    icon={<EyeOutlined />}
                    loading={requestAccessMutation.isPending}
                    onClick={() => requestAccessMutation.mutate('VIEW')}
                  >
                    Request View Access
                  </Button>
                  <Button 
                    icon={<DownloadOutlined />}
                    loading={requestAccessMutation.isPending}
                    onClick={() => requestAccessMutation.mutate('DOWNLOAD')}
                  >
                    Request Download Access
                  </Button>
                  <Button 
                    icon={<EditOutlined />}
                    loading={requestAccessMutation.isPending}
                    onClick={() => requestAccessMutation.mutate('EDIT')}
                  >
                    Request Edit Access
                  </Button>
                </Space>
              </Space>
            )}
            
            <div className="mt-6">
              <Button onClick={() => navigate('/documents')}>Back to Documents</Button>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  const getStatusColor = (status: LifecycleStatus) => {
    const colors: Record<LifecycleStatus, string> = {
      DRAFT: 'default',
      REVIEW: 'processing',
      APPROVED: 'success',
      ARCHIVED: 'warning',
      DELETED: 'error',
    }
    return colors[status]
  }

  const getNextActions = () => {
    // Check if user has workflow permissions
    const hasWorkflowPermission = user?.roles?.some(r => 
      r.permissions.includes('documents:update') || 
      r.permissions.includes('approvals.approve')
    )
    if (!hasWorkflowPermission) return []
    
    const actions = []
    if (document.lifecycle_status === 'DRAFT') {
      actions.push({
        label: 'Submit for Review',
        status: 'REVIEW' as LifecycleStatus,
      })
    } else if (document.lifecycle_status === 'REVIEW' && canApprove) {
      actions.push(
        { label: 'Approve', status: 'APPROVED' as LifecycleStatus },
        { label: 'Reject', status: 'DRAFT' as LifecycleStatus }
      )
    } else if (document.lifecycle_status === 'APPROVED') {
      actions.push({ label: 'Archive', status: 'ARCHIVED' as LifecycleStatus })
    }
    return actions
  }

  const tabItems = [
    {
      key: 'details',
      label: 'Details',
      children: (
        <Descriptions column={2} bordered>
          <Descriptions.Item label="File Name">{document.file_name}</Descriptions.Item>
          <Descriptions.Item label="File Size">
            {(document.file_size / 1024).toFixed(1)} KB
          </Descriptions.Item>
          <Descriptions.Item label="MIME Type">{document.mime_type}</Descriptions.Item>
          <Descriptions.Item label="Page Count">{document.page_count || '-'}</Descriptions.Item>
          <Descriptions.Item label="Source Type">
            <Tag color="blue">{document.source_type}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Classification">
            <Tag>{document.classification}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Document Type">
            {document.document_type?.name || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="Folder">
            {document.folder?.path || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="Customer ID">
            {document.customer_id || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="Vendor ID">
            {document.vendor_id || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="Created At">
            {dayjs(document.created_at).format('MMM D, YYYY h:mm A')}
          </Descriptions.Item>
          <Descriptions.Item label="Updated At">
            {dayjs(document.updated_at).format('MMM D, YYYY h:mm A')}
          </Descriptions.Item>
        </Descriptions>
      ),
    },
    {
      key: 'versions',
      label: `Versions (${versions?.length || 0})`,
      children: (
        <VersionHistoryWithDiff
          documentId={document.id}
          versions={versions || []}
          lifecycleStatus={document.lifecycle_status}
          isWormLocked={document.is_worm_locked}
          onRestore={(versionNumber) => {
            Modal.confirm({
              title: 'Restore Version',
              content: `Are you sure you want to restore Version ${versionNumber}? This will create a new version based on the selected one.`,
              okText: 'Restore',
              onOk: () => restoreVersionMutation.mutate(versionNumber),
            })
          }}
          restoreLoading={restoreVersionMutation.isPending}
        />
      ),
    },
    {
      key: 'metadata',
      label: 'Custom Metadata',
      children: (
        <Descriptions column={1} bordered>
          {Object.entries(document.custom_metadata || {}).map(([key, value]) => (
            <Descriptions.Item key={key} label={key}>
              {String(value)}
            </Descriptions.Item>
          ))}
          {Object.keys(document.custom_metadata || {}).length === 0 && (
            <div className="text-gray-500 py-4 text-center">
              No custom metadata
            </div>
          )}
        </Descriptions>
      ),
    },
    {
      key: 'extracted',
      label: (
        <span>
          Extracted Data{' '}
          <Tag color={document.ocr_status === 'COMPLETED' ? 'green' : document.ocr_status === 'PROCESSING' ? 'blue' : 'default'} style={{ marginLeft: 4 }}>
            {document.ocr_status}
          </Tag>
        </span>
      ),
      children: (
        <div>
          {document.ocr_status === 'PROCESSING' && (
            <Alert message="OCR processing in progress..." type="info" showIcon style={{ marginBottom: 16 }} />
          )}
          {document.ocr_status === 'FAILED' && (
            <Alert 
              message="OCR extraction failed" 
              description={document.extracted_metadata?.error || 'Unknown error'} 
              type="error" 
              showIcon 
              style={{ marginBottom: 16 }} 
            />
          )}
          {document.extracted_metadata && Object.keys(document.extracted_metadata).length > 0 && document.extracted_metadata.error === undefined && (
            <Card title="Extracted Metadata" size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={2} size="small" bordered>
                {document.extracted_metadata.document_type && (
                  <Descriptions.Item label="Document Type">
                    <Tag color="blue">{document.extracted_metadata.document_type}</Tag>
                  </Descriptions.Item>
                )}
                {document.extracted_metadata.language && (
                  <Descriptions.Item label="Language">
                    <Tag>{document.extracted_metadata.language.toUpperCase()}</Tag>
                  </Descriptions.Item>
                )}
                {document.extracted_metadata.confidence !== undefined && (
                  <Descriptions.Item label="Confidence">
                    <Tag color={document.extracted_metadata.confidence > 80 ? 'green' : document.extracted_metadata.confidence > 50 ? 'orange' : 'red'}>
                      {document.extracted_metadata.confidence}%
                    </Tag>
                  </Descriptions.Item>
                )}
              </Descriptions>
              {document.extracted_metadata.entities && Object.keys(document.extracted_metadata.entities).length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <Text strong>Extracted Entities:</Text>
                  <div style={{ marginTop: 8 }}>
                    {document.extracted_metadata.entities.names?.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <Text type="secondary">Names: </Text>
                        {document.extracted_metadata.entities.names.map((n: string, i: number) => <Tag key={i} color="purple">{n}</Tag>)}
                      </div>
                    )}
                    {document.extracted_metadata.entities.dates?.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <Text type="secondary">Dates: </Text>
                        {document.extracted_metadata.entities.dates.map((d: string, i: number) => <Tag key={i} color="cyan">{d}</Tag>)}
                      </div>
                    )}
                    {document.extracted_metadata.entities.amounts?.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <Text type="secondary">Amounts: </Text>
                        {document.extracted_metadata.entities.amounts.map((a: string, i: number) => <Tag key={i} color="green">{a}</Tag>)}
                      </div>
                    )}
                    {document.extracted_metadata.entities.organizations?.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <Text type="secondary">Organizations: </Text>
                        {document.extracted_metadata.entities.organizations.map((o: string, i: number) => <Tag key={i} color="blue">{o}</Tag>)}
                      </div>
                    )}
                    {document.extracted_metadata.entities.id_numbers?.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <Text type="secondary">ID Numbers: </Text>
                        {document.extracted_metadata.entities.id_numbers.map((id: string, i: number) => <Tag key={i} color="orange">{id}</Tag>)}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </Card>
          )}
          <Card title="OCR Text" size="small">
            {document.ocr_text ? (
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', maxHeight: 400, overflow: 'auto', margin: 0 }}>
                {document.ocr_text}
              </pre>
            ) : (
              <div className="text-gray-500 py-4 text-center">
                {document.ocr_status === 'PENDING' ? 'Click "Extract Data" to process this document' : 'No OCR text available'}
              </div>
            )}
          </Card>
        </div>
      ),
    },
    {
      key: 'tags',
      label: 'Tags',
      children: (
        <DocumentTags
          documentId={document.id}
          editable={!document.is_worm_locked}
        />
      ),
    },
    {
      key: 'sharing',
      label: 'Sharing',
      children: (
        <div>
          <SharePermissions
            documentId={document.id}
            canManage={!document.is_worm_locked}
          />
          <ShareLinks
            documentId={document.id}
            canManage={!document.is_worm_locked}
          />
        </div>
      ),
    },
  ]

  return (
    <div>
      {/* Breadcrumb */}
      <Breadcrumb
        className="mb-4"
        items={[
          { title: <a onClick={() => navigate('/documents')}>Documents</a> },
          { title: document.title },
        ]}
      />

      {/* Header */}
      <Card className="mb-4">
        <div className="flex justify-between items-start">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-primary-50 rounded-lg">
              <FileOutlined className="text-2xl text-primary-500" />
            </div>
            <div>
              <Title level={4} className="mb-1">
                {document.title}
              </Title>
              <Space>
                <Tag color={getStatusColor(document.lifecycle_status)}>
                  {document.lifecycle_status}
                </Tag>
                {document.is_worm_locked && (
                  <Tag icon={<LockOutlined />} color="red">
                    WORM Locked
                  </Tag>
                )}
                {document.legal_hold && (
                  <Tag icon={<SafetyOutlined />} color="orange">
                    Legal Hold
                  </Tag>
                )}
              </Space>
              <div className="mt-3">
                <LifecycleTimeline currentStatus={document.lifecycle_status} />
              </div>
            </div>
          </div>

          <Space wrap>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/documents')}>
              Back
            </Button>
            <Button icon={<EyeOutlined />} type="primary" onClick={() => setViewerOpen(true)}>
              View
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleDownload}>
              Download
            </Button>
            {document.ocr_status !== 'COMPLETED' && (
              <Button 
                icon={<ScanOutlined />} 
                onClick={() => ocrMutation.mutate()}
                loading={ocrMutation.isPending}
              >
                Extract Data
              </Button>
            )}
            {!document.is_worm_locked && canEdit && (
              <Button icon={<EditOutlined />} onClick={handleEdit}>
                Edit
              </Button>
            )}
            {getNextActions().map((action) => (
              <Button
                key={action.status}
                type={action.status === 'APPROVED' ? 'primary' : 'default'}
                onClick={() => {
                  if (action.label === 'Submit for Review') {
                    submitForApprovalMutation.mutate()
                  } else {
                    transitionMutation.mutate({ toStatus: action.status })
                  }
                }}
                loading={transitionMutation.isPending || submitForApprovalMutation.isPending}
              >
                {action.label}
              </Button>
            ))}
          </Space>
        </div>
      </Card>

      {/* Content */}
      <Card>
        <Tabs items={tabItems} activeKey={activeTab} onChange={setActiveTab} />
      </Card>

      {/* Document Viewer Modal */}
      <DocumentViewer
        documentId={document.id}
        fileName={document.file_name}
        mimeType={document.mime_type}
        open={viewerOpen}
        onClose={() => setViewerOpen(false)}
        extractedMetadata={document.extracted_metadata}
        ocrText={document.ocr_text}
      />
    </div>
  )
}

export default DocumentDetailPage
