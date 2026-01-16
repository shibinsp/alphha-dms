import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Card, Table, Button, Modal, Form, Input, Select, Space, Tag, message,
  Popconfirm, Switch, InputNumber, Divider, Typography
} from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, MinusCircleOutlined, BranchesOutlined } from '@ant-design/icons'
import api from '@/services/api'

const { Text } = Typography

interface ApprovalStep {
  id?: string
  step_order: number
  name: string
  approver_role_id?: string
  required_approvals?: number
}

interface Workflow {
  id: string
  name: string
  description?: string
  workflow_type: string
  is_active: boolean
  steps: ApprovalStep[]
  created_at: string
}

interface Role {
  id: string
  name: string
}

const WorkflowsPage: React.FC = () => {
  const [modalOpen, setModalOpen] = useState(false)
  const [editingWorkflow, setEditingWorkflow] = useState<Workflow | null>(null)
  const [form] = Form.useForm()
  const queryClient = useQueryClient()

  const { data: workflows, isLoading } = useQuery<Workflow[]>({
    queryKey: ['workflows'],
    queryFn: () => api.get('/workflows/').then(r => r.data)
  })

  const { data: roles } = useQuery<Role[]>({
    queryKey: ['roles'],
    queryFn: () => api.get('/users/roles').then(r => r.data)
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post('/workflows/', data),
    onSuccess: () => {
      message.success('Workflow created')
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
      closeModal()
    },
    onError: () => message.error('Failed to create workflow')
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => api.put(`/workflows/${id}`, data),
    onSuccess: () => {
      message.success('Workflow updated')
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
      closeModal()
    },
    onError: () => message.error('Failed to update workflow')
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/workflows/${id}`),
    onSuccess: () => {
      message.success('Workflow deleted')
      queryClient.invalidateQueries({ queryKey: ['workflows'] })
    },
    onError: () => message.error('Failed to delete workflow')
  })

  const closeModal = () => {
    setModalOpen(false)
    setEditingWorkflow(null)
    form.resetFields()
  }

  const handleSubmit = (values: any) => {
    const data = {
      name: values.name,
      description: values.description,
      workflow_type: values.workflow_type || 'SEQUENTIAL',
      is_active: values.is_active ?? true,
      steps: (values.steps || []).map((s: any, i: number) => ({
        step_order: i + 1,
        name: s.name,
        approver_role_id: s.approver_role_id,
        required_approvals: s.required_approvals || 1
      }))
    }

    if (editingWorkflow) {
      updateMutation.mutate({ id: editingWorkflow.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const openEdit = (workflow: Workflow) => {
    setEditingWorkflow(workflow)
    form.setFieldsValue({
      name: workflow.name,
      description: workflow.description,
      workflow_type: workflow.workflow_type,
      is_active: workflow.is_active,
      steps: workflow.steps?.map(s => ({
        name: s.name,
        approver_role_id: s.approver_role_id,
        required_approvals: s.required_approvals
      })) || []
    })
    setModalOpen(true)
  }

  const columns = [
    {
      title: 'Workflow',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, r: Workflow) => (
        <Space direction="vertical" size={0}>
          <Space><BranchesOutlined /><span className="font-medium">{name}</span></Space>
          {r.description && <Text type="secondary" className="text-xs">{r.description}</Text>}
        </Space>
      )
    },
    {
      title: 'Type',
      dataIndex: 'workflow_type',
      key: 'type',
      render: (type: string) => <Tag>{type}</Tag>
    },
    {
      title: 'Steps',
      key: 'steps',
      render: (_: any, r: Workflow) => (
        <Space size={4}>
          {r.steps?.map((s, i) => (
            <Tag key={i} color="blue">{s.name}</Tag>
          ))}
          {(!r.steps || r.steps.length === 0) && <Text type="secondary">No steps</Text>}
        </Space>
      )
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'status',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'default'}>{active ? 'Active' : 'Inactive'}</Tag>
      )
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_: any, r: Workflow) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => openEdit(r)} />
          <Popconfirm title="Delete this workflow?" onConfirm={() => deleteMutation.mutate(r.id)}>
            <Button icon={<DeleteOutlined />} size="small" danger />
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <div className="p-6">
      <Card
        title="Approval Workflows"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => {
            setEditingWorkflow(null)
            form.resetFields()
            setModalOpen(true)
          }}>
            Create Workflow
          </Button>
        }
      >
        <Table
          dataSource={workflows}
          columns={columns}
          rowKey="id"
          loading={isLoading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={editingWorkflow ? 'Edit Workflow' : 'Create Workflow'}
        open={modalOpen}
        onCancel={closeModal}
        onOk={() => form.submit()}
        width={650}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item name="name" label="Workflow Name" rules={[{ required: true, message: 'Name is required' }]}>
            <Input placeholder="e.g., Document Approval" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} placeholder="Describe the workflow purpose" />
          </Form.Item>
          <div className="flex gap-4">
            <Form.Item name="workflow_type" label="Type" initialValue="SEQUENTIAL" className="flex-1">
              <Select>
                <Select.Option value="SEQUENTIAL">Sequential (one after another)</Select.Option>
                <Select.Option value="PARALLEL">Parallel (all at once)</Select.Option>
                <Select.Option value="ANY">Any (first approval wins)</Select.Option>
              </Select>
            </Form.Item>
            <Form.Item name="is_active" label="Active" valuePropName="checked" initialValue={true}>
              <Switch />
            </Form.Item>
          </div>

          <Divider orientation="left">Approval Steps</Divider>

          <Form.List name="steps">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...rest }, index) => (
                  <div key={key} className="flex gap-2 mb-3 items-start">
                    <div className="w-6 h-8 flex items-center justify-center text-gray-400 font-medium">
                      {index + 1}.
                    </div>
                    <Form.Item
                      {...rest}
                      name={[name, 'name']}
                      rules={[{ required: true, message: 'Step name required' }]}
                      className="flex-1 mb-0"
                    >
                      <Input placeholder="Step name (e.g., Manager Review)" />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, 'approver_role_id']} className="w-40 mb-0">
                      <Select placeholder="Approver role" allowClear>
                        {roles?.map(r => (
                          <Select.Option key={r.id} value={r.id}>{r.name}</Select.Option>
                        ))}
                      </Select>
                    </Form.Item>
                    <Form.Item {...rest} name={[name, 'required_approvals']} initialValue={1} className="w-20 mb-0">
                      <InputNumber min={1} max={10} />
                    </Form.Item>
                    <Button
                      type="text"
                      danger
                      icon={<MinusCircleOutlined />}
                      onClick={() => remove(name)}
                    />
                  </div>
                ))}
                <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                  Add Approval Step
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </div>
  )
}

export default WorkflowsPage
