import React from 'react'
import { Card, Tag, Typography, Space, Dropdown, Button } from 'antd'
import {
  FileOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  FileExcelOutlined,
  FileImageOutlined,
  MoreOutlined,
  DownloadOutlined,
  EyeOutlined,
  EditOutlined,
  DeleteOutlined,
  LockOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import type { Document, SourceType } from '@/types'
import StatusBadge from './StatusBadge'
import dayjs from 'dayjs'

const { Text, Title } = Typography

interface DocumentCardProps {
  document: Document
  onDownload?: (doc: Document) => void
  onDelete?: (doc: Document) => void
}

const getFileIcon = (mimeType: string) => {
  if (mimeType.includes('pdf')) return <FilePdfOutlined className="text-red-500" />
  if (mimeType.includes('word') || mimeType.includes('document')) return <FileWordOutlined className="text-blue-500" />
  if (mimeType.includes('excel') || mimeType.includes('sheet')) return <FileExcelOutlined className="text-green-500" />
  if (mimeType.includes('image')) return <FileImageOutlined className="text-purple-500" />
  return <FileOutlined className="text-gray-500" />
}

const getSourceTypeColor = (type: SourceType) => {
  const colors: Record<SourceType, string> = {
    CUSTOMER: 'blue',
    VENDOR: 'green',
    INTERNAL: 'gold',
  }
  return colors[type]
}

const DocumentCard: React.FC<DocumentCardProps> = ({ document, onDownload, onDelete }) => {
  const navigate = useNavigate()

  const menuItems = [
    {
      key: 'view',
      icon: <EyeOutlined />,
      label: 'View Details',
      onClick: () => navigate(`/documents/${document.id}`),
    },
    {
      key: 'download',
      icon: <DownloadOutlined />,
      label: 'Download',
      onClick: () => onDownload?.(document),
    },
    ...(document.is_worm_locked ? [] : [
      {
        key: 'edit',
        icon: <EditOutlined />,
        label: 'Edit',
        onClick: () => navigate(`/documents/${document.id}/edit`),
      },
    ]),
    { type: 'divider' as const },
    {
      key: 'delete',
      icon: <DeleteOutlined />,
      label: 'Delete',
      danger: true,
      disabled: document.is_worm_locked || document.legal_hold,
      onClick: () => onDelete?.(document),
    },
  ]

  return (
    <Card
      hoverable
      className="h-full"
      onClick={() => navigate(`/documents/${document.id}`)}
      actions={[
        <Button
          key="download"
          type="text"
          icon={<DownloadOutlined />}
          onClick={(e) => {
            e.stopPropagation()
            onDownload?.(document)
          }}
        />,
        <Dropdown
          key="more"
          menu={{ items: menuItems }}
          trigger={['click']}
        >
          <Button
            type="text"
            icon={<MoreOutlined />}
            onClick={(e) => e.stopPropagation()}
          />
        </Dropdown>,
      ]}
    >
      <div className="flex items-start gap-3">
        <div className="text-3xl">
          {getFileIcon(document.mime_type)}
        </div>
        <div className="flex-1 min-w-0">
          <Title level={5} className="mb-1 truncate" title={document.title}>
            {document.title}
          </Title>
          <Text type="secondary" className="text-sm block truncate">
            {document.file_name}
          </Text>
        </div>
      </div>

      <div className="mt-4">
        <Space wrap size={[4, 4]}>
          <StatusBadge status={document.lifecycle_status} size="small" />
          <Tag color={getSourceTypeColor(document.source_type)} className="text-xs">
            {document.source_type}
          </Tag>
          {document.is_worm_locked && (
            <Tag icon={<LockOutlined />} color="red" className="text-xs">
              WORM
            </Tag>
          )}
          {document.legal_hold && (
            <Tag icon={<SafetyOutlined />} color="orange" className="text-xs">
              Hold
            </Tag>
          )}
        </Space>
      </div>

      <div className="mt-3 text-xs text-gray-500">
        <div className="flex justify-between">
          <span>{(document.file_size / 1024).toFixed(1)} KB</span>
          <span>{dayjs(document.created_at).format('MMM D, YYYY')}</span>
        </div>
      </div>
    </Card>
  )
}

export default DocumentCard
