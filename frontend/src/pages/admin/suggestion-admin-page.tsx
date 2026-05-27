import { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Tag,
  Pagination,
  Select,
  Button,
  Space,
  Typography,
  Modal,
  Input,
  Spin,
  Empty,
  Image,
  message,
} from 'antd'
import { EyeOutlined, MessageOutlined } from '@ant-design/icons'
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
      const params: Record<string, any> = { page: p, page_size: 10 }
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

  const columns = [
    {
      title: 'ID',
      dataIndex: 'suggestion_id',
      width: 70,
    },
    {
      title: '用户ID',
      dataIndex: 'user_id',
      width: 80,
    },
    {
      title: '分类',
      dataIndex: 'category',
      width: 100,
      render: (v: string) => (
        <Tag>{CATEGORY_OPTIONS.find((c) => c.value === v)?.label || v}</Tag>
      ),
    },
    {
      title: '主题',
      dataIndex: 'subject',
      width: 200,
      ellipsis: true,
    },
    {
      title: '内容摘要',
      dataIndex: 'content',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (v: string) => {
        const s = STATUS_MAP[v] || { label: v, color: 'default' }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    {
      title: '提交时间',
      dataIndex: 'created_at',
      width: 160,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      render: (_: any, record: SuggestionItem) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => showDetail(record)}>
            详情
          </Button>
          <Button type="link" size="small" icon={<MessageOutlined />} onClick={() => showReply(record)}>
            回复
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px 32px 80px', maxWidth: 1400, margin: '0 auto' }}>
      <Title level={3}>建议管理</Title>

      <Card style={{ marginBottom: 24 }}>
        <Space style={{ marginBottom: 16 }}>
          <Select
            placeholder="状态筛选"
            value={statusFilter}
            onChange={setStatusFilter}
            options={STATUS_OPTIONS}
            style={{ width: 140 }}
            allowClear
          />
          <Select
            placeholder="分类筛选"
            value={categoryFilter}
            onChange={setCategoryFilter}
            options={[{ value: '', label: '全部分类' }, ...CATEGORY_OPTIONS]}
            style={{ width: 140 }}
            allowClear
          />
        </Space>

        <Spin spinning={loading}>
          {data.length === 0 ? (
            <Empty description="暂无数据" />
          ) : (
            <>
              <Table dataSource={data} columns={columns} rowKey="suggestion_id" pagination={false} size="small" />
              <div style={{ display: 'flex', justifyContent: 'center', marginTop: 16 }}>
                <Pagination current={page} pageSize={10} total={total} onChange={setPage} showSizeChanger={false} />
              </div>
            </>
          )}
        </Spin>
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
        width={700}
      >
        {detail && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>分类：</Text>
              <Tag>{CATEGORY_OPTIONS.find((c) => c.value === detail.category)?.label || detail.category}</Tag>
            </div>
            <div>
              <Text strong>主题：</Text>
              <Text>{detail.subject}</Text>
            </div>
            <div>
              <Text strong>内容：</Text>
              <div style={{ whiteSpace: 'pre-wrap', background: '#f6ffed', padding: 12, borderRadius: 4, marginTop: 4 }}>
                {detail.content}
              </div>
            </div>
            {detail.admin_reply && (
              <div>
                <Text strong>管理员回复：</Text>
                <div style={{ whiteSpace: 'pre-wrap', background: '#e6f7ff', padding: 12, borderRadius: 4, marginTop: 4 }}>
                  {detail.admin_reply}
                </div>
              </div>
            )}
            {detail.attachments?.length > 0 && (
              <div>
                <Text strong>附件：</Text>
                <Space wrap>
                  {detail.attachments.map((url, idx) => (
                    <Image key={idx} src={url} width={120} height={120} style={{ objectFit: 'cover', borderRadius: 4 }} preview={{ src: url }} />
                  ))}
                </Space>
              </div>
            )}
            <div>
              <Text type="secondary" style={{ fontSize: 12 }}>
                提交时间：{new Date(detail.created_at).toLocaleString('zh-CN')}
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
              <div style={{ whiteSpace: 'pre-wrap', background: '#f6ffed', padding: 8, borderRadius: 4, maxHeight: 120, overflow: 'auto' }}>
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
