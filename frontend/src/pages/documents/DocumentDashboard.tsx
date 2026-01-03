import React, { useState, useEffect } from 'react';
import {
  Table, Card, Button, Tag, Space, Dropdown, Checkbox, Input, Select,
  DatePicker, message, Tooltip, Badge
} from 'antd';
import {
  SettingOutlined, SearchOutlined, FilterOutlined, DownloadOutlined,
  EyeOutlined, FileTextOutlined, UserOutlined, ShopOutlined, BankOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';
import { api } from '../../services/api';

interface Document {
  id: string;
  title: string;
  file_name: string;
  file_size: number;
  source_type: string;
  customer_id?: string;
  vendor_id?: string;
  department_id?: string;
  classification: string;
  lifecycle_status: string;
  document_type?: { name: string };
  created_at: string;
  updated_at: string;
  custom_metadata: Record<string, any>;
}

interface CustomField {
  id: string;
  name: string;
  field_key: string;
  field_type: string;
}

const DEFAULT_COLUMNS = [
  'title',
  'file_name',
  'source_type',
  'lifecycle_status',
  'classification',
  'created_at',
];

const DocumentDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [customFields, setCustomFields] = useState<CustomField[]>([]);
  const [visibleColumns, setVisibleColumns] = useState<string[]>(DEFAULT_COLUMNS);
  const [filters, setFilters] = useState<Record<string, any>>({});
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });

  useEffect(() => {
    fetchDocuments();
    fetchCustomFields();
    // Load saved column preferences
    const saved = localStorage.getItem('doc_dashboard_columns');
    if (saved) setVisibleColumns(JSON.parse(saved));
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [filters, pagination.current, pagination.pageSize]);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const params = {
        skip: (pagination.current - 1) * pagination.pageSize,
        limit: pagination.pageSize,
        ...filters,
      };
      const res = await api.get('/documents', { params });
      setDocuments(res.data.items || res.data);
      setPagination((p) => ({ ...p, total: res.data.total || res.data.length }));
    } catch (err) {
      message.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  const fetchCustomFields = async () => {
    try {
      const res = await api.get('/entities/custom-fields');
      setCustomFields(res.data);
    } catch (err) {
      console.error('Failed to load custom fields');
    }
  };

  const handleColumnChange = (cols: string[]) => {
    setVisibleColumns(cols);
    localStorage.setItem('doc_dashboard_columns', JSON.stringify(cols));
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const statusColors: Record<string, string> = {
    DRAFT: 'default',
    REVIEW: 'processing',
    APPROVED: 'success',
    ARCHIVED: 'warning',
    DELETED: 'error',
  };

  const sourceIcons: Record<string, React.ReactNode> = {
    CUSTOMER: <UserOutlined />,
    VENDOR: <ShopOutlined />,
    INTERNAL: <BankOutlined />,
  };

  // Define all available columns
  const allColumns: Record<string, any> = {
    title: {
      title: 'Title',
      dataIndex: 'title',
      key: 'title',
      fixed: 'left',
      width: 200,
      render: (title: string, record: Document) => (
        <Space>
          <FileTextOutlined />
          <a onClick={() => navigate(`/documents/${record.id}`)}>{title}</a>
        </Space>
      ),
    },
    file_name: {
      title: 'File Name',
      dataIndex: 'file_name',
      key: 'file_name',
      ellipsis: true,
    },
    file_size: {
      title: 'Size',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => formatFileSize(size),
    },
    source_type: {
      title: 'Source',
      dataIndex: 'source_type',
      key: 'source_type',
      render: (type: string) => (
        <Tag icon={sourceIcons[type]}>{type}</Tag>
      ),
    },
    customer_id: {
      title: 'Customer ID',
      dataIndex: 'customer_id',
      key: 'customer_id',
      render: (id?: string) => id ? <Tag color="blue">{id}</Tag> : '-',
    },
    vendor_id: {
      title: 'Vendor ID',
      dataIndex: 'vendor_id',
      key: 'vendor_id',
      render: (id?: string) => id ? <Tag color="purple">{id}</Tag> : '-',
    },
    department_id: {
      title: 'Department',
      dataIndex: 'department_id',
      key: 'department_id',
      render: (id?: string) => id ? <Tag color="cyan">{id}</Tag> : '-',
    },
    lifecycle_status: {
      title: 'Status',
      dataIndex: 'lifecycle_status',
      key: 'lifecycle_status',
      render: (status: string) => (
        <Tag color={statusColors[status]}>{status}</Tag>
      ),
    },
    classification: {
      title: 'Classification',
      dataIndex: 'classification',
      key: 'classification',
      render: (c: string) => <Tag>{c}</Tag>,
    },
    document_type: {
      title: 'Document Type',
      dataIndex: ['document_type', 'name'],
      key: 'document_type',
    },
    created_at: {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    updated_at: {
      title: 'Updated',
      dataIndex: 'updated_at',
      key: 'updated_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
  };

  // Add custom field columns
  customFields.forEach((field) => {
    allColumns[`custom_${field.field_key}`] = {
      title: field.name,
      key: `custom_${field.field_key}`,
      render: (_: any, record: Document) => {
        const value = record.custom_metadata?.[field.field_key];
        return value !== undefined ? String(value) : '-';
      },
    };
  });

  // Actions column
  const actionsColumn = {
    title: 'Actions',
    key: 'actions',
    fixed: 'right' as const,
    width: 100,
    render: (_: any, record: Document) => (
      <Space>
        <Tooltip title="View">
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/documents/${record.id}`)}
          />
        </Tooltip>
        <Tooltip title="Download">
          <Button type="link" icon={<DownloadOutlined />} />
        </Tooltip>
      </Space>
    ),
  };

  // Build visible columns
  const columns: ColumnsType<Document> = [
    ...visibleColumns.map((key) => allColumns[key]).filter(Boolean),
    actionsColumn,
  ];

  // Column selector options
  const columnOptions = [
    { label: 'Title', value: 'title' },
    { label: 'File Name', value: 'file_name' },
    { label: 'File Size', value: 'file_size' },
    { label: 'Source Type', value: 'source_type' },
    { label: 'Customer ID', value: 'customer_id' },
    { label: 'Vendor ID', value: 'vendor_id' },
    { label: 'Department', value: 'department_id' },
    { label: 'Status', value: 'lifecycle_status' },
    { label: 'Classification', value: 'classification' },
    { label: 'Document Type', value: 'document_type' },
    { label: 'Created', value: 'created_at' },
    { label: 'Updated', value: 'updated_at' },
    ...customFields.map((f) => ({ label: f.name, value: `custom_${f.field_key}` })),
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="Document Dashboard"
        extra={
          <Space>
            <Input
              placeholder="Search..."
              prefix={<SearchOutlined />}
              style={{ width: 200 }}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              allowClear
            />
            <Select
              placeholder="Status"
              style={{ width: 120 }}
              allowClear
              onChange={(v) => setFilters({ ...filters, status: v })}
            >
              <Select.Option value="DRAFT">Draft</Select.Option>
              <Select.Option value="REVIEW">Review</Select.Option>
              <Select.Option value="APPROVED">Approved</Select.Option>
              <Select.Option value="ARCHIVED">Archived</Select.Option>
            </Select>
            <Select
              placeholder="Source"
              style={{ width: 120 }}
              allowClear
              onChange={(v) => setFilters({ ...filters, source_type: v })}
            >
              <Select.Option value="CUSTOMER">Customer</Select.Option>
              <Select.Option value="VENDOR">Vendor</Select.Option>
              <Select.Option value="INTERNAL">Internal</Select.Option>
            </Select>
            <Dropdown
              trigger={['click']}
              dropdownRender={() => (
                <Card size="small" style={{ width: 250 }}>
                  <p style={{ fontWeight: 'bold', marginBottom: 8 }}>Visible Columns</p>
                  <Checkbox.Group
                    options={columnOptions}
                    value={visibleColumns}
                    onChange={(v) => handleColumnChange(v as string[])}
                    style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
                  />
                  <Button
                    type="link"
                    size="small"
                    onClick={() => handleColumnChange(DEFAULT_COLUMNS)}
                    style={{ marginTop: 8 }}
                  >
                    Reset to Default
                  </Button>
                </Card>
              )}
            >
              <Button icon={<SettingOutlined />}>Columns</Button>
            </Dropdown>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={documents}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} documents`,
            onChange: (page, pageSize) => setPagination({ ...pagination, current: page, pageSize }),
          }}
        />
      </Card>
    </div>
  );
};

export default DocumentDashboard;
