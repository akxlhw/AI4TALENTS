import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Badge, Button, Card, Checkbox, Col, Form, Input, InputNumber, Modal,
  Popconfirm, Row, Space, Table, Tag, Typography, message,
} from 'antd'
import { KeyOutlined, PlusOutlined } from '@ant-design/icons'
import { apiKeysApi, type ApiKeyCreated, type ApiKeyListItem } from '../../services/api/apiKeys'
import { formatDBLocal } from '../../utils/datetime'
import { getErrorMessage } from './components/utils'

const { Text, Title } = Typography

// Domain × read/write scope matrix (mirrors backend scope strings)
const DOMAINS: { code: string; label: string; color: string }[] = [
  { code: 'academic', label: '学术', color: 'blue' },
  { code: 'open_source', label: '开源', color: 'purple' },
  { code: 'competition', label: '竞赛', color: 'gold' },
  { code: 'lab', label: '实验室', color: 'cyan' },
  { code: 'industry', label: '行业', color: 'magenta' },
]

const ApiKeysTab: React.FC = () => {
  const [keys, setKeys] = useState<ApiKeyListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [createVisible, setCreateVisible] = useState(false)
  const [creating, setCreating] = useState(false)
  const [created, setCreated] = useState<ApiKeyCreated | null>(null)
  const [form] = Form.useForm()

  const loadKeys = useCallback(async () => {
    setLoading(true)
    try {
      const res = await apiKeysApi.list()
      setKeys(res.data || [])
    } catch (e) {
      message.error(getErrorMessage(e, '加载 API Key 失败'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadKeys()
  }, [loadKeys])

  const handleCreate = async () => {
    const values = await form.validateFields()
    setCreating(true)
    try {
      const res = await apiKeysApi.create({
        key_name: values.key_name,
        scopes: values.scopes,
        rate_limit_per_minute: values.rate_limit_per_minute,
      })
      setCreated(res.data)
      setCreateVisible(false)
      form.resetFields()
      loadKeys()
    } catch (e) {
      message.error(getErrorMessage(e, '创建失败'))
    } finally {
      setCreating(false)
    }
  }

  const handleSetActive = async (id: number, isActive: boolean) => {
    try {
      await apiKeysApi.setActive(id, isActive)
      message.success(isActive ? '已启用' : '已吊销')
      loadKeys()
    } catch (e) {
      message.error(getErrorMessage(e, '操作失败'))
    }
  }

  const columns = [
    {
      title: 'Key',
      dataIndex: 'key_prefix',
      key: 'key_prefix',
      width: 130,
      render: (prefix: string) => (
        <Text code style={{ fontSize: 12 }}>{prefix}…</Text>
      ),
    },
    { title: '备注名', dataIndex: 'key_name', key: 'key_name', width: 160 },
    {
      title: '权限范围',
      dataIndex: 'scopes',
      key: 'scopes',
      render: (scopes: string[]) => (
        <Space size={4} wrap>
          {scopes.map(s => {
            const [domain, action] = s.split(':')
            const d = DOMAINS.find(x => x.code === domain)
            return (
              <Tag key={s} style={{ margin: 0, fontSize: 11 }}>
                {d?.label ?? domain}·{action === 'write' ? '读写' : '读'}
              </Tag>
            )
          })}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 90,
      render: (active: boolean) =>
        active ? <Badge status="success" text="启用" /> : <Badge status="error" text="已吊销" />,
    },
    {
      title: '限流/分',
      dataIndex: 'rate_limit_per_minute',
      key: 'rate',
      width: 90,
      render: (v: number | null) => (v ? <Text>{v}</Text> : <Text type="secondary">默认</Text>),
    },
    {
      title: '最近使用',
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      width: 160,
      render: (v: string | null) => (v ? formatDBLocal(v) : <Text type="secondary">从未</Text>),
    },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record: ApiKeyListItem) =>
        record.is_active ? (
          <Popconfirm
            title="确定吊销此 Key？"
            description="吊销后立即生效，使用该 Key 的调用将全部 401"
            okText="吊销"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            onConfirm={() => handleSetActive(record.api_key_id, false)}
          >
            <Button type="link" size="small" danger>吊销</Button>
          </Popconfirm>
        ) : (
          <Button type="link" size="small" onClick={() => handleSetActive(record.api_key_id, true)}>
            启用
          </Button>
        ),
    },
  ]

  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={5} style={{ margin: 0 }}>
          <KeyOutlined style={{ marginRight: 8 }} />
          API Key 管理
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}>
          创建 Key
        </Button>
      </div>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16, fontSize: 13 }}>
        供外部工具 / Skill 调用开放 API（/api/v1/open-api/*）。明文 Key 仅创建时展示一次；权限按 域×读写 粒度授权。
      </Text>

      <Table
        dataSource={keys}
        columns={columns}
        rowKey="api_key_id"
        loading={loading}
        pagination={keys.length > 20 ? { pageSize: 20 } : false}
      />

      <Modal
        title="创建 API Key"
        open={createVisible}
        onCancel={() => setCreateVisible(false)}
        onOk={handleCreate}
        confirmLoading={creating}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="key_name"
            label="备注名"
            rules={[{ required: true, message: '请输入备注名' }]}
          >
            <Input placeholder="如：洞察 Skill / 数据看板" maxLength={100} />
          </Form.Item>
          <Form.Item
            name="scopes"
            label="权限范围（域 × 读写）"
            rules={[{ required: true, message: '至少勾选一个权限' }]}
          >
            <Checkbox.Group style={{ width: '100%' }}>
              {DOMAINS.map(d => (
                <Row key={d.code} gutter={8} style={{ marginBottom: 4 }}>
                  <Col span={5}>
                    <Tag color={d.color} style={{ margin: 0 }}>{d.label}</Tag>
                  </Col>
                  <Col>
                    <Checkbox value={`${d.code}:read`}>只读</Checkbox>
                    <Checkbox value={`${d.code}:write`} style={{ marginLeft: 16 }}>
                      读写（含导入）
                    </Checkbox>
                  </Col>
                </Row>
              ))}
            </Checkbox.Group>
          </Form.Item>
          <Form.Item name="rate_limit_per_minute" label="限流（次/分钟，留空用全局默认）">
            <InputNumber min={1} max={10000} style={{ width: '100%' }} placeholder="默认" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Key 已创建"
        open={!!created}
        onCancel={() => setCreated(null)}
        footer={<Button type="primary" onClick={() => setCreated(null)}>我已保存</Button>}
      >
        <Alert
          type="warning"
          showIcon
          message="明文 Key 仅此一次展示，关闭后无法再查看"
          style={{ marginBottom: 12 }}
        />
        {created && (
          <Typography.Paragraph copyable={{ text: created.plaintext_key }}>
            <Text code style={{ fontSize: 13, wordBreak: 'break-all' }}>
              {created.plaintext_key}
            </Text>
          </Typography.Paragraph>
        )}
      </Modal>
    </Card>
  )
}

export default ApiKeysTab
