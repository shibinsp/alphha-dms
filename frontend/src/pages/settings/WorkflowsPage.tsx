import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Table, Tag, Typography, Button, Space, Spin, Empty, Badge } from 'antd'
import { SettingOutlined, PlusOutlined, BranchesOutlined } from '@ant-design/icons'
import api from '@/services/api'

const { Title, Text } = Typography

interface Workflow {
  id: string
  name: string
  description: string
  workflow_type: string
  is_active: boolean
  trigger_conditions?: Record<string, any>
  steps: Array<{
    id: string
    name: string
    step_order: number
  }>
  created_at: string
}

const WorkflowsPage: React.FC = () => {
  const { data: workflows, isLoading } = useQuery<Workflow[]>({
    queryKey: ['workflows'],
    queryFn: async () => {
      const response = await api.get('/workflows')
      return response.data
    },
  })

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'DOCUMENT_APPROVAL': return 'blue'
      case 'REVIEW': return 'purple'
      case 'PUBLISHING': return 'green'
      default: return 'default'
    }
  }

  const columns = [
    {
      title: 'Workflow Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          <BranchesOutlined />
          <span className="font-medium">{name}</span>
        </Space>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'workflow_type',
      key: 'workflow_type',
      render: (type: string) => (
        <Tag color={getTypeColor(type)}>{type}</Tag>
      ),
    },
    {
      title: 'Steps',
      dataIndex: 'steps',
      key: 'steps',
      render: (steps: Array<{ name: string }>) => (
        <Space>
          {steps?.map((step, idx) => (
            <Badge key={idx} count={idx + 1} style={{ backgroundColor: '#1890ff' }}>
              <Tag>{step.name}</Tag>
            </Badge>
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
          <Button type="link" size="small">Duplicate</Button>
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
          <SettingOutlined className="mr-2" />
          Workflow Configuration
        </Title>
        <Button type="primary" icon={<PlusOutlined />}>
          Create Workflow
        </Button>
      </div>

      <Card>
        <Text type="secondary" className="block mb-4">
          Configure approval workflows for document processing. Each workflow can have multiple steps with different approvers.
        </Text>

        {workflows && workflows.length > 0 ? (
          <Table
            dataSource={workflows}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
          />
        ) : (
          <Empty description="No workflows configured" />
        )}
      </Card>
    </div>
  )
}

export default WorkflowsPage
