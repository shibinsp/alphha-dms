import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Typography,
  Tabs,
  Timeline,
  message,
  Spin,
  Breadcrumb,
} from 'antd'
import {
  DownloadOutlined,
  EditOutlined,
  ArrowLeftOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  FileOutlined,
  LockOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { documentService } from '@/services/documentService'
import type { LifecycleStatus } from '@/types'
import dayjs from 'dayjs'

const { Title, Text } = Typography

const DocumentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

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

  // Download handler
  const handleDownload = async () => {
    if (!document) return
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
    const actions = []
    if (document.lifecycle_status === 'DRAFT') {
      actions.push({
        label: 'Submit for Review',
        status: 'REVIEW' as LifecycleStatus,
      })
    } else if (document.lifecycle_status === 'REVIEW') {
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
        <Timeline
          items={versions?.map((version) => ({
            color: version.is_current ? 'green' : 'gray',
            dot: version.is_current ? <CheckCircleOutlined /> : <ClockCircleOutlined />,
            children: (
              <div>
                <Text strong>Version {version.version_number}</Text>
                {version.is_current && <Tag color="green" className="ml-2">Current</Tag>}
                <div className="text-gray-500 text-sm">
                  {dayjs(version.created_at).format('MMM D, YYYY h:mm A')}
                </div>
                {version.change_reason && (
                  <div className="text-gray-600 mt-1">{version.change_reason}</div>
                )}
              </div>
            ),
          })) || []}
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
            </div>
          </div>

          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/documents')}>
              Back
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleDownload}>
              Download
            </Button>
            {!document.is_worm_locked && (
              <Button icon={<EditOutlined />} onClick={() => navigate(`/documents/${id}/edit`)}>
                Edit
              </Button>
            )}
            {getNextActions().map((action) => (
              <Button
                key={action.status}
                type={action.status === 'APPROVED' ? 'primary' : 'default'}
                onClick={() => transitionMutation.mutate({ toStatus: action.status })}
                loading={transitionMutation.isPending}
              >
                {action.label}
              </Button>
            ))}
          </Space>
        </div>
      </Card>

      {/* Content */}
      <Card>
        <Tabs items={tabItems} />
      </Card>
    </div>
  )
}

export default DocumentDetailPage
