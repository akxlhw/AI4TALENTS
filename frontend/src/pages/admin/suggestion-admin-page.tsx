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
import { EyeOutlined, MessageOutlined, ReloadOutlined, MessageFilled } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { api } from '../../services/api'
import { getErrorMessage } from '../../utils'
import '../../i18n/namespaces/admin'

const { Title, Text } = Typography
const { TextArea } = Input

const CATEGORIES = ['feature', 'bug', 'data_issue', 'experience', 'other'] as const

const STATUS_COLOR_MAP: Record<string, string> = {
  open: 'orange',
  in_progress: 'blue',
  resolved: 'green',
  closed: 'default',
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
  username: string
}

const SuggestionAdminPage: React.FC = () => {
  const { t } = useTranslation(['admin', 'common'])
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
  const [replyStatus, setReplyStatus] = useState<string>('resolved')
  const [replying, setReplying] = useState(false)

  const categoryOptions = CATEGORIES.map(value => ({
    value,
    label: t(`suggestions.categories.${value}`),
  }))
  const statusOptions = [
    { value: '', label: t('suggestions.status.all') },
    { value: 'open', label: t('suggestions.status.open') },
    { value: 'in_progress', label: t('suggestions.status.in_progress') },
    { value: 'resolved', label: t('suggestions.status.resolved') },
    { value: 'closed', label: t('suggestions.status.closed') },
  ]
  const statusLabel = (v: string) => t(`suggestions.status.${v}`, { defaultValue: v })

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
      message.error(getErrorMessage(e, t('suggestions.messages.loadFailed')))
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
    // 智能默认状态：待处理→处理中，处理中→已解决，其他保持原状
    const nextStatus =
      item.status === 'open'
        ? 'in_progress'
        : item.status === 'in_progress'
          ? 'resolved'
          : item.status
    setReplyStatus(nextStatus)
    setReplyVisible(true)
  }

  const handleReply = async () => {
    if (!detail) return
    if (!replyContent.trim()) {
      message.error(t('suggestions.messages.replyRequired'))
      return
    }
    setReplying(true)
    try {
      await api.suggestions.reply(detail.suggestion_id, {
        admin_reply: replyContent.trim(),
        status: replyStatus,
      })
      message.success(t('suggestions.messages.replySuccess'))
      setReplyVisible(false)
      fetchData(page, statusFilter, categoryFilter)
    } catch (e) {
      message.error(getErrorMessage(e, t('suggestions.messages.replyFailed')))
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
      title: t('suggestions.columns.id'),
      dataIndex: 'suggestion_id',
      width: 70,
      align: 'center' as const,
    },
    {
      title: t('suggestions.columns.user'),
      dataIndex: 'username',
      width: 120,
      ellipsis: true,
    },
    {
      title: t('suggestions.columns.category'),
      dataIndex: 'category',
      width: 100,
      align: 'center' as const,
      render: (v: string) => <Tag>{categoryOptions.find(c => c.value === v)?.label || v}</Tag>,
    },
    {
      title: t('suggestions.columns.subject'),
      dataIndex: 'subject',
      width: 220,
      ellipsis: true,
    },
    {
      title: t('suggestions.columns.content'),
      dataIndex: 'content',
      minWidth: 200,
      ellipsis: true,
    },
    {
      title: t('suggestions.columns.status'),
      dataIndex: 'status',
      width: 100,
      align: 'center' as const,
      render: (v: string) => <Tag color={STATUS_COLOR_MAP[v] || 'default'}>{statusLabel(v)}</Tag>,
    },
    {
      title: t('suggestions.columns.adminReply'),
      dataIndex: 'admin_reply',
      width: 140,
      ellipsis: true,
      render: (v: string | null) =>
        v ? (
          <Badge dot color="green">
            <Text type="secondary" style={{ fontSize: 12 }}>
              {t('suggestions.replied')}
            </Text>
          </Badge>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>
            -
          </Text>
        ),
    },
    {
      title: t('suggestions.columns.createdAt'),
      dataIndex: 'created_at',
      width: 170,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: t('suggestions.columns.actions'),
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
            {t('suggestions.actions.detail')}
          </Button>
          <Button
            type="link"
            size="small"
            icon={<MessageOutlined />}
            onClick={() => showReply(record)}
          >
            {t('suggestions.actions.reply')}
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <Title level={4} style={{ marginBottom: 16 }}>
        <MessageFilled style={{ marginRight: 8, color: '#1677ff' }} />
        {t('suggestions.title')}
      </Title>

      {/* 统计概览 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        {statusOptions
          .filter(s => s.value)
          .map(s => (
            <Col key={s.value}>
              <Card
                size="small"
                style={{
                  minWidth: 120,
                  textAlign: 'center',
                  borderTop: `3px solid ${STATUS_COLOR_MAP[s.value || ''] || '#d9d9d9'}`,
                }}
                bodyStyle={{ padding: '12px 24px' }}
              >
                <div style={{ fontSize: 24, fontWeight: 700, color: '#262626' }}>
                  {statusCounts[s.value || ''] || 0}
                </div>
                <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 4 }}>{s.label}</div>
              </Card>
            </Col>
          ))}
      </Row>

      <Card
        title={
          <Space>
            <span>{t('suggestions.listTitle')}</span>
            <Text type="secondary" style={{ fontSize: 13, fontWeight: 400 }}>
              {t('common:pagination.total', { n: total })}
            </Text>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder={t('suggestions.filters.status')}
            value={statusFilter || undefined}
            onChange={val => setStatusFilter(val || '')}
            options={statusOptions}
            style={{ width: 140 }}
            allowClear
          />
          <Select
            placeholder={t('suggestions.filters.category')}
            value={categoryFilter || undefined}
            onChange={val => setCategoryFilter(val || '')}
            options={[
              { value: '', label: t('suggestions.filters.allCategories') },
              ...categoryOptions,
            ]}
            style={{ width: 140 }}
            allowClear
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={() => fetchData(page, statusFilter, categoryFilter)}
          >
            {t('actions.refresh')}
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
            showTotal: count => t('common:pagination.total', { n: count }),
          }}
          onChange={pagination => setPage(pagination.current || 1)}
          locale={{ emptyText: <Empty description={t('common:status.empty')} /> }}
          scroll={{ x: 1200 }}
          size="middle"
        />
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title={t('suggestions.detailModal.title')}
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>
            {t('common:actions.close')}
          </Button>,
        ]}
        width={720}
      >
        {detail && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Row gutter={16}>
              <Col span={12}>
                <Text strong>{t('suggestions.detailModal.category')}</Text>
                <Tag>
                  {categoryOptions.find(c => c.value === detail.category)?.label || detail.category}
                </Tag>
              </Col>
              <Col span={12} style={{ textAlign: 'right' }}>
                <Tag color={STATUS_COLOR_MAP[detail.status] || 'default'}>
                  {statusLabel(detail.status)}
                </Tag>
              </Col>
            </Row>
            <div>
              <Text strong>{t('suggestions.detailModal.subject')}</Text>
              <Text>{detail.subject}</Text>
            </div>
            <div>
              <Text strong>{t('suggestions.detailModal.content')}</Text>
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
                <Text strong>{t('suggestions.detailModal.adminReply')}</Text>
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
                <Text strong>{t('suggestions.detailModal.attachments')}</Text>
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
                {t('suggestions.detailModal.meta', {
                  username: detail.username,
                  time: new Date(detail.created_at).toLocaleString('zh-CN'),
                })}
              </Text>
            </div>
          </Space>
        )}
      </Modal>

      {/* 回复弹窗 */}
      <Modal
        title={t('suggestions.replyModal.title')}
        open={replyVisible}
        onCancel={() => setReplyVisible(false)}
        onOk={handleReply}
        confirmLoading={replying}
        width={600}
      >
        {detail && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>{t('suggestions.detailModal.subject')}</Text>
              <Text>{detail.subject}</Text>
            </div>
            <div>
              <Text strong>{t('suggestions.detailModal.content')}</Text>
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
            <Row gutter={16}>
              <Col span={12}>
                <Text strong>{t('suggestions.replyModal.changeStatus')}</Text>
                <Select
                  value={replyStatus}
                  onChange={setReplyStatus}
                  options={statusOptions.filter(s => s.value)}
                  style={{ width: '100%', marginTop: 4 }}
                />
              </Col>
            </Row>
            <div>
              <Text strong>{t('suggestions.replyModal.contentLabel')}</Text>
              <TextArea
                rows={4}
                value={replyContent}
                onChange={e => setReplyContent(e.target.value)}
                placeholder={t('suggestions.replyModal.placeholder')}
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
