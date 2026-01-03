import React from 'react'
import { Steps, Tag, Space } from 'antd'
import {
  EditOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  InboxOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import type { LifecycleStatus } from '@/types'


interface LifecycleTransition {
  id: string
  from_status: LifecycleStatus | null
  to_status: LifecycleStatus
  transitioned_at: string
  transitioned_by?: {
    id: string
    full_name: string
  }
  reason?: string
}

interface LifecycleTimelineProps {
  currentStatus: LifecycleStatus
  transitions?: LifecycleTransition[]
  compact?: boolean
}

const statusConfig: Record<LifecycleStatus, { icon: React.ReactNode; color: string }> = {
  DRAFT: { icon: <EditOutlined />, color: '#8c8c8c' },
  REVIEW: { icon: <ClockCircleOutlined />, color: '#1890ff' },
  APPROVED: { icon: <CheckCircleOutlined />, color: '#52c41a' },
  ARCHIVED: { icon: <InboxOutlined />, color: '#faad14' },
  DELETED: { icon: <DeleteOutlined />, color: '#ff4d4f' },
}

const LIFECYCLE_ORDER: LifecycleStatus[] = ['DRAFT', 'REVIEW', 'APPROVED', 'ARCHIVED']

const LifecycleTimeline: React.FC<LifecycleTimelineProps> = ({
  currentStatus,
  transitions = [],
  compact = false,
}) => {
  const currentIndex = LIFECYCLE_ORDER.indexOf(currentStatus)

  const items = LIFECYCLE_ORDER.map((status, index) => {
    const config = statusConfig[status]
    const isCompleted = index < currentIndex
    const isCurrent = status === currentStatus

    let stepStatus: 'wait' | 'process' | 'finish' | 'error' = 'wait'
    if (isCompleted) stepStatus = 'finish'
    if (isCurrent) stepStatus = 'process'
    if (currentStatus === 'DELETED') stepStatus = 'error'

    const transition = transitions.find((t) => t.to_status === status)

    return {
      title: (
        <Space>
          <span>{status}</span>
          {isCurrent && <Tag color={config.color}>Current</Tag>}
        </Space>
      ),
      description: !compact && transition && (
        <div className="text-xs text-gray-500">
          {transition.transitioned_by && (
            <div>By: {transition.transitioned_by.full_name}</div>
          )}
          {transition.reason && (
            <div className="italic">"{transition.reason}"</div>
          )}
        </div>
      ),
      status: stepStatus,
      icon: config.icon,
    }
  })

  return (
    <Steps
      current={currentIndex}
      items={items}
      size={compact ? 'small' : 'default'}
      direction={compact ? 'horizontal' : 'horizontal'}
    />
  )
}

export default LifecycleTimeline
