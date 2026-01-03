import React, { useState, useCallback, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Card,
  Input,
  Select,
  Button,
  List,
  Tag,
  Space,
  Typography,
  Empty,
  Spin,
  message,
  Modal,
  Form,
} from 'antd'
import {
  SearchOutlined,
  FileOutlined,
  FilterOutlined,
  StarOutlined,
  StarFilled,
  HistoryOutlined,
  DownloadOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import api from '@/services/api'
import type { Document, SourceType, LifecycleStatus } from '@/types'

const { Title, Text } = Typography
const { Option } = Select

const SearchPage: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()

  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [debouncedQuery, setDebouncedQuery] = useState(query)
  const [searchType, setSearchType] = useState<'keyword' | 'semantic' | 'hybrid'>('hybrid')
  const [filters, setFilters] = useState<{
    source_type?: string
    document_type_id?: string
    lifecycle_status?: string
  }>({})
  const [showFilters, setShowFilters] = useState(false)
  const [saveModalOpen, setSaveModalOpen] = useState(false)
  const [form] = Form.useForm()
  const debounceTimer = useRef<NodeJS.Timeout>()

  // Debounce the search query
  useEffect(() => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current)
    }
    debounceTimer.current = setTimeout(() => {
      setDebouncedQuery(query)
    }, 300)
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current)
      }
    }
  }, [query])

  // Search results - uses debounced query
  const {
    data: searchResults,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['search', debouncedQuery, searchType, filters],
    queryFn: async () => {
      if (!debouncedQuery.trim()) return null
      const params = new URLSearchParams()
      params.set('query', debouncedQuery)
      params.set('search_type', searchType)
      if (filters.source_type) params.set('source_type', filters.source_type)
      if (filters.document_type_id) params.set('document_type_id', filters.document_type_id)
      if (filters.lifecycle_status) params.set('lifecycle_status', filters.lifecycle_status)

      const response = await api.get(`/search?${params.toString()}`)
      return response.data
    },
    enabled: !!debouncedQuery.trim(),
  })

  // Recent searches
  const { data: recentSearches } = useQuery({
    queryKey: ['recent-searches'],
    queryFn: async () => {
      const response = await api.get('/search/recent')
      return response.data.recent as string[]
    },
  })

  // Saved searches
  const { data: savedSearches } = useQuery({
    queryKey: ['saved-searches'],
    queryFn: async () => {
      const response = await api.get('/search/saved')
      return response.data
    },
  })

  // Save search mutation
  const saveSearchMutation = useMutation({
    mutationFn: async (name: string) => {
      await api.post('/search/saved', {
        name,
        query,
        search_type: searchType,
        filters,
      })
    },
    onSuccess: () => {
      message.success('Search saved')
      queryClient.invalidateQueries({ queryKey: ['saved-searches'] })
    },
  })

  const handleSearch = useCallback(() => {
    if (query.trim()) {
      setSearchParams({ q: query })
      refetch()
    }
  }, [query, refetch, setSearchParams])

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const getStatusColor = (status: LifecycleStatus) => {
    const colors: Record<LifecycleStatus, string> = {
      DRAFT: 'default',
      REVIEW: 'processing',
      APPROVED: 'success',
      ARCHIVED: 'warning',
      DELETED: 'error',
    }
    return colors[status]
  }

  const getSourceColor = (source: SourceType) => {
    const colors: Record<SourceType, string> = {
      CUSTOMER: 'blue',
      VENDOR: 'green',
      INTERNAL: 'gold',
    }
    return colors[source]
  }

  return (
    <div className="max-w-4xl mx-auto">
      <Title level={3} className="mb-6">
        Search Documents
      </Title>

      {/* Search Input */}
      <Card className="mb-6">
        <div className="flex gap-4">
          <Input
            size="large"
            placeholder="Search documents..."
            prefix={<SearchOutlined />}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            allowClear
          />
          <Select
            size="large"
            value={searchType}
            onChange={setSearchType}
            style={{ width: 150 }}
          >
            <Option value="hybrid">Hybrid</Option>
            <Option value="keyword">Keyword</Option>
            <Option value="semantic">Semantic</Option>
          </Select>
          <Button
            size="large"
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleSearch}
            loading={isLoading}
          >
            Search
          </Button>
          <Button
            size="large"
            icon={<FilterOutlined />}
            onClick={() => setShowFilters(!showFilters)}
          />
        </div>

        {/* Filters */}
        {showFilters && (
          <div className="mt-4 pt-4 border-t">
            <Space wrap>
              <Select
                placeholder="Source Type"
                style={{ width: 150 }}
                value={filters.source_type}
                onChange={(v) => setFilters({ ...filters, source_type: v })}
                allowClear
              >
                <Option value="CUSTOMER">Customer</Option>
                <Option value="VENDOR">Vendor</Option>
                <Option value="INTERNAL">Internal</Option>
              </Select>
              <Select
                placeholder="Status"
                style={{ width: 150 }}
                value={filters.lifecycle_status}
                onChange={(v) => setFilters({ ...filters, lifecycle_status: v })}
                allowClear
              >
                <Option value="DRAFT">Draft</Option>
                <Option value="REVIEW">Review</Option>
                <Option value="APPROVED">Approved</Option>
                <Option value="ARCHIVED">Archived</Option>
              </Select>
              <Button onClick={() => setFilters({})}>Clear Filters</Button>
            </Space>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-4 gap-6">
        {/* Results */}
        <div className="col-span-3">
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Spin size="large" />
            </div>
          ) : searchResults ? (
            <Card>
              <div className="flex justify-between items-center mb-4">
                <Text type="secondary">
                  {searchResults.total} results found
                </Text>
                <Button
                  icon={<StarOutlined />}
                  onClick={() => setSaveModalOpen(true)}
                >
                  Save Search
                </Button>
              </div>

              {searchResults.items?.length > 0 ? (
                <List
                  dataSource={searchResults.items}
                  renderItem={(doc: Document) => (
                    <List.Item
                      actions={[
                        <Button
                          key="view"
                          type="text"
                          icon={<EyeOutlined />}
                          onClick={() => navigate(`/documents/${doc.id}`)}
                        >
                          View
                        </Button>,
                        <Button
                          key="download"
                          type="text"
                          icon={<DownloadOutlined />}
                        >
                          Download
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        avatar={<FileOutlined style={{ fontSize: 24, color: '#1E3A5F' }} />}
                        title={
                          <a onClick={() => navigate(`/documents/${doc.id}`)}>
                            {doc.title}
                          </a>
                        }
                        description={
                          <div>
                            <Text type="secondary" className="block">
                              {doc.file_name} • {(doc.file_size / 1024).toFixed(1)} KB
                            </Text>
                            <Space className="mt-2">
                              <Tag color={getStatusColor(doc.lifecycle_status)}>
                                {doc.lifecycle_status}
                              </Tag>
                              <Tag color={getSourceColor(doc.source_type)}>
                                {doc.source_type}
                              </Tag>
                              <Text type="secondary" className="text-xs">
                                {dayjs(doc.created_at).format('MMM D, YYYY')}
                              </Text>
                            </Space>
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="No results found" />
              )}
            </Card>
          ) : (
            <Card>
              <Empty description="Enter a search query to find documents" />
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="col-span-1">
          {/* Recent Searches */}
          <Card title="Recent Searches" size="small" className="mb-4">
            {recentSearches && recentSearches.length > 0 ? (
              <div className="space-y-2">
                {recentSearches.slice(0, 5).map((search, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 cursor-pointer hover:text-primary-500"
                    onClick={() => setQuery(search)}
                  >
                    <HistoryOutlined className="text-gray-400" />
                    <Text className="text-sm truncate">{search}</Text>
                  </div>
                ))}
              </div>
            ) : (
              <Text type="secondary" className="text-sm">
                No recent searches
              </Text>
            )}
          </Card>

          {/* Saved Searches */}
          <Card title="Saved Searches" size="small">
            {savedSearches?.length > 0 ? (
              <div className="space-y-2">
                {savedSearches.slice(0, 5).map((saved: any) => (
                  <div
                    key={saved.id}
                    className="flex items-center gap-2 cursor-pointer hover:text-primary-500"
                    onClick={() => setQuery(saved.query)}
                  >
                    <StarFilled className="text-yellow-500" />
                    <Text className="text-sm truncate">{saved.name}</Text>
                  </div>
                ))}
              </div>
            ) : (
              <Text type="secondary" className="text-sm">
                No saved searches
              </Text>
            )}
          </Card>
        </div>
      </div>

      {/* Save Search Modal */}
      <Modal
        title="Save Search"
        open={saveModalOpen}
        onCancel={() => {
          setSaveModalOpen(false)
          form.resetFields()
        }}
        onOk={() => {
          form.validateFields().then((values) => {
            saveSearchMutation.mutate(values.name, {
              onSuccess: () => {
                setSaveModalOpen(false)
                form.resetFields()
              },
            })
          })
        }}
        confirmLoading={saveSearchMutation.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Search Name"
            rules={[{ required: true, message: 'Please enter a name for this search' }]}
          >
            <Input placeholder="e.g., All pending contracts" />
          </Form.Item>
          <Text type="secondary">
            Query: "{query}" | Type: {searchType}
          </Text>
        </Form>
      </Modal>
    </div>
  )
}

export default SearchPage
