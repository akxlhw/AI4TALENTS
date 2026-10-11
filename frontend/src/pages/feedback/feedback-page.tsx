import { useEffect, useState } from 'react'
import { logger } from '../../utils/logger'
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
import { useTranslation } from 'react-i18next'
import { api } from '../../services/api'
import { getErrorMessage } from '../../utils'
import '../../i18n/namespaces/user'
import ImagePasteUpload from '../../components/ImagePasteUpload'
import type { UploadFile } from 'antd/es/upload/interface'

const { Title, Text } = Typography
const { TextArea } = Input

const CATEGORY_VALUES = ['feature', 'bug', 'data_issue', 'experience', 'other'] as const

const CATEGORY_LABEL_KEYS: Record<string, string> = {
  feature: 'user:feedback.category.feature',
  bug: 'user:feedback.category.bug',
  data_issue: 'user:feedback.category.dataIssue',
  experience: 'user:feedback.category.experience',
  other: 'user:feedback.category.other',
}

const STATUS_LABEL_KEYS: Record<string, string> = {
  open: 'user:feedback.status.open',
  in_progress: 'user:feedback.status.inProgress',
  resolved: 'user:feedback.status.resolved',
  closed: 'user:feedback.status.closed',
}

// Ant Design Tag preset colors (language-independent)
const STATUS_COLORS: Record<string, string> = {
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
}

const FeedbackPage: React.FC = () => {
  const { t, i18n } = useTranslation('user')
  const [form] = Form.useForm()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [mySuggestions, setMySuggestions] = useState<SuggestionItem[]>([])
  const [myTotal, setMyTotal] = useState(0)
  const [myPage, setMyPage] = useState(1)
  const [loadingList, setLoadingList] = useState(false)

  const categoryOptions = CATEGORY_VALUES.map(value => ({
    value,
    label: t(CATEGORY_LABEL_KEYS[value]),
  }))

  const fetchMySuggestions = async (page = 1) => {
    setLoadingList(true)
    try {
      const res = await api.suggestions.listMy({ page, page_size: 10 })
      setMySuggestions(res.data.items || [])
      setMyTotal(res.data.total || 0)
    } catch (e) {
      logger.error('Failed to load suggestions', e)
      message.error(t('feedback.loadFailed'))
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
      message.success(t('feedback.submitted'))
      form.resetFields()
      setFileList([])
      setMyPage(1)
      fetchMySuggestions(1)
    } catch (e) {
      message.error(getErrorMessage(e, t('feedback.submitFailed')))
    } finally {
      setSubmitting(false)
    }
  }

  const columns = [
    {
      title: t('feedback.columns.category'),
      dataIndex: 'category',
      width: 100,
      render: (v: string) => <Tag>{t(CATEGORY_LABEL_KEYS[v] || '', { defaultValue: v })}</Tag>,
    },
    {
      title: t('feedback.columns.subject'),
      dataIndex: 'subject',
      width: 200,
      ellipsis: true,
    },
    {
      title: t('feedback.columns.content'),
      dataIndex: 'content',
      ellipsis: true,
    },
    {
      title: t('feedback.columns.status'),
      dataIndex: 'status',
      width: 100,
      render: (v: string) => {
        const label = t(STATUS_LABEL_KEYS[v] || '', { defaultValue: v })
        return <Tag color={STATUS_COLORS[v] || 'default'}>{label}</Tag>
      },
    },
    {
      title: t('feedback.columns.adminReply'),
      dataIndex: 'admin_reply',
      width: 200,
      ellipsis: true,
      render: (v: string | null) => v || '-',
    },
    {
      title: t('feedback.columns.attachments'),
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
      title: t('feedback.columns.createdAt'),
      dataIndex: 'created_at',
      width: 160,
      render: (v: string) => new Date(v).toLocaleString(i18n.language === 'en' ? 'en-US' : 'zh-CN'),
    },
  ]

  return (
    <div style={{ padding: '88px 32px 80px', maxWidth: 1200, margin: '0 auto' }}>
      <Title level={3} style={{ marginBottom: 24 }}>
        <MessageOutlined style={{ marginRight: 8 }} />
        {t('feedback.title')}
      </Title>

      <Card title={t('feedback.formTitle')} style={{ marginBottom: 24 }}>
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="category"
            label={t('feedback.category.label')}
            rules={[{ required: true, message: t('feedback.category.required') }]}
          >
            <Select placeholder={t('feedback.category.placeholder')} options={categoryOptions} />
          </Form.Item>
          <Form.Item
            name="subject"
            label={t('feedback.subject.label')}
            rules={[{ required: true, message: t('feedback.subject.required') }]}
          >
            <Input placeholder={t('feedback.subject.placeholder')} maxLength={200} showCount />
          </Form.Item>
          <Form.Item
            name="content"
            label={t('feedback.content.label')}
            rules={[{ required: true, message: t('feedback.content.required') }]}
          >
            <TextArea
              placeholder={t('feedback.content.placeholder')}
              rows={6}
              showCount
              maxLength={5000}
            />
          </Form.Item>
          <Form.Item label={t('feedback.attachments')}>
            <ImagePasteUpload fileList={fileList} onChange={setFileList} maxCount={5} />
          </Form.Item>
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SendOutlined />}
              loading={submitting}
            >
              {t('feedback.submit')}
            </Button>
          </Form.Item>
        </Form>
      </Card>

      <Card title={t('feedback.historyTitle')}>
        <Spin spinning={loadingList}>
          {mySuggestions.length === 0 ? (
            <Empty description={t('feedback.emptyHistory')} />
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
