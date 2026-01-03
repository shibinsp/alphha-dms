import React, { useState, useEffect } from 'react';
import { Table, Card, Input, Button, Tag, Space, Modal, Form, message, Tabs } from 'antd';
import { SearchOutlined, UserOutlined, FileTextOutlined, SyncOutlined } from '@ant-design/icons';
import { api } from '../../services/api';

interface Customer {
  id: string;
  external_id: string;
  name: string;
  email?: string;
  phone?: string;
  document_count: number;
  last_synced_at?: string;
}

interface Document {
  id: string;
  title: string;
  file_name: string;
  lifecycle_status: string;
  created_at: string;
}

const CustomersPage: React.FC = () => {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);

  useEffect(() => {
    fetchCustomers();
  }, [search]);

  const fetchCustomers = async () => {
    setLoading(true);
    try {
      const params = search ? { search } : {};
      const res = await api.get('/entities/customers', { params });
      setCustomers(res.data);
    } catch (err) {
      message.error('Failed to load customers');
    } finally {
      setLoading(false);
    }
  };

  const fetchCustomerDocs = async (customerId: string) => {
    setDocsLoading(true);
    try {
      const res = await api.get(`/entities/customers/${customerId}/documents`);
      setDocuments(res.data);
    } catch (err) {
      message.error('Failed to load documents');
    } finally {
      setDocsLoading(false);
    }
  };

  const columns = [
    {
      title: 'Customer ID',
      dataIndex: 'external_id',
      key: 'external_id',
      render: (id: string) => <Tag color="blue">{id}</Tag>,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          <UserOutlined />
          {name}
        </Space>
      ),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: 'Phone',
      dataIndex: 'phone',
      key: 'phone',
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
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Customer) => (
        <Button
          type="link"
          onClick={() => {
            setSelectedCustomer(record);
            fetchCustomerDocs(record.id);
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
            <UserOutlined />
            Customer Management
          </Space>
        }
        extra={
          <Input
            placeholder="Search customers..."
            prefix={<SearchOutlined />}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 250 }}
            allowClear
          />
        }
      >
        <Table
          columns={columns}
          dataSource={customers}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={
          <Space>
            <UserOutlined />
            {selectedCustomer?.name} - Documents
          </Space>
        }
        open={!!selectedCustomer}
        onCancel={() => setSelectedCustomer(null)}
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

export default CustomersPage;
