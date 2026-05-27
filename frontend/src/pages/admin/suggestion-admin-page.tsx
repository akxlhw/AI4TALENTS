import { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Tag,
  Select,
  Button,
  Space,
  Typography,
  Modal,
  Input,
  Empty,
  Image,
  message,
  Badge,
  Row,
  Col,
} from 'antd'
import {
  EyeOutlined,
  MessageOutlined,
  ReloadOutlined,
  MessageFilled,
} from '@ant-design/icons'
import { api } from '../../services/api'
import { getErrorMessage } from '../../utils'

const { Title, Text } = Typography
const { TextArea } = Input

const CATEGORY_OPTIONS = [
  { value: 'feature', label: '功能建议' },
  { value: 'bug', label: 'Bug 反馈' },
  { value: 'data_issue', label: '数据纠错' },
  { value: 'experience', label: '体验反馈' },
  { value: 'other', label: '其他' },
]

const STATUS_OPTIONS = [
  { value: '', label: '全部状态' },
  { value: 'open', label: '待处理' },
  { value: 'in_progress', label: '处理中' },
  { value: 'resolved', label: '已解决' },
  { value: 'closed', label: '已关闭' },
]

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  open: { label: '待处理', color: 'orange' },
  in_progress: { label: '处理中', color: 'blue' },
  resolved: { label: '已解决', color: 'green' },
  closed: { label: '已关闭', color: 'default' },
}

interface SuggestionItem {
  suggestion_id: number
  category: string
  subject: string
  content: string
  status: string
  admin_reply: string | null
  attachments: string[]
  created_at: string
  updated_at: string
  user_id: number
}

