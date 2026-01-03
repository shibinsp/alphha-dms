import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Table, Tag, Typography, Button, Space, Spin, Empty } from 'antd'
import { PlusOutlined, ClockCircleOutlined } from '@ant-design/icons'
import api from '@/services/api'

const { Title } = Typography

interface RetentionPolicy {
  id: string
  name: string
  description: string
  retention_days: number
  document_types: string[]
  is_active: boolean
  created_at: string
}

const RetentionPoliciesPage: React.FC = () => {
  const { data: policies, isLoading } = useQuery<RetentionPolicy[]>({
    queryKey: ['retention-policies'],
    queryFn: async () => {
      const response = await api.get('/compliance/retention-policies')
      return response.data
    },
  })

  const columns = [
    {
      title: 'Policy Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Retention Period',
      dataIndex: 'retention_days',
      key: 'retention_days',
      render: (days: number) => {
        if (days >= 365) {
          const years = Math.floor(days / 365)
          return `${years} year${years > 1 ? 's' : ''}`
        }
        return `${days} days`
      },
    },
    {
      title: 'Document Types',
      dataIndex: 'document_types',
      key: 'document_types',
      render: (types: string[]) => (
        <Space wrap>
          {types?.map((type) => (
            <Tag key={type} color="blue">{type}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'default'}>
          {active ? 'Active' : 'Inactive'}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: () => (
        <Space>
          <Button type="link" size="small">Edit</Button>
          <Button type="link" size="small" danger>Delete</Button>
        </Space>
      ),
    },
  ]

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <Title level={2}>
          <ClockCircleOutlined className="mr-2" />
          Retention Policies
        </Title>
        <Button type="primary" icon={<PlusOutlined />}>
          Create Policy
        </Button>
      </div>

      <Card>
        {policies && policies.length > 0 ? (
          <Table
            dataSource={policies}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
          />
        ) : (
          <Empty description="No retention policies configured" />
        )}
      </Card>
    </div>
  )
}

export default RetentionPoliciesPage
