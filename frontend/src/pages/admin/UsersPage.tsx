import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, Table, Tag, Typography, Button, Space, Avatar, Spin, Empty } from 'antd'
import { UserOutlined, PlusOutlined, TeamOutlined } from '@ant-design/icons'
import api from '@/services/api'

const { Title } = Typography

interface User {
  id: string
  email: string
  full_name: string
  is_active: boolean
  role?: { name: string }
  department?: { name: string }
  created_at: string
  last_login_at?: string
}

const UsersPage: React.FC = () => {
  const { data: users, isLoading } = useQuery<User[]>({
    queryKey: ['admin', 'users'],
    queryFn: async () => {
      const response = await api.get('/admin/users')
      return response.data
    },
  })

  const columns = [
    {
      title: 'User',
      key: 'user',
      render: (_: any, record: User) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <div className="font-medium">{record.full_name}</div>
            <div className="text-gray-500 text-xs">{record.email}</div>
          </div>
        </Space>
      ),
    },
    {
      title: 'Role',
      key: 'role',
      render: (_: any, record: User) => (
        <Tag color="blue">{record.role?.name || 'No Role'}</Tag>
      ),
    },
    {
      title: 'Department',
      key: 'department',
      render: (_: any, record: User) => record.department?.name || '-',
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>
          {active ? 'Active' : 'Inactive'}
        </Tag>
      ),
    },
    {
      title: 'Last Login',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (date: string) => date ? new Date(date).toLocaleString() : 'Never',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: () => (
        <Space>
          <Button type="link" size="small">Edit</Button>
          <Button type="link" size="small">Reset Password</Button>
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
          <TeamOutlined className="mr-2" />
          User Management
        </Title>
        <Button type="primary" icon={<PlusOutlined />}>
          Add User
        </Button>
      </div>

      <Card>
        {users && users.length > 0 ? (
          <Table
            dataSource={users}
            columns={columns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
          />
        ) : (
          <Empty description="No users found" />
        )}
      </Card>
    </div>
  )
}

export default UsersPage
