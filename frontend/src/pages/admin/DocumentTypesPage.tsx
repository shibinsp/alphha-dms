import React, { useState, useEffect } from 'react';
import {
  Table, Card, Button, Tag, Space, Modal, Form, Input, Select,
  InputNumber, message, Popconfirm, Divider, List, Switch
} from 'antd';
import {
  PlusOutlined, EditOutlined, FolderOutlined,
  CheckCircleOutlined, FieldTimeOutlined
} from '@ant-design/icons';
import { api } from '../../services/api';

interface CustomField {
  id: string;
  name: string;
  field_key: string;
  field_type: string;
  options?: string[];
  required: boolean;
}

interface DocumentType {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  retention_days?: number;
  approval_flow_type: string;
  auto_approvers?: string[];
  custom_fields: CustomField[];
}

const DocumentTypesPage: React.FC = () => {
  const [types, setTypes] = useState<DocumentType[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [fieldModalOpen, setFieldModalOpen] = useState(false);
  const [editingType, setEditingType] = useState<DocumentType | null>(null);
  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null);
  const [form] = Form.useForm();
  const [fieldForm] = Form.useForm();

  useEffect(() => {
    fetchTypes();
  }, []);

  const fetchTypes = async () => {
    setLoading(true);
    try {
      const res = await api.get('/entities/document-types');
      setTypes(res.data);
    } catch (err) {
      message.error('Failed to load document types');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (values: any) => {
    try {
      if (editingType) {
        await api.put(`/entities/document-types/${editingType.id}`, values);
        message.success('Document type updated');
      } else {
        await api.post('/entities/document-types', values);
        message.success('Document type created');
      }
      setModalOpen(false);
      form.resetFields();
      setEditingType(null);
      fetchTypes();
    } catch (err) {
      message.error('Failed to save document type');
    }
  };

  const handleAddField = async (values: any) => {
    try {
      await api.post('/entities/custom-fields', {
        ...values,
        document_type_id: selectedTypeId,
      });
      message.success('Custom field added');
      setFieldModalOpen(false);
      fieldForm.resetFields();
      fetchTypes();
    } catch (err) {
      message.error('Failed to add custom field');
    }
  };

  const handleDeleteField = async (fieldId: string) => {
    try {
      await api.delete(`/entities/custom-fields/${fieldId}`);
      message.success('Custom field deleted');
      fetchTypes();
    } catch (err) {
      message.error('Failed to delete custom field');
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, _record: DocumentType) => (
        <Space>
          <FolderOutlined />
          {name}
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
      title: 'Retention',
      dataIndex: 'retention_days',
      key: 'retention_days',
      render: (days?: number) =>
        days ? (
          <Tag icon={<FieldTimeOutlined />} color="blue">
            {days} days
          </Tag>
        ) : (
          <Tag>No limit</Tag>
        ),
    },
    {
      title: 'Approval Flow',
      dataIndex: 'approval_flow_type',
      key: 'approval_flow_type',
      render: (type: string) => {
        const colors: Record<string, string> = {
          AUTO: 'green',
          MANUAL: 'orange',
          NONE: 'default',
        };
        return (
          <Tag icon={<CheckCircleOutlined />} color={colors[type]}>
            {type}
          </Tag>
        );
      },
    },
    {
      title: 'Custom Fields',
      key: 'custom_fields',
      render: (_: any, record: DocumentType) => (
        <Tag color="purple">{record.custom_fields?.length || 0} fields</Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: DocumentType) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingType(record);
              form.setFieldsValue(record);
              setModalOpen(true);
            }}
          />
          <Button
            type="link"
            onClick={() => {
              setSelectedTypeId(record.id);
              setFieldModalOpen(true);
            }}
          >
            + Field
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <FolderOutlined />
            Document Types & Folders
          </Space>
        }
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingType(null);
              form.resetFields();
              setModalOpen(true);
            }}
          >
            Add Document Type
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={types}
          rowKey="id"
          loading={loading}
          expandable={{
            expandedRowRender: (record) => (
              <div style={{ padding: '0 48px' }}>
                <h4>Custom Fields</h4>
                {record.custom_fields?.length > 0 ? (
                  <List
                    size="small"
                    dataSource={record.custom_fields}
                    renderItem={(field) => (
                      <List.Item
                        actions={[
                          <Popconfirm
                            title="Delete this field?"
                            onConfirm={() => handleDeleteField(field.id)}
                          >
                            <Button type="link" danger size="small">
                              Delete
                            </Button>
                          </Popconfirm>,
                        ]}
                      >
                        <Space>
                          <Tag color="blue">{field.field_type}</Tag>
                          <strong>{field.name}</strong>
                          <span style={{ color: '#888' }}>({field.field_key})</span>
                          {field.required && <Tag color="red">Required</Tag>}
                        </Space>
                      </List.Item>
                    )}
                  />
                ) : (
                  <p style={{ color: '#888' }}>No custom fields defined</p>
                )}
              </div>
            ),
          }}
        />
      </Card>

      {/* Document Type Modal */}
      <Modal
        title={editingType ? 'Edit Document Type' : 'Create Document Type'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., Invoice, Contract, KYC" />
          </Form.Item>

          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item name="icon" label="Icon">
            <Input placeholder="e.g., file-text, folder, bank" />
          </Form.Item>

          <Form.Item name="retention_days" label="Retention Period (days)">
            <InputNumber min={0} style={{ width: '100%' }} placeholder="Leave empty for no limit" />
          </Form.Item>

          <Divider>Approval Flow</Divider>

          <Form.Item name="approval_flow_type" label="Approval Type" initialValue="NONE">
            <Select>
              <Select.Option value="NONE">No Approval Required</Select.Option>
              <Select.Option value="AUTO">Auto Approval (Predefined Approvers)</Select.Option>
              <Select.Option value="MANUAL">Manual Approval (User Selects)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.approval_flow_type !== curr.approval_flow_type}
          >
            {({ getFieldValue }) =>
              getFieldValue('approval_flow_type') === 'AUTO' && (
                <Form.Item name="auto_approvers" label="Auto Approvers (User IDs or Roles)">
                  <Select mode="tags" placeholder="Enter user IDs or role names" />
                </Form.Item>
              )
            }
          </Form.Item>
        </Form>
      </Modal>

      {/* Custom Field Modal */}
      <Modal
        title="Add Custom Field"
        open={fieldModalOpen}
        onCancel={() => setFieldModalOpen(false)}
        onOk={() => fieldForm.submit()}
      >
        <Form form={fieldForm} layout="vertical" onFinish={handleAddField}>
          <Form.Item name="name" label="Field Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., Invoice Number" />
          </Form.Item>

          <Form.Item name="field_key" label="Field Key" rules={[{ required: true }]}>
            <Input placeholder="e.g., invoice_number (no spaces)" />
          </Form.Item>

          <Form.Item name="field_type" label="Field Type" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="TEXT">Text</Select.Option>
              <Select.Option value="NUMBER">Number</Select.Option>
              <Select.Option value="DATE">Date</Select.Option>
              <Select.Option value="SELECT">Single Select</Select.Option>
              <Select.Option value="MULTI_SELECT">Multi Select</Select.Option>
              <Select.Option value="BOOLEAN">Yes/No</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.field_type !== curr.field_type}
          >
            {({ getFieldValue }) =>
              ['SELECT', 'MULTI_SELECT'].includes(getFieldValue('field_type')) && (
                <Form.Item name="options" label="Options">
                  <Select mode="tags" placeholder="Enter options" />
                </Form.Item>
              )
            }
          </Form.Item>

          <Form.Item name="required" label="Required" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item name="default_value" label="Default Value">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DocumentTypesPage;
