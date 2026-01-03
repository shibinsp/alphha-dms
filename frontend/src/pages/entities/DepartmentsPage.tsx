import React, { useState, useEffect } from 'react';
import { Table, Card, Button, Tag, Space, Modal, Form, Input, message } from 'antd';
import { PlusOutlined, BankOutlined, FileTextOutlined } from '@ant-design/icons';
import { api } from '../../services/api';

interface Department {
  id: string;
  name: string;
  code: string;
  document_count: number;
  created_at: string;
}

interface Document {
  id: string;
  title: string;
  file_name: string;
  lifecycle_status: string;
  created_at: string;
}

const DepartmentsPage: React.FC = () => {
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedDept, setSelectedDept] = useState<Department | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchDepartments();
  }, []);

  const fetchDepartments = async () => {
    setLoading(true);
    try {
      const res = await api.get('/entities/departments');
      setDepartments(res.data);
    } catch (err) {
      message.error('Failed to load departments');
    } finally {
      setLoading(false);
    }
  };

  const fetchDeptDocs = async (deptId: string) => {
    setDocsLoading(true);
    try {
      const res = await api.get(`/entities/departments/${deptId}/documents`);
      setDocuments(res.data);
    } catch (err) {
      message.error('Failed to load documents');
    } finally {
      setDocsLoading(false);
    }
  };

  const handleCreate = async (values: { name: string; code: string }) => {
    try {
      await api.post('/entities/departments', values);
      message.success('Department created');
      setModalOpen(false);
      form.resetFields();
      fetchDepartments();
    } catch (err) {
      message.error('Failed to create department');
    }
  };

  const columns = [
    {
      title: 'Code',
      dataIndex: 'code',
      key: 'code',
      render: (code: string) => <Tag color="cyan">{code}</Tag>,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          <BankOutlined />
          {name}
        </Space>
      ),
    },
    {
      title: 'Documents',
      dataIndex: 'document_count',
      key: 'document_count',
      render: (count: number) => (
        <Tag color={count > 0 ? 'green' : 'default'}>
          <FileTextOutlined /> {count}
        </Tag>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Department) => (
        <Button
          type="link"
          onClick={() => {
            setSelectedDept(record);
            fetchDeptDocs(record.id);
          }}
        >
          View Documents
        </Button>
      ),
    },
  ];

  const docColumns = [
    { title: 'Title', dataIndex: 'title', key: 'title' },
    { title: 'File', dataIndex: 'file_name', key: 'file_name' },
    {
      title: 'Status',
      dataIndex: 'lifecycle_status',
      key: 'lifecycle_status',
      render: (status: string) => {
        const colors: Record<string, string> = {
          DRAFT: 'default',
          REVIEW: 'processing',
          APPROVED: 'success',
          ARCHIVED: 'warning',
        };
        return <Tag color={colors[status] || 'default'}>{status}</Tag>;
      },
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <BankOutlined />
            Department Management
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            Add Department
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={departments}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Create Modal */}
      <Modal
        title="Create Department"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="Department Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., Human Resources" />
          </Form.Item>
          <Form.Item name="code" label="Department Code" rules={[{ required: true }]}>
            <Input placeholder="e.g., HR" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Documents Modal */}
      <Modal
        title={
          <Space>
            <BankOutlined />
            {selectedDept?.name} - Documents
          </Space>
        }
        open={!!selectedDept}
        onCancel={() => setSelectedDept(null)}
        width={800}
        footer={null}
      >
        <Table
          columns={docColumns}
          dataSource={documents}
          rowKey="id"
          loading={docsLoading}
          pagination={{ pageSize: 5 }}
          size="small"
        />
      </Modal>
    </div>
  );
};

export default DepartmentsPage;
