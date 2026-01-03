import React, { useState } from 'react'
import {
  Card,
  Tabs,
  Table,
  Button,
  Tag,
  Space,
  Typography,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  message,
  Tooltip,
  Alert,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  LockOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type { ColumnsType } from 'antd/es/table'
import api from '@/services/api'

const { Title, Text } = Typography
const { TextArea } = Input
const { Option } = Select

interface PIIPattern {
  id: string
  name: string
  pii_type: string
  regex_pattern: string
  mask_format: string | null
  sensitivity_level: string
  is_active: boolean
  is_system: boolean
}

interface PIIPolicy {
  id: string
  name: string
  description: string | null
  pii_types: string[]
  action: string
  is_active: boolean
  priority: number
}

const PII_TYPES = [
  'CREDIT_CARD',
  'EMAIL',
  'PHONE',
  'AADHAAR',
  'PAN',
  'SSN',
  'IBAN',
  'PASSPORT',
  'DRIVING_LICENSE',
  'BANK_ACCOUNT',
  'CUSTOM',
]

const PII_ACTIONS = [
  { value: 'MASK', label: 'Mask (show partial)', color: 'blue' },
  { value: 'REDACT', label: 'Redact (replace with [REDACTED])', color: 'orange' },
  { value: 'ENCRYPT', label: 'Encrypt in storage', color: 'green' },
  { value: 'LOG_ONLY', label: 'Log only', color: 'default' },
  { value: 'BLOCK', label: 'Block upload', color: 'red' },
]

const SENSITIVITY_LEVELS = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

const PIISettingsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState('patterns')
  const [patternModalOpen, setPatternModalOpen] = useState(false)
  const [policyModalOpen, setPolicyModalOpen] = useState(false)
  const [editingPattern, setEditingPattern] = useState<PIIPattern | null>(null)
  const [editingPolicy, setEditingPolicy] = useState<PIIPolicy | null>(null)
  const [patternForm] = Form.useForm()
  const [policyForm] = Form.useForm()

  // Fetch patterns
  const { data: patterns, isLoading: patternsLoading } = useQuery({
    queryKey: ['pii-patterns'],
    queryFn: async () => {
      const response = await api.get('/pii/patterns')
      return response.data as PIIPattern[]
    },
  })

  // Fetch policies
  const { data: policies, isLoading: policiesLoading } = useQuery({
    queryKey: ['pii-policies'],
    queryFn: async () => {
      const response = await api.get('/pii/policies')
      return response.data as PIIPolicy[]
    },
  })

  // Pattern mutations
  const createPatternMutation = useMutation({
    mutationFn: async (data: any) => {
      await api.post('/pii/patterns', data)
    },
    onSuccess: () => {
      message.success('Pattern created successfully')
      queryClient.invalidateQueries({ queryKey: ['pii-patterns'] })
      setPatternModalOpen(false)
      patternForm.resetFields()
    },
  })

  const updatePatternMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: any }) => {
      await api.put(`/pii/patterns/${id}`, data)
    },
    onSuccess: () => {
      message.success('Pattern updated successfully')
      queryClient.invalidateQueries({ queryKey: ['pii-patterns'] })
      setPatternModalOpen(false)
      setEditingPattern(null)
      patternForm.resetFields()
    },
  })

  const deletePatternMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/pii/patterns/${id}`)
    },
    onSuccess: () => {
      message.success('Pattern deleted')
      queryClient.invalidateQueries({ queryKey: ['pii-patterns'] })
    },
  })

  // Policy mutations
  const createPolicyMutation = useMutation({
    mutationFn: async (data: any) => {
      await api.post('/pii/policies', data)
    },
    onSuccess: () => {
      message.success('Policy created successfully')
      queryClient.invalidateQueries({ queryKey: ['pii-policies'] })
      setPolicyModalOpen(false)
      policyForm.resetFields()
    },
  })

  const updatePolicyMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: any }) => {
      await api.put(`/pii/policies/${id}`, data)
    },
    onSuccess: () => {
      message.success('Policy updated successfully')
      queryClient.invalidateQueries({ queryKey: ['pii-policies'] })
      setPolicyModalOpen(false)
      setEditingPolicy(null)
      policyForm.resetFields()
    },
  })

  const getSensitivityColor = (level: string) => {
    const colors: Record<string, string> = {
      LOW: 'green',
      MEDIUM: 'blue',
      HIGH: 'orange',
      CRITICAL: 'red',
    }
    return colors[level] || 'default'
  }

  const patternColumns: ColumnsType<PIIPattern> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <Space>
          {record.is_system && (
            <Tooltip title="System pattern (read-only)">
              <LockOutlined className="text-gray-400" />
            </Tooltip>
          )}
          <Text>{name}</Text>
        </Space>
      ),
    },
    {
      title: 'PII Type',
      dataIndex: 'pii_type',
      key: 'pii_type',
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: 'Sensitivity',
      dataIndex: 'sensitivity_level',
      key: 'sensitivity_level',
      render: (level: string) => (
        <Tag color={getSensitivityColor(level)}>{level}</Tag>
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
      render: (_, record) => (
        <Space>
          <Tooltip title="View pattern">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => {
                setEditingPattern(record)
                patternForm.setFieldsValue(record)
                setPatternModalOpen(true)
              }}
            />
          </Tooltip>
          {!record.is_system && (
            <>
              <Tooltip title="Edit">
                <Button
                  type="text"
                  icon={<EditOutlined />}
                  onClick={() => {
                    setEditingPattern(record)
                    patternForm.setFieldsValue(record)
                    setPatternModalOpen(true)
                  }}
                />
              </Tooltip>
              <Tooltip title="Delete">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => {
                    Modal.confirm({
                      title: 'Delete Pattern',
                      content: 'Are you sure you want to delete this pattern?',
                      okText: 'Delete',
                      okButtonProps: { danger: true },
                      onOk: () => deletePatternMutation.mutate(record.id),
                    })
                  }}
                />
              </Tooltip>
            </>
          )}
        </Space>
      ),
    },
  ]

  const policyColumns: ColumnsType<PIIPolicy> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'PII Types',
      dataIndex: 'pii_types',
      key: 'pii_types',
      render: (types: string[]) => (
        <Space wrap>
          {types.map((type) => (
            <Tag key={type}>{type}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: 'Action',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => {
        const actionConfig = PII_ACTIONS.find((a) => a.value === action)
        return (
          <Tag color={actionConfig?.color || 'default'}>
            {actionConfig?.label || action}
          </Tag>
        )
      },
    },
    {
      title: 'Priority',
      dataIndex: 'priority',
      key: 'priority',
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
      render: (_, record) => (
        <Space>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingPolicy(record)
              policyForm.setFieldsValue(record)
              setPolicyModalOpen(true)
            }}
          />
        </Space>
      ),
    },
  ]

  const tabItems = [
    {
      key: 'patterns',
      label: 'Detection Patterns',
      children: (
        <div>
          <div className="flex justify-between mb-4">
            <Text type="secondary">
              Configure patterns for detecting PII in documents
            </Text>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingPattern(null)
                patternForm.resetFields()
                setPatternModalOpen(true)
              }}
            >
              Add Pattern
            </Button>
          </div>
          <Table
            columns={patternColumns}
            dataSource={patterns}
            rowKey="id"
            loading={patternsLoading}
            pagination={{ pageSize: 10 }}
          />
        </div>
      ),
    },
    {
      key: 'policies',
      label: 'Handling Policies',
      children: (
        <div>
          <div className="flex justify-between mb-4">
            <Text type="secondary">
              Configure how detected PII should be handled
            </Text>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingPolicy(null)
                policyForm.resetFields()
                setPolicyModalOpen(true)
              }}
            >
              Add Policy
            </Button>
          </div>
          <Table
            columns={policyColumns}
            dataSource={policies}
            rowKey="id"
            loading={policiesLoading}
            pagination={{ pageSize: 10 }}
          />
        </div>
      ),
    },
  ]

  return (
    <div>
      <Title level={3} className="mb-6">
        PII Detection Settings
      </Title>

      <Alert
        message="Data Loss Prevention"
        description="Configure automatic detection and handling of Personally Identifiable Information (PII) in documents. System patterns are pre-configured and cannot be modified."
        type="info"
        showIcon
        icon={<ExclamationCircleOutlined />}
        className="mb-6"
      />

      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Card>

      {/* Pattern Modal */}
      <Modal
        title={editingPattern ? 'Edit Pattern' : 'Create Pattern'}
        open={patternModalOpen}
        onOk={() => patternForm.submit()}
        onCancel={() => {
          setPatternModalOpen(false)
          setEditingPattern(null)
          patternForm.resetFields()
        }}
        okText={editingPattern ? 'Update' : 'Create'}
        confirmLoading={createPatternMutation.isPending || updatePatternMutation.isPending}
        width={600}
      >
        <Form
          form={patternForm}
          layout="vertical"
          onFinish={(values) => {
            if (editingPattern) {
              if (editingPattern.is_system) {
                message.error('Cannot modify system patterns')
                return
              }
              updatePatternMutation.mutate({ id: editingPattern.id, data: values })
            } else {
              createPatternMutation.mutate(values)
            }
          }}
          initialValues={{ is_active: true, sensitivity_level: 'HIGH' }}
        >
          <Form.Item
            name="name"
            label="Pattern Name"
            rules={[{ required: true }]}
          >
            <Input placeholder="Enter pattern name" disabled={editingPattern?.is_system} />
          </Form.Item>

          <Form.Item
            name="pii_type"
            label="PII Type"
            rules={[{ required: true }]}
          >
            <Select placeholder="Select PII type" disabled={editingPattern?.is_system}>
              {PII_TYPES.map((type) => (
                <Option key={type} value={type}>
                  {type}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="regex_pattern"
            label="Regex Pattern"
            rules={[{ required: true }]}
          >
            <TextArea
              rows={2}
              placeholder="Enter regex pattern"
              disabled={editingPattern?.is_system}
            />
          </Form.Item>

          <Form.Item name="mask_format" label="Mask Format">
            <Input
              placeholder="e.g., ****-****-****-{last4}"
              disabled={editingPattern?.is_system}
            />
          </Form.Item>

          <Form.Item name="sensitivity_level" label="Sensitivity Level">
            <Select disabled={editingPattern?.is_system}>
              {SENSITIVITY_LEVELS.map((level) => (
                <Option key={level} value={level}>
                  {level}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch disabled={editingPattern?.is_system} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Policy Modal */}
      <Modal
        title={editingPolicy ? 'Edit Policy' : 'Create Policy'}
        open={policyModalOpen}
        onOk={() => policyForm.submit()}
        onCancel={() => {
          setPolicyModalOpen(false)
          setEditingPolicy(null)
          policyForm.resetFields()
        }}
        okText={editingPolicy ? 'Update' : 'Create'}
        confirmLoading={createPolicyMutation.isPending || updatePolicyMutation.isPending}
        width={600}
      >
        <Form
          form={policyForm}
          layout="vertical"
          onFinish={(values) => {
            if (editingPolicy) {
              updatePolicyMutation.mutate({ id: editingPolicy.id, data: values })
            } else {
              createPolicyMutation.mutate(values)
            }
          }}
          initialValues={{ is_active: true, priority: 0 }}
        >
          <Form.Item
            name="name"
            label="Policy Name"
            rules={[{ required: true }]}
          >
            <Input placeholder="Enter policy name" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <TextArea rows={2} placeholder="Enter description" />
          </Form.Item>

          <Form.Item
            name="pii_types"
            label="PII Types"
            rules={[{ required: true }]}
          >
            <Select mode="multiple" placeholder="Select PII types">
              {PII_TYPES.map((type) => (
                <Option key={type} value={type}>
                  {type}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="action"
            label="Action"
            rules={[{ required: true }]}
          >
            <Select placeholder="Select action">
              {PII_ACTIONS.map((action) => (
                <Option key={action.value} value={action.value}>
                  {action.label}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="priority" label="Priority">
            <Input type="number" placeholder="Higher priority policies are applied first" />
          </Form.Item>

          <Form.Item name="is_active" label="Active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default PIISettingsPage
