import React, { useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Table,
  Card,
  Button,
  Input,
  Select,
  Space,
  Tag,
  Typography,
  Dropdown,
  message,
  Tooltip,
} from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  DownloadOutlined,
  EyeOutlined,
  DeleteOutlined,
  MoreOutlined,
  FilterOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ColumnsType } from 'antd/es/table'
import { documentService, DocumentFilters } from '@/services/documentService'
import type { Document, SourceType, LifecycleStatus } from '@/types'
import dayjs from 'dayjs'

const { Title } = Typography
const { Option } = Select

const DocumentListPage: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [filters, setFilters] = useState<DocumentFilters>({
    page: 1,
    page_size: 20,
  })

  // Fetch documents
  const { data, isLoading } = useQuery({
    queryKey: ['documents', filters],
    queryFn: () => documentService.getDocuments(filters),
  })

  // Fetch document types for filter
  const { data: documentTypes } = useQuery({
    queryKey: ['document-types'],
    queryFn: () => documentService.getDocumentTypes(),
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: documentService.deleteDocument,
    onSuccess: () => {
      message.success('Document deleted')
      queryClient.invalidateQueries({ queryKey: ['documents'] })
    },
    onError: () => {
      message.error('Failed to delete document')
    },
  })

  // Download handler
  const handleDownload = useCallback(async (doc: Document) => {
    try {
      const blob = await documentService.downloadDocument(doc.id)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = doc.file_name
      a.click()
      window.URL.revokeObjectURL(url)
    } catch {
      message.error('Failed to download document')
    }
  }, [])

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

  const getSourceTypeColor = (type: SourceType) => {
    const colors: Record<SourceType, string> = {
      CUSTOMER: 'blue',
      VENDOR: 'green',
      INTERNAL: 'gold',
    }
    return colors[type]
  }

  const columns: ColumnsType<Document> = useMemo(() => [
    {
      title: 'Title',
      dataIndex: 'title',
      key: 'title',
      render: (title: string, record: Document) => (
        <a onClick={() => navigate(`/documents/${record.id}`)}>{title}</a>
      ),
      sorter: true,
    },
    {
      title: 'Type',
      dataIndex: 'document_type',
      key: 'document_type',
      render: (type) => type?.name || '-',
    },
    {
      title: 'Source',
      dataIndex: 'source_type',
      key: 'source_type',
      render: (type: SourceType) => (
        <Tag color={getSourceTypeColor(type)}>{type}</Tag>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'lifecycle_status',
      key: 'lifecycle_status',
      render: (status: LifecycleStatus) => (
        <Tag color={getStatusColor(status)}>{status}</Tag>
      ),
    },
    {
      title: 'Classification',
      dataIndex: 'classification',
      key: 'classification',
      render: (classification: string) => (
        <Tag>{classification}</Tag>
      ),
    },
    {
      title: 'Size',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => `${(size / 1024).toFixed(1)} KB`,
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('MMM D, YYYY'),
      sorter: true,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_, record: Document) => (
        <Dropdown
          menu={{
            items: [
              {
                key: 'view',
                icon: <EyeOutlined />,
                label: 'View',
                onClick: () => navigate(`/documents/${record.id}`),
              },
              {
                key: 'download',
                icon: <DownloadOutlined />,
                label: 'Download',
                onClick: () => handleDownload(record),
              },
              {
                type: 'divider',
              },
              {
                key: 'delete',
                icon: <DeleteOutlined />,
                label: 'Delete',
                danger: true,
                disabled: record.is_worm_locked || record.legal_hold,
                onClick: () => deleteMutation.mutate(record.id),
              },
            ],
          }}
          trigger={['click']}
        >
          <Button type="text" icon={<MoreOutlined />} aria-label="More actions" />
        </Dropdown>
      ),
    },
  ], [navigate, handleDownload, deleteMutation])

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <Title level={3} className="mb-0">
          Documents
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/documents/upload')}
        >
          Upload Document
        </Button>
      </div>

      <Card>
        {/* Filters */}
        <div className="mb-4">
          <Space wrap>
            <Input
              placeholder="Search documents..."
              prefix={<SearchOutlined />}
              style={{ width: 250 }}
              value={filters.search}
              onChange={(e) =>
                setFilters({ ...filters, search: e.target.value, page: 1 })
              }
              allowClear
            />

            <Select
              placeholder="Source Type"
              style={{ width: 150 }}
              value={filters.source_type}
              onChange={(value) =>
                setFilters({ ...filters, source_type: value, page: 1 })
              }
              allowClear
            >
              <Option value="CUSTOMER">Customer</Option>
              <Option value="VENDOR">Vendor</Option>
              <Option value="INTERNAL">Internal</Option>
            </Select>

            <Select
              placeholder="Document Type"
              style={{ width: 180 }}
              value={filters.document_type_id}
              onChange={(value) =>
                setFilters({ ...filters, document_type_id: value, page: 1 })
              }
              allowClear
            >
              {documentTypes?.map((type) => (
                <Option key={type.id} value={type.id}>
                  {type.name}
                </Option>
              ))}
            </Select>

            <Select
              placeholder="Status"
              style={{ width: 130 }}
              value={filters.lifecycle_status}
              onChange={(value) =>
                setFilters({ ...filters, lifecycle_status: value, page: 1 })
              }
              allowClear
            >
              <Option value="DRAFT">Draft</Option>
              <Option value="REVIEW">Review</Option>
              <Option value="APPROVED">Approved</Option>
              <Option value="ARCHIVED">Archived</Option>
            </Select>

            <Tooltip title="Clear filters">
              <Button
                icon={<FilterOutlined />}
                onClick={() =>
                  setFilters({ page: 1, page_size: 20 })
                }
              >
                Clear
              </Button>
            </Tooltip>
          </Space>
        </div>

        {/* Table */}
        <Table
          columns={columns}
          dataSource={data?.items}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: filters.page,
            pageSize: filters.page_size,
            total: data?.total,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} documents`,
            onChange: (page, pageSize) =>
              setFilters({ ...filters, page, page_size: pageSize }),
          }}
        />
      </Card>
    </div>
  )
}

export default DocumentListPage
