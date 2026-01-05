import React, { useState } from 'react'
import {
  Table,
  Button,
  Space,
  Select,
  DatePicker,
  Popconfirm,
  message,
  Typography,
  Tag,
  Modal,
  Form,
  Input,
  Empty,
  Tooltip,
} from 'antd'
import {
  UserOutlined,
  TeamOutlined,
  DeleteOutlined,
  PlusOutlined,
  CrownOutlined,
  EditOutlined,
  EyeOutlined,
  StopOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  sharingService,
  PERMISSION_LEVELS,
  type Permission,
  type GrantPermissionRequest,
} from '@/services/sharingService'
import dayjs from 'dayjs'

const { Text } = Typography

interface SharePermissionsProps {
  documentId: string
  canManage: boolean
}

const getPermissionIcon = (level: string) => {
  switch (level) {
    case 'OWNER':
    case 'CO_OWNER':
      return <CrownOutlined style={{ color: '#faad14' }} />
    case 'EDITOR':
      return <EditOutlined style={{ color: '#1890ff' }} />
    case 'VIEWER_DOWNLOAD':
    case 'VIEWER_NO_DOWNLOAD':
    case 'COMMENTER':
      return <EyeOutlined style={{ color: '#52c41a' }} />
    case 'NO_ACCESS':
      return <StopOutlined style={{ color: '#ff4d4f' }} />
    default:
      return <UserOutlined />
  }
}

const getPermissionColor = (level: string) => {
  switch (level) {
    case 'OWNER':
      return 'gold'
    case 'CO_OWNER':
      return 'orange'
    case 'EDITOR':
      return 'blue'
    case 'COMMENTER':
      return 'cyan'
    case 'VIEWER_DOWNLOAD':
      return 'green'
    case 'VIEWER_NO_DOWNLOAD':
      return 'lime'
    case 'RESTRICTED_MASKED':
      return 'purple'
    case 'NO_ACCESS':
      return 'red'
    default:
      return 'default'
  }
}

const SharePermissions: React.FC<SharePermissionsProps> = ({ documentId, canManage }) => {
  const queryClient = useQueryClient()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [form] = Form.useForm()

  // Fetch permissions
  const { data: permissions = [], isLoading } = useQuery({
    queryKey: ['document-permissions', documentId],
    queryFn: () => sharingService.getPermissions(documentId),
  })

  // Grant permission mutation
  const grantMutation = useMutation({
    mutationFn: (data: GrantPermissionRequest) => sharingService.grantPermission(documentId, data),
    onSuccess: () => {
      message.success('Permission granted')
      queryClient.invalidateQueries({ queryKey: ['document-permissions', documentId] })
      setIsModalOpen(false)
      form.resetFields()
    },
    onError: () => {
      message.error('Failed to grant permission')
    },
  })

  // Revoke permission mutation
  const revokeMutation = useMutation({
    mutationFn: (permissionId: string) => sharingService.revokePermission(documentId, permissionId),
    onSuccess: () => {
      message.success('Permission revoked')
      queryClient.invalidateQueries({ queryKey: ['document-permissions', documentId] })
    },
    onError: () => {
      message.error('Failed to revoke permission')
    },
  })

  const handleSubmit = (values: any) => {
    const data: GrantPermissionRequest = {
      permission_level: values.permission_level,
      expires_at: values.expires_at?.toISOString(),
    }

    if (values.target_type === 'user') {
      data.user_id = values.target_id
    } else if (values.target_type === 'role') {
      data.role_id = values.target_id
    } else if (values.target_type === 'department') {
      data.department_id = values.target_id
    }

    grantMutation.mutate(data)
  }

  const columns = [
    {
      title: 'Granted To',
      key: 'target',
      render: (record: Permission) => (
        <Space>
          {record.user_id ? (
            <>
              <UserOutlined />
              <Text>User: {record.user_id.slice(0, 8)}...</Text>
            </>
          ) : record.role_id ? (
            <>
              <TeamOutlined />
              <Text>Role: {record.role_id.slice(0, 8)}...</Text>
            </>
          ) : (
            <>
              <TeamOutlined />
              <Text>Dept: {record.department_id?.slice(0, 8)}...</Text>
            </>
          )}
        </Space>
      ),
    },
    {
      title: 'Permission',
      dataIndex: 'permission_level',
      key: 'permission_level',
      render: (level: string) => (
        <Tag icon={getPermissionIcon(level)} color={getPermissionColor(level)}>
          {PERMISSION_LEVELS.find((p) => p.value === level)?.label || level}
        </Tag>
      ),
    },
    {
      title: 'Granted By',
      dataIndex: 'granted_by_email',
      key: 'granted_by',
      render: (email: string | null) => email || '-',
    },
    {
      title: 'Expires',
      dataIndex: 'expires_at',
      key: 'expires_at',
      render: (date: string | null) => {
        if (!date) return <Text type="secondary">Never</Text>
        const expiry = dayjs(date)
        const isExpired = expiry.isBefore(dayjs())
        return (
          <Tooltip title={expiry.format('YYYY-MM-DD HH:mm')}>
            <Text type={isExpired ? 'danger' : undefined}>
              {isExpired ? 'Expired' : expiry.fromNow()}
            </Text>
          </Tooltip>
        )
      },
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (record: Permission) =>
        canManage && (
          <Popconfirm
            title="Revoke permission?"
            description="This user will lose access to this document."
            onConfirm={() => revokeMutation.mutate(record.id)}
            okText="Revoke"
            cancelText="Cancel"
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              loading={revokeMutation.isPending}
            />
          </Popconfirm>
        ),
    },
  ]

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <Text strong>Permissions ({permissions.length})</Text>
        {canManage && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setIsModalOpen(true)}
          >
            Add Permission
          </Button>
        )}
      </div>

      {permissions.length === 0 ? (
        <Empty
          description="No permissions granted"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <Table
          dataSource={permissions}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={false}
          size="small"
        />
      )}

      {/* Grant Permission Modal */}
      <Modal
        title="Grant Permission"
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false)
          form.resetFields()
        }}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="target_type"
            label="Grant To"
            rules={[{ required: true, message: 'Select target type' }]}
          >
            <Select placeholder="Select target type">
              <Select.Option value="user">User</Select.Option>
              <Select.Option value="role">Role</Select.Option>
              <Select.Option value="department">Department</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="target_id"
            label="Target ID"
            rules={[{ required: true, message: 'Enter target ID' }]}
          >
            <Input placeholder="Enter user/role/department ID" />
          </Form.Item>

          <Form.Item
            name="permission_level"
            label="Permission Level"
            rules={[{ required: true, message: 'Select permission level' }]}
          >
            <Select placeholder="Select permission">
              {PERMISSION_LEVELS.filter((p) => p.value !== 'OWNER').map((level) => (
                <Select.Option key={level.value} value={level.value}>
                  <Space>
                    {getPermissionIcon(level.value)}
                    <span>{level.label}</span>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      - {level.description}
                    </Text>
                  </Space>
                </Select.Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="expires_at" label="Expires At (Optional)">
            <DatePicker
              showTime
              style={{ width: '100%' }}
              disabledDate={(current) => current && current < dayjs().startOf('day')}
            />
          </Form.Item>

          <Form.Item className="mb-0">
            <Space className="w-full justify-end">
              <Button onClick={() => setIsModalOpen(false)}>Cancel</Button>
              <Button type="primary" htmlType="submit" loading={grantMutation.isPending}>
                Grant Permission
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default SharePermissions