const SuggestionAdminPage: React.FC = () => {
  const [data, setData] = useState<SuggestionItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [loading, setLoading] = useState(false)

  const [detailVisible, setDetailVisible] = useState(false)
  const [detail, setDetail] = useState<SuggestionItem | null>(null)

  const [replyVisible, setReplyVisible] = useState(false)
  const [replyContent, setReplyContent] = useState('')
  const [replying, setReplying] = useState(false)

  const fetchData = async (p = 1, status?: string, category?: string) => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { page: p, page_size: 10 }
      if (status) params.status = status
      if (category) params.category = category
      const res = await api.suggestions.listAll(params)
      setData(res.data.items || [])
      setTotal(res.data.total || 0)
    } catch (e) {
      message.error(getErrorMessage(e, '加载失败'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData(1, statusFilter, categoryFilter)
    setPage(1)
  }, [statusFilter, categoryFilter])

  useEffect(() => {
    fetchData(page, statusFilter, categoryFilter)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page])

  const showDetail = (item: SuggestionItem) => {
    setDetail(item)
    setDetailVisible(true)
  }

  const showReply = (item: SuggestionItem) => {
    setDetail(item)
    setReplyContent(item.admin_reply || '')
    setReplyVisible(true)
  }

  const handleReply = async () => {
    if (!detail) return
    if (!replyContent.trim()) {
      message.error('请输入回复内容')
      return
    }
    setReplying(true)
    try {
      await api.suggestions.reply(detail.suggestion_id, {
        admin_reply: replyContent.trim(),
        status: 'resolved',
      })
      message.success('回复成功')
      setReplyVisible(false)
      fetchData(page, statusFilter, categoryFilter)
    } catch (e) {
      message.error(getErrorMessage(e, '回复失败'))
    } finally {
      setReplying(false)
    }
  }

  // 简单统计（基于当前页数据）
  const statusCounts = data.reduce(
    (acc, item) => {
      acc[item.status] = (acc[item.status] || 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  const columns = [
    {
      title: 'ID',
      dataIndex: 'suggestion_id',
      width: 70,
      align: 'center' as const,
    },
    {
      title: '用户ID',
      dataIndex: 'user_id',
      width: 85,
      align: 'center' as const,
    },
    {
      title: '分类',
      dataIndex: 'category',
      width: 100,
      align: 'center' as const,
      render: (v: string) => (
        <Tag>{CATEGORY_OPTIONS.find((c) => c.value === v)?.label || v}</Tag>
      ),
    },
    {
      title: '主题',
      dataIndex: 'subject',
      width: 220,
      ellipsis: true,
    },
    {
      title: '内容',
      dataIndex: 'content',
      minWidth: 200,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      align: 'center' as const,
      render: (v: string) => {
        const s = STATUS_MAP[v] || { label: v, color: 'default' }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    {
      title: '管理员回复',
      dataIndex: 'admin_reply',
      width: 140,
      ellipsis: true,
      render: (v: string | null) =>
        v ? (
          <Badge dot color="green">
            <Text type="secondary" style={{ fontSize: 12 }}>已回复</Text>
          </Badge>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>-</Text>
        ),
    },
    {
      title: '提交时间',
      dataIndex: 'created_at',
      width: 170,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      align: 'center' as const,
      fixed: 'right' as const,
      render: (_: unknown, record: SuggestionItem) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => showDetail(record)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<MessageOutlined />}
            onClick={() => showReply(record)}
          >
            回复
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <Title level={4} style={{ marginBottom: 16 }}>
        <MessageFilled style={{ marginRight: 8, color: '#1677ff' }} />
        建议管理
      </Title>

      {/* 统计概览 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {STATUS_OPTIONS.filter((s) => s.value).map((s) => (
          <Col key={s.value}>
            <Card
              size="small"
              style={{
                minWidth: 120,
                textAlign: 'center',
                borderTop: `3px solid ${STATUS_MAP[s.value]?.color || '#d9d9d9'}`,
              }}
              bodyStyle={{ padding: '12px 24px' }}
            >
              <div style={{ fontSize: 24, fontWeight: 700, color: '#262626' }}>
                {statusCounts[s.value] || 0}
              </div>
              <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>
                {s.label}
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Card
        title={
          <Space>
            <span>建议列表</span>
            <Text type="secondary" style={{ fontSize: 13, fontWeight: 400 }}>
              共 {total} 条
            </Text>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder="状态筛选"
            value={statusFilter || undefined}
            onChange={(val) => setStatusFilter(val || '')}
            options={STATUS_OPTIONS}
            style={{ width: 140 }}
            allowClear
          />
          <Select
            placeholder="分类筛选"
            value={categoryFilter || undefined}
            onChange={(val) => setCategoryFilter(val || '')}
            options={[{ value: '', label: '全部分类' }, ...CATEGORY_OPTIONS]}
            style={{ width: 140 }}
            allowClear
          />
          <Button icon={<ReloadOutlined />} onClick={() => fetchData(page, statusFilter, categoryFilter)}>
            刷新
          </Button>
        </Space>

        <Table
          dataSource={data}
          columns={columns}
          rowKey="suggestion_id"
          loading={loading}
          pagination={{
            current: page,
            pageSize: 10,
            total,
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 条`,
          }}
          onChange={(pagination) => setPage(pagination.current || 1)}
          locale={{ emptyText: <Empty description="暂无数据" /> }}
          scroll={{ x: 1200 }}
          size="middle"
        />
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title="建议详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>,
        ]}
        width={720}
      >
        {detail && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Row gutter={16}>
              <Col span={12}>
                <Text strong>分类：</Text>
                <Tag>
                  {CATEGORY_OPTIONS.find((c) => c.value === detail.category)?.label ||
                    detail.category}
                </Tag>
              </Col>
              <Col span={12} style={{ textAlign: 'right' }}>
                <Tag color={STATUS_MAP[detail.status]?.color || 'default'}>
                  {STATUS_MAP[detail.status]?.label || detail.status}
                </Tag>
              </Col>
            </Row>
            <div>
              <Text strong>主题：</Text>
              <Text>{detail.subject}</Text>
            </div>
            <div>
              <Text strong>内容：</Text>
              <div
                style={{
                  whiteSpace: 'pre-wrap',
                  background: '#f6ffed',
                  padding: 12,
                  borderRadius: 6,
                  marginTop: 4,
                  border: '1px solid #d9f7be',
                }}
              >
                {detail.content}
              </div>
            </div>
            {detail.admin_reply && (
              <div>
                <Text strong>管理员回复：</Text>
                <div
                  style={{
                    whiteSpace: 'pre-wrap',
                    background: '#e6f7ff',
                    padding: 12,
                    borderRadius: 6,
                    marginTop: 4,
                    border: '1px solid #91d5ff',
                  }}
                >
                  {detail.admin_reply}
                </div>
              </div>
            )}
            {detail.attachments?.length > 0 && (
              <div>
                <Text strong>附件：</Text>
                <Space wrap>
                  {detail.attachments.map((url, idx) => (
                    <Image
                      key={idx}
                      src={url}
                      width={120}
                      height={120}
                      style={{ objectFit: 'cover', borderRadius: 6 }}
                      preview={{ src: url }}
                    />
                  ))}
                </Space>
              </div>
            )}
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                用户ID：{detail.user_id} · 提交时间：
                {new Date(detail.created_at).toLocaleString('zh-CN')}
              </Text>
            </div>
          </Space>
        )}
      </Modal>

      {/* 回复弹窗 */}
      <Modal
        title="回复建议"
        open={replyVisible}
        onCancel={() => setReplyVisible(false)}
        onOk={handleReply}
        confirmLoading={replying}
        width={600}
      >
        {detail && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>主题：</Text>
              <Text>{detail.subject}</Text>
            </div>
            <div>
              <Text strong>内容：</Text>
              <div
                style={{
                  whiteSpace: 'pre-wrap',
                  background: '#f6ffed',
                  padding: 8,
                  borderRadius: 4,
                  maxHeight: 120,
                  overflow: 'auto',
                }}
              >
                {detail.content}
              </div>
            </div>
            <div>
              <Text strong>回复内容：</Text>
              <TextArea
                rows={4}
                value={replyContent}
                onChange={(e) => setReplyContent(e.target.value)}
                placeholder="请输入回复内容..."
                maxLength={2000}
                showCount
              />
            </div>
          </Space>
        )}
      </Modal>
    </div>
  )
}

export default SuggestionAdminPage
