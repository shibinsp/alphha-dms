import React from 'react'
import { Tag } from 'antd'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  EditOutlined,
  InboxOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import type { LifecycleStatus } from '@/types'

interface StatusBadgeProps {
  status: LifecycleStatus
  size?: 'small' | 'default'
}

const statusConfig: Record<LifecycleStatus, { color: string; icon: React.ReactNode; label: string }> = {
  DRAFT: {
    color: 'default',
    icon: <EditOutlined />,
    label: 'Draft',
  },
  REVIEW: {
    color: 'processing',
    icon: <ClockCircleOutlined />,
    label: 'In Review',
  },
  APPROVED: {
    color: 'success',
    icon: <CheckCircleOutlined />,
    label: 'Approved',
  },
  ARCHIVED: {
    color: 'warning',
    icon: <InboxOutlined />,
    label: 'Archived',
  },
  DELETED: {
    color: 'error',
    icon: <DeleteOutlined />,
    label: 'Deleted',
  },
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'default' }) => {
  const config = statusConfig[status]

  return (
    <Tag
      color={config.color}
      icon={config.icon}
      style={size === 'small' ? { fontSize: '12px' } : undefined}
    >
      {config.label}
    </Tag>
  )
}

export default StatusBadge
