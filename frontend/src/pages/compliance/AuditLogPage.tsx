import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Table, Tag, Typography, DatePicker, Select, Space, Spin, Input } from 'antd'
import { AuditOutlined, SearchOutlined } from '@ant-design/icons'
import api from '@/services/api'

const { Title } = Typography
const { RangePicker } = DatePicker

interface AuditEvent {
  id: string
  event_type: string
  entity_type: string
  entity_id: string
  user_id: string
  user_email?: string
  ip_address: string
  created_at: string
  event_metadata?: Record<string, any>
}

const AuditLogPage: React.FC = () => {
  const [eventType, setEventType] = useState<string | undefined>()
  const [searchQuery, setSearchQuery] = useState('')

  const { data: events, isLoading } = useQuery<{ items: AuditEvent[]; total: number }>({
    queryKey: ['audit-events', eventType],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (eventType) params.set('event_type', eventType)
      const response = await api.get(`/audit/events?${params.toString()}`)
      return response.data
    },
  })

  const getEventColor = (type: string) => {
    if (type.includes('CREATE') || type.includes('UPLOAD')) return 'green'
    if (type.includes('DELETE') || type.includes('REMOVE')) return 'red'
    if (type.includes('UPDATE') || type.includes('EDIT')) return 'blue'
    if (type.includes('VIEW') || type.includes('DOWNLOAD')) return 'default'
    if (type.includes('LOGIN') || type.includes('LOGOUT')) return 'purple'
    return 'default'
  }

  const columns = [
    {
      title: 'Timestamp',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
      width: 180,
    },
    {
      title: 'Event Type',
      dataIndex: 'event_type',
      key: 'event_type',
      render: (type: string) => (
        <Tag color={getEventColor(type)}>{type}</Tag>
      ),
    },
    {
      title: 'Entity',
      key: 'entity',
      render: (_: any, record: AuditEvent) => (
        <span>{record.entity_type} ({record.entity_id?.slice(0, 8)}...)</span>
      ),
    },
    {
      title: 'User',
      dataIndex: 'user_email',
      key: 'user_email',
      render: (email: string, record: AuditEvent) => email || record.user_id?.slice(0, 8) || 'System',
    },
    {
      title: 'IP Address',
      dataIndex: 'ip_address',
      key: 'ip_address',
    },
    {
      title: 'Details',
      dataIndex: 'event_metadata',
      key: 'event_metadata',
      render: (metadata: Record<string, any>) => (
        <span className="text-gray-500 text-xs">
          {metadata?.description || '-'}
        </span>
      ),
      ellipsis: true,
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <Title level={2}>
          <AuditOutlined className="mr-2" />
          Audit Log
        </Title>
      </div>

      <Card>
        <Space className="mb-4" wrap>
          <Input
            placeholder="Search events..."
            prefix={<SearchOutlined />}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ width: 250 }}
          />
          <Select
            placeholder="Event Type"
            allowClear
            style={{ width: 200 }}
            value={eventType}
            onChange={setEventType}
            options={[
              { label: 'Document Upload', value: 'DOCUMENT_UPLOAD' },
              { label: 'Document View', value: 'DOCUMENT_VIEW' },
              { label: 'Document Download', value: 'DOCUMENT_DOWNLOAD' },
              { label: 'Document Delete', value: 'DOCUMENT_DELETE' },
              { label: 'User Login', value: 'USER_LOGIN' },
              { label: 'Approval Action', value: 'APPROVAL_ACTION' },
            ]}
          />
          <RangePicker />
        </Space>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <Spin size="large" />
          </div>
        ) : (
          <Table
            dataSource={events?.items || []}
            columns={columns}
            rowKey="id"
            pagination={{
              total: events?.total || 0,
              pageSize: 20,
              showTotal: (total) => `Total ${total} events`,
            }}
            size="small"
          />
        )}
      </Card>
    </div>
  )
}

export default AuditLogPage
