import React, { useState, useEffect } from 'react';
import { Table, Card, Input, Button, Tag, Space, Modal, message } from 'antd';
import { SearchOutlined, ShopOutlined, FileTextOutlined } from '@ant-design/icons';
import { api } from '../../services/api';

interface Vendor {
  id: string;
  external_id: string;
  name: string;
  email?: string;
  phone?: string;
  tax_id?: string;
  document_count: number;
}

interface Document {
  id: string;
  title: string;
  file_name: string;
  lifecycle_status: string;
  created_at: string;
}

const VendorsPage: React.FC = () => {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedVendor, setSelectedVendor] = useState<Vendor | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);

  useEffect(() => {
    fetchVendors();
  }, [search]);

  const fetchVendors = async () => {
    setLoading(true);
    try {
      const params = search ? { search } : {};
      const res = await api.get('/entities/vendors', { params });
      setVendors(res.data);
    } catch (err) {
      message.error('Failed to load vendors');
    } finally {
      setLoading(false);
    }
  };

  const fetchVendorDocs = async (vendorId: string) => {
    setDocsLoading(true);
    try {
      const res = await api.get(`/entities/vendors/${vendorId}/documents`);
      setDocuments(res.data);
    } catch (err) {
      message.error('Failed to load documents');
    } finally {
      setDocsLoading(false);
    }
  };

  const columns = [
    {
      title: 'Vendor ID',
      dataIndex: 'external_id',
      key: 'external_id',
      render: (id: string) => <Tag color="purple">{id}</Tag>,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          <ShopOutlined />
          {name}
        </Space>
      ),
    },
    {
      title: 'Tax ID',
      dataIndex: 'tax_id',
      key: 'tax_id',
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
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
      render: (_: any, record: Vendor) => (
        <Button
          type="link"
          onClick={() => {
            setSelectedVendor(record);
            fetchVendorDocs(record.id);
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
            <ShopOutlined />
            Vendor Management
          </Space>
        }
        extra={
          <Input
            placeholder="Search vendors..."
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
          dataSource={vendors}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal
        title={
          <Space>
            <ShopOutlined />
            {selectedVendor?.name} - Documents
          </Space>
        }
        open={!!selectedVendor}
        onCancel={() => setSelectedVendor(null)}
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

export default VendorsPage;
