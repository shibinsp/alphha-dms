import React, { useState, useEffect } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, Space, Tag, Popconfirm, message, Tabs, ColorPicker } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import api from '../../services/api';

interface ConfigOption {
  id: string;
  category: string;
  value: string;
  label: string;
  description?: string;
  color?: string;
  sort_order: number;
  is_active: boolean;
  is_system: boolean;
}

const CATEGORIES = [
  { key: 'source_type', label: 'Source Types', description: 'Customer, Vendor, Internal, etc.' },
  { key: 'classification', label: 'Classifications', description: 'Security classification levels' },
  { key: 'folder', label: 'Folders', description: 'Document folder categories' },
];

const SettingsPage: React.FC = () => {
  const [options, setOptions] = useState<ConfigOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingOption, setEditingOption] = useState<ConfigOption | null>(null);
  const [activeTab, setActiveTab] = useState('source_type');
  const [form] = Form.useForm();

  const fetchOptions = async () => {
    setLoading(true);
    try {
      const res = await api.get('/config/options', { params: { include_inactive: true } });
      setOptions(res.data);
    } catch {
      message.error('Failed to load options');
    }
    setLoading(false);
  };

  useEffect(() => { fetchOptions(); }, []);

  const seedDefaults = async () => {
    try {
      await api.post('/config/options/seed-defaults');
      message.success('Default options created');
      fetchOptions();
    } catch {
      message.error('Failed to seed defaults');
    }
  };

  const handleSave = async (values: any) => {
    try {
      const color = typeof values.color === 'string' ? values.color : values.color?.toHexString?.() || values.color;
      const payload = { ...values, color, category: activeTab };
      
      if (editingOption) {
        await api.put(`/config/options/${editingOption.id}`, payload);
        message.success('Option updated');
      } else {
        await api.post('/config/options', payload);
        message.success('Option created');
      }
      setModalOpen(false);
      form.resetFields();
      setEditingOption(null);
      fetchOptions();
    } catch {
      message.error('Failed to save option');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.delete(`/config/options/${id}`);
      message.success('Option deleted');
      fetchOptions();
    } catch {
      message.error('Failed to delete option');
    }
  };

  const openEdit = (option: ConfigOption) => {
    setEditingOption(option);
    form.setFieldsValue(option);
    setModalOpen(true);
  };

  const openCreate = () => {
    setEditingOption(null);
    form.resetFields();
    setModalOpen(true);
  };

  const filteredOptions = options.filter(o => o.category === activeTab);

  const columns = [
    { title: 'Value', dataIndex: 'value', key: 'value' },
    { title: 'Label', dataIndex: 'label', key: 'label' },
    {
      title: 'Color',
      dataIndex: 'color',
      key: 'color',
      render: (color: string) => color ? <Tag color={color}>{color}</Tag> : '-'
    },
    { title: 'Order', dataIndex: 'sort_order', key: 'sort_order', width: 80 },
    {
      title: 'Status',
      key: 'status',
      render: (_: any, r: ConfigOption) => (
        <Space>
          {r.is_system && <Tag color="blue">System</Tag>}
          {!r.is_active && <Tag color="red">Inactive</Tag>}
        </Space>
      )
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, r: ConfigOption) => (
        <Space>
          <Button icon={<EditOutlined />} size="small" onClick={() => openEdit(r)} />
          {!r.is_system && (
            <Popconfirm title="Delete this option?" onConfirm={() => handleDelete(r.id)}>
              <Button icon={<DeleteOutlined />} size="small" danger />
            </Popconfirm>
          )}
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="System Settings"
        extra={
          <Space>
            <Button onClick={seedDefaults}>Seed Defaults</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              Add Option
            </Button>
          </Space>
        }
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={CATEGORIES.map(c => ({
            key: c.key,
            label: c.label,
            children: (
              <Table
                dataSource={filteredOptions}
                columns={columns}
                rowKey="id"
                loading={loading}
                size="small"
                pagination={false}
              />
            )
          }))}
        />
      </Card>

      <Modal
        title={editingOption ? 'Edit Option' : 'Add Option'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); setEditingOption(null); }}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleSave}>
          <Form.Item name="value" label="Value" rules={[{ required: true }]}>
            <Input placeholder="UPPERCASE_VALUE" disabled={editingOption?.is_system} />
          </Form.Item>
          <Form.Item name="label" label="Display Label" rules={[{ required: true }]}>
            <Input placeholder="Human readable label" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="color" label="Color">
            <ColorPicker format="hex" />
          </Form.Item>
          <Form.Item name="sort_order" label="Sort Order" initialValue={0}>
            <Input type="number" />
          </Form.Item>
          <Form.Item name="is_active" label="Active" initialValue={true}>
            <Select options={[{ value: true, label: 'Yes' }, { value: false, label: 'No' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SettingsPage;
