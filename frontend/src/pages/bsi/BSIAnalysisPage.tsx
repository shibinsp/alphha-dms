import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Card,
  Row,
  Col,
  Table,
  Tag,
  Typography,
  Button,
  Spin,
  Space,
  Upload,
  Statistic,
  Progress,
  Select,
  Tabs,
  Empty,
  message,
} from 'antd'
import {
  UploadOutlined,
  BankOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons'
import { api } from '@/services/api'

const { Title, Text } = Typography
const { Option } = Select

interface BankStatement {
  id: string
  bank_name: string
  account_number: string
  account_holder: string
  period_start: string
  period_end: string
  opening_balance: number
  closing_balance: number
  total_credits: number
  total_debits: number
  transaction_count: number
  status: string
  parsing_confidence: number
  is_verified: boolean
  created_at: string
}

interface BankTransaction {
  id: string
  transaction_date: string
  description: string
  transaction_type: string
  amount: number
  balance: number
  category: string
  is_recurring: boolean
  is_suspicious: boolean
}

interface CategorySummary {
  category: string
  total_amount: number
  transaction_count: number
  percentage: number
}

const BSIAnalysisPage: React.FC = () => {
  const [selectedStatement, setSelectedStatement] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState('statements')
  const queryClient = useQueryClient()

  const { data: statements, isLoading: loadingStatements } = useQuery<BankStatement[]>({
    queryKey: ['bsi', 'statements'],
    queryFn: async () => {
      const response = await api.get('/bsi/statements')
      return response.data
    },
  })

  const { data: transactions, isLoading: loadingTransactions } = useQuery<BankTransaction[]>({
    queryKey: ['bsi', 'transactions', selectedStatement],
    queryFn: async () => {
      if (!selectedStatement) return []
      const response = await api.get(`/bsi/statements/${selectedStatement}/transactions`)
      return response.data
    },
    enabled: !!selectedStatement,
  })

  const { data: analysis, isLoading: loadingAnalysis } = useQuery({
    queryKey: ['bsi', 'analysis', selectedStatement],
    queryFn: async () => {
      if (!selectedStatement) return null
      const response = await api.get(`/bsi/statements/${selectedStatement}/analysis`)
      return response.data
    },
    enabled: !!selectedStatement,
  })

  const verifyMutation = useMutation({
    mutationFn: (statementId: string) => api.post(`/bsi/statements/${statementId}/verify`),
    onSuccess: () => {
      message.success('Statement verified')
      queryClient.invalidateQueries({ queryKey: ['bsi', 'statements'] })
    },
  })

  const categorizeMutation = useMutation({
    mutationFn: ({ transactionId, category }: { transactionId: string; category: string }) =>
      api.post(`/bsi/transactions/${transactionId}/categorize?category=${category}`),
    onSuccess: () => {
      message.success('Transaction categorized')
      queryClient.invalidateQueries({ queryKey: ['bsi', 'transactions'] })
    },
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'verified': return 'success'
      case 'parsed': return 'processing'
      case 'pending': return 'warning'
      case 'failed': return 'error'
      default: return 'default'
    }
  }

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      salary: 'green',
      rent: 'blue',
      utilities: 'cyan',
      groceries: 'orange',
      transportation: 'purple',
      entertainment: 'magenta',
      loan_payment: 'red',
      investment: 'gold',
      transfer: 'geekblue',
      other: 'default',
    }
    return colors[category] || 'default'
  }

  const statementColumns = [
    {
      title: 'Bank',
      dataIndex: 'bank_name',
      key: 'bank_name',
    },
    {
      title: 'Account',
      dataIndex: 'account_number',
      key: 'account_number',
    },
    {
      title: 'Period',
      key: 'period',
      render: (_: any, record: BankStatement) => (
        <span>
          {new Date(record.period_start).toLocaleDateString()} -{' '}
          {new Date(record.period_end).toLocaleDateString()}
        </span>
      ),
    },
    {
      title: 'Transactions',
      dataIndex: 'transaction_count',
      key: 'transaction_count',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{status.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Confidence',
      dataIndex: 'parsing_confidence',
      key: 'parsing_confidence',
      render: (confidence: number) => (
        <Progress
          percent={confidence}
          size="small"
          strokeColor={confidence >= 80 ? '#52c41a' : '#faad14'}
        />
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: BankStatement) => (
        <Space>
          <Button
            type="link"
            onClick={() => {
              setSelectedStatement(record.id)
              setActiveTab('transactions')
            }}
          >
            View
          </Button>
          {!record.is_verified && (
            <Button
              type="link"
              onClick={() => verifyMutation.mutate(record.id)}
              loading={verifyMutation.isPending}
            >
              Verify
            </Button>
          )}
        </Space>
      ),
    },
  ]

  const transactionColumns = [
    {
      title: 'Date',
      dataIndex: 'transaction_date',
      key: 'transaction_date',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Type',
      dataIndex: 'transaction_type',
      key: 'transaction_type',
      render: (type: string) => (
        <Tag color={type === 'credit' ? 'green' : 'red'}>
          {type === 'credit' ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {type}
        </Tag>
      ),
    },
    {
      title: 'Amount',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number, record: BankTransaction) => (
        <Text
          type={record.transaction_type === 'credit' ? 'success' : 'danger'}
          strong
        >
          {record.transaction_type === 'credit' ? '+' : '-'} {amount.toLocaleString()}
        </Text>
      ),
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (category: string, record: BankTransaction) => (
        <Select
          value={category}
          size="small"
          style={{ width: 130 }}
          onChange={(value) => categorizeMutation.mutate({
            transactionId: record.id,
            category: value,
          })}
        >
          <Option value="salary">Salary</Option>
          <Option value="rent">Rent</Option>
          <Option value="utilities">Utilities</Option>
          <Option value="groceries">Groceries</Option>
          <Option value="transportation">Transportation</Option>
          <Option value="entertainment">Entertainment</Option>
          <Option value="loan_payment">Loan Payment</Option>
          <Option value="investment">Investment</Option>
          <Option value="transfer">Transfer</Option>
          <Option value="other">Other</Option>
        </Select>
      ),
    },
    {
      title: 'Flags',
      key: 'flags',
      render: (_: any, record: BankTransaction) => (
        <Space>
          {record.is_recurring && <Tag color="blue">Recurring</Tag>}
          {record.is_suspicious && <Tag color="red">Suspicious</Tag>}
        </Space>
      ),
    },
  ]

  const selectedStatementData = statements?.find(s => s.id === selectedStatement)

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <Title level={2}>
          <BankOutlined className="mr-2" />
          Bank Statement Intelligence
        </Title>
        <Upload
          action="/api/v1/documents/upload"
          showUploadList={false}
          onChange={(info) => {
            if (info.file.status === 'done') {
              message.success('Statement uploaded for processing')
              queryClient.invalidateQueries({ queryKey: ['bsi', 'statements'] })
            }
          }}
        >
          <Button type="primary" icon={<UploadOutlined />}>
            Upload Statement
          </Button>
        </Upload>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <Tabs.TabPane tab="Statements" key="statements">
          {loadingStatements ? (
            <Spin />
          ) : statements?.length ? (
            <Table
              dataSource={statements}
              columns={statementColumns}
              rowKey="id"
              pagination={{ pageSize: 10 }}
            />
          ) : (
            <Empty description="No bank statements uploaded yet" />
          )}
        </Tabs.TabPane>

        <Tabs.TabPane tab="Transactions" key="transactions" disabled={!selectedStatement}>
          {selectedStatementData && (
            <div className="mb-4">
              <Row gutter={[16, 16]}>
                <Col xs={24} sm={8}>
                  <Card size="small">
                    <Statistic
                      title="Opening Balance"
                      value={selectedStatementData.opening_balance}
                      prefix="$"
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={8}>
                  <Card size="small">
                    <Statistic
                      title="Closing Balance"
                      value={selectedStatementData.closing_balance}
                      prefix="$"
                    />
                  </Card>
                </Col>
                <Col xs={24} sm={8}>
                  <Card size="small">
                    <Statistic
                      title="Net Change"
                      value={selectedStatementData.closing_balance - selectedStatementData.opening_balance}
                      prefix="$"
                      valueStyle={{
                        color:
                          selectedStatementData.closing_balance >= selectedStatementData.opening_balance
                            ? '#52c41a'
                            : '#ff4d4f',
                      }}
                    />
                  </Card>
                </Col>
              </Row>
            </div>
          )}

          {loadingTransactions ? (
            <Spin />
          ) : transactions?.length ? (
            <Table
              dataSource={transactions}
              columns={transactionColumns}
              rowKey="id"
              pagination={{ pageSize: 20 }}
            />
          ) : (
            <Empty description="Select a statement to view transactions" />
          )}
        </Tabs.TabPane>

        <Tabs.TabPane tab="Analysis" key="analysis" disabled={!selectedStatement}>
          {loadingAnalysis ? (
            <Spin />
          ) : analysis ? (
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={12}>
                <Card title="Cash Flow Analysis">
                  <Space direction="vertical" className="w-full">
                    <div className="flex justify-between">
                      <Text>Total Inflow</Text>
                      <Text type="success" strong>
                        +{analysis.cash_flow?.total_inflow?.toLocaleString() || 0}
                      </Text>
                    </div>
                    <div className="flex justify-between">
                      <Text>Total Outflow</Text>
                      <Text type="danger" strong>
                        -{analysis.cash_flow?.total_outflow?.toLocaleString() || 0}
                      </Text>
                    </div>
                    <div className="flex justify-between border-t pt-2">
                      <Text strong>Net Change</Text>
                      <Text
                        type={
                          (analysis.cash_flow?.net_change || 0) >= 0 ? 'success' : 'danger'
                        }
                        strong
                      >
                        {analysis.cash_flow?.net_change?.toLocaleString() || 0}
                      </Text>
                    </div>
                  </Space>
                </Card>
              </Col>

              <Col xs={24} lg={12}>
                <Card title="Expense Breakdown">
                  {analysis.expense_breakdown?.map((cat: CategorySummary) => (
                    <div key={cat.category} className="mb-2">
                      <div className="flex justify-between mb-1">
                        <Tag color={getCategoryColor(cat.category)}>{cat.category}</Tag>
                        <Text>{cat.total_amount.toLocaleString()}</Text>
                      </div>
                      <Progress
                        percent={cat.percentage}
                        size="small"
                        showInfo={false}
                      />
                    </div>
                  )) || <Empty description="No expense data" />}
                </Card>
              </Col>

              <Col xs={24}>
                <Card title="Anomalies Detected">
                  {analysis.anomalies?.length ? (
                    <Table
                      dataSource={analysis.anomalies}
                      columns={[
                        {
                          title: 'Type',
                          dataIndex: 'anomaly_type',
                          key: 'anomaly_type',
                        },
                        {
                          title: 'Description',
                          dataIndex: 'description',
                          key: 'description',
                        },
                        {
                          title: 'Severity',
                          dataIndex: 'severity',
                          key: 'severity',
                          render: (severity: string) => (
                            <Tag color={severity === 'high' ? 'red' : 'orange'}>
                              {severity}
                            </Tag>
                          ),
                        },
                        {
                          title: 'Amount',
                          dataIndex: 'amount',
                          key: 'amount',
                          render: (amount: number) => amount.toLocaleString(),
                        },
                      ]}
                      rowKey="transaction_id"
                      pagination={false}
                      size="small"
                    />
                  ) : (
                    <Empty description="No anomalies detected" />
                  )}
                </Card>
              </Col>
            </Row>
          ) : (
            <Empty description="Select a statement to view analysis" />
          )}
        </Tabs.TabPane>
      </Tabs>
    </div>
  )
}

export default BSIAnalysisPage
