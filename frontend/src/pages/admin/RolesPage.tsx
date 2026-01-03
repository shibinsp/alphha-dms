import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Card, Table, Tag, Typography, Button, Space, Spin, Empty, Modal,
  Form, Input, Checkbox, message, Divider, Collapse
} from 'antd'
import { SafetyOutlined, PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
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

// Feature-based permissions as per Excel requirements
const PERMISSION_GROUPS = {
  'Documents': [
    'documents.view',
    'documents.create',
    'documents.edit',
    'documents.delete',
    'documents.download',
    'documents.share',
    'documents.checkout',
  ],
  'Approvals': [
    'approvals.view',
    'approvals.approve',
    'approvals.reject',
    'approvals.delegate',
  ],
  'Compliance': [
    'compliance.legal_hold.view',
    'compliance.legal_hold.manage',
    'compliance.retention.view',
    'compliance.retention.manage',
    'compliance.audit.view',
    'compliance.audit.export',
  ],
  'PII & DLP': [
    'pii.view_masked',
    'pii.view_unmasked',
    'pii.manage_patterns',
    'pii.export_sensitive',
  ],
  'Administration': [
    'admin.users.view',
    'admin.users.manage',
    'admin.roles.view',
    'admin.roles.manage',
    'admin.settings.view',
    'admin.settings.manage',
  ],
  'Analytics': [
    'analytics.view',
    'analytics.export',
    'analytics.manage_dashboards',
  ],
  'Entities': [
    'entities.customers.view',
    'entities.customers.manage',
    'entities.vendors.view',
    'entities.vendors.manage',
    'entities.departments.view',
    'entities.departments.manage',
  ],
}

const RolesPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingRole, setEditingRole] = useState<Role | null>(null)
  const [form] = Form.useForm()

  const { data: roles, isLoading } = useQuery<Role[]>({
    queryKey: ['admin', 'roles'],
    queryFn: async () => {
      const response = await api.get('/admin/roles')
      return response.data
    },
  })

  const createMutation = useMutation({
    mutationFn: async (data: { name: string; description: string; permissions: string[] }) => {
      return api.post('/admin/roles', data)
    },
    onSuccess: () => {
      message.success('Role created successfully')
      queryClient.invalidateQueries({ queryKey: ['admin', 'roles'] })
      setModalOpen(false)
      form.resetFields()
    },
    onError: () => {
      message.error('Failed to create role')
    },
  })

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: any }) => {
      return api.put(`/admin/roles/${id}`, data)
    },
    onSuccess: () => {
      message.success('Role updated successfully')
      queryClient.invalidateQueries({ queryKey: ['admin', 'roles'] })
      setModalOpen(false)
      setEditingRole(null)
      form.resetFields()
    },
    onError: () => {
      message.error('Failed to update role')
    },
  })

  const handleSubmit = (values: any) => {
    const permissions = Object.entries(values)
      .filter(([key, val]) => key.startsWith('perm_') && val)
      .map(([key]) => key.replace('perm_', ''))

    const data = {
      name: values.name,
      description: values.description,
      permissions,
    }

    if (editingRole) {
      updateMutation.mutate({ id: editingRole.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const openEditModal = (role: Role) => {
    setEditingRole(role)
    const formValues: any = {
      name: role.name,
      description: role.description,
    }
    role.permissions?.forEach((p) => {
      formValues[`perm_${p}`] = true
    })
    form.setFieldsValue(formValues)
    setModalOpen(true)
  }

  const getPermissionColor = (perm: string) => {
    if (perm.includes('delete') || perm.includes('admin') || perm.includes('manage')) return 'red'
    if (perm.includes('create') || perm.includes('approve')) return 'green'
    if (perm.includes('view')) return 'blue'
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
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openEditModal(record)}
          >
            Edit
          </Button>
          {!record.is_system && (
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              Delete
            </Button>
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
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => {
            setEditingRole(null)
            form.resetFields()
            setModalOpen(true)
          }}
        >
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

      {/* Role Modal */}
      <Modal
        title={editingRole ? 'Edit Role' : 'Create Role'}
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false)
          setEditingRole(null)
          form.resetFields()
        }}
        onOk={() => form.submit()}
        width={700}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="Role Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., Document Manager" disabled={editingRole?.is_system} />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} placeholder="Describe the role's purpose" />
          </Form.Item>

          <Divider>Permissions</Divider>

          <Collapse
            defaultActiveKey={['Documents']}
            items={Object.entries(PERMISSION_GROUPS).map(([group, perms]) => ({
              key: group,
              label: <strong>{group}</strong>,
              children: (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
                  {perms.map((perm) => (
                    <Form.Item
                      key={perm}
                      name={`perm_${perm}`}
                      valuePropName="checked"
                      style={{ marginBottom: 0 }}
                    >
                      <Checkbox>
                        <Tag color={getPermissionColor(perm)} style={{ marginLeft: 4 }}>
                          {perm.split('.').pop()}
                        </Tag>
                        <span style={{ fontSize: 12, color: '#888' }}>{perm}</span>
                      </Checkbox>
                    </Form.Item>
                  ))}
                </div>
              ),
            }))}
          />
        </Form>
      </Modal>
    </div>
  )
}

export default RolesPage
