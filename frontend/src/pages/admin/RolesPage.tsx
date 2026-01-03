import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Table, Tag, Typography, Button, Space, Spin, Empty, Collapse } from 'antd'
import { SafetyOutlined, PlusOutlined } from '@ant-design/icons'
import api from '@/services/api'

const { Title } = Typography

interface Role {
  id: string
  name: string
  description: string
  permissions: string[]
  user_count?: number
  is_system: boolean
  created_at: string
}

const RolesPage: React.FC = () => {
  const { data: roles, isLoading } = useQuery<Role[]>({
    queryKey: ['admin', 'roles'],
    queryFn: async () => {
      const response = await api.get('/admin/roles')
      return response.data
    },
  })

  const getPermissionColor = (perm: string) => {
    if (perm.includes('delete') || perm.includes('admin')) return 'red'
    if (perm.includes('write') || perm.includes('create')) return 'green'
    if (perm.includes('read') || perm.includes('view')) return 'blue'
    return 'default'
  }

  const columns = [
    {
      title: 'Role Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Role) => (
        <Space>
          <span className="font-medium">{name}</span>
          {record.is_system && <Tag color="purple">System</Tag>}
        </Space>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Users',
      dataIndex: 'user_count',
      key: 'user_count',
      render: (count: number) => count || 0,
    },
    {
      title: 'Permissions',
      dataIndex: 'permissions',
      key: 'permissions',
      render: (permissions: string[]) => (
        <Space wrap>
          {permissions?.slice(0, 3).map((perm) => (
            <Tag key={perm} color={getPermissionColor(perm)}>{perm}</Tag>
          ))}
          {permissions?.length > 3 && (
            <Tag>+{permissions.length - 3} more</Tag>
          )}
        </Space>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Role) => (
        <Space>
          <Button type="link" size="small">Edit</Button>
          {!record.is_system && (
            <Button type="link" size="small" danger>Delete</Button>
          )}
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
          <SafetyOutlined className="mr-2" />
          Role Management
        </Title>
        <Button type="primary" icon={<PlusOutlined />}>
          Create Role
        </Button>
      </div>

      <Card>
        {roles && roles.length > 0 ? (
          <Table
            dataSource={roles}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
          />
        ) : (
          <Empty description="No roles configured" />
        )}
      </Card>
    </div>
  )
}

export default RolesPage
