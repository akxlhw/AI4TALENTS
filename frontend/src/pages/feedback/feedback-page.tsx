import { useEffect, useState } from 'react'
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  Space,
  Typography,
  Table,
  Tag,
  Pagination,
  Empty,
  Spin,
  message,
  Image,
} from 'antd'
import { SendOutlined, MessageOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import { getErrorMessage } from '../../utils'
import ImagePasteUpload from '../../components/ImagePasteUpload'
import type { UploadFile } from 'antd/es/upload/interface'

const { Title, Text } = Typography
const { TextArea } = Input

const CATEGORY_OPTIONS = [
  { value: 'feature', label: '功能建议' },
  { value: 'bug', label: 'Bug 反馈' },
  { value: 'data_issue', label: '数据纠错' },
  { value: 'experience', label: '体验反馈' },
  { value: 'other', label: '其他' },
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
}

const FeedbackPage: React.FC = () => {
  const [form] = Form.useForm()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [mySuggestions, setMySuggestions] = useState<SuggestionItem[]>([])
  const [myTotal, setMyTotal] = useState(0)
  const [myPage, setMyPage] = useState(1)
  const [loadingList, setLoadingList] = useState(false)

  const fetchMySuggestions = async (page = 1) => {
    setLoadingList(true)
    try {
      const res = await api.suggestions.listMy({ page, page_size: 10 })
      setMySuggestions(res.data.items || [])
      setMyTotal(res.data.total || 0)
    } catch (e) {
      console.error('Failed to load suggestions', e)
    } finally {
      setLoadingList(false)
    }
  }

  useEffect(() => {
    fetchMySuggestions(myPage)
  }, [myPage])

  const handleSubmit = async (values: { category: string; subject: string; content: string }) => {
    setSubmitting(true)
    try {
      const formData = new FormData()
      formData.append('category', values.category)
      formData.append('subject', values.subject)
      formData.append('content', values.content)
      fileList.forEach((file) => {
        if (file.originFileObj) {
          formData.append('files', file.originFileObj)
        }
      })

      await api.suggestions.create(formData)
      message.success('建议提交成功')
      form.resetFields()
      setFileList([])
      setMyPage(1)
      fetchMySuggestions(1)
    } catch (e) {
      message.error(getErrorMessage(e, '提交失败'))
    } finally {
      setSubmitting(false)
    }
  }

  const columns = [
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
      title: '内容',
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
      title: '管理员回复',
      dataIndex: 'admin_reply',
      width: 200,
      ellipsis: true,
      render: (v: string | null) => v || '-',
    },
    {
      title: '附件',
      dataIndex: 'attachments',
      width: 120,
      render: (v: string[]) =>
        v?.length ? (
          <Space>
            {v.slice(0, 3).map((url, idx) => (
              <Image
                key={idx}
                src={url}
                width={40}
                height={40}
                style={{ borderRadius: 4, objectFit: 'cover' }}
                preview={{ src: url }}
              />
            ))}
            {v.length > 3 && <Text type="secondary">+{v.length - 3}</Text>}
          </Space>
        ) : (
          '-'
        ),
    },
    {
      title: '提交时间',
      dataIndex: 'created_at',
      width: 160,
      render: (v: string) => new Date(v).toLocaleString('zh-CN'),
    },
  ]

  return (
    <div style={{ padding: '88px 32px 80px', maxWidth: 1200, margin: '0 auto' }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        <MessageOutlined style={{ marginRight: 8 }} />
        意见反馈
      </Title>

      <Card title="提交新建议" style={{ marginBottom: 24 }}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="category"
            label="分类"
            rules={[{ required: true, message: '请选择分类' }]}
          >
            <Select placeholder="选择分类" options={CATEGORY_OPTIONS} />
          </Form.Item>
          <Form.Item
            name="subject"
            label="主题"
            rules={[{ required: true, message: '请输入主题' }]}
          >
            <Input placeholder="简要描述您的建议主题" maxLength={200} showCount />
          </Form.Item>
          <Form.Item
            name="content"
            label="详细内容"
            rules={[{ required: true, message: '请输入详细内容' }]}
          >
            <TextArea
              placeholder="请详细描述您的建议、遇到的问题或数据纠错内容..."
              rows={6}
              showCount
              maxLength={5000}
            />
          </Form.Item>
          <Form.Item label="截图附件">
            <ImagePasteUpload fileList={fileList} onChange={setFileList} maxCount={5} />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SendOutlined />}
              loading={submitting}
            >
              提交建议
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card title="我的历史建议">
        <Spin spinning={loadingList}>
          {mySuggestions.length === 0 ? (
            <Empty description="暂无提交记录" />
          ) : (
            <>
              <Table
                dataSource={mySuggestions}
                columns={columns}
                rowKey="suggestion_id"
                pagination={false}
                size="small"
              />
              <div style={{ display: 'flex', justifyContent: 'center', marginTop: 16 }}>
                <Pagination
                  current={myPage}
                  pageSize={10}
                  total={myTotal}
                  onChange={setMyPage}
                  showSizeChanger={false}
                />
              </div>
            </>
          )}
        </Spin>
      </Card>
    </div>
  )
}

export default FeedbackPage
