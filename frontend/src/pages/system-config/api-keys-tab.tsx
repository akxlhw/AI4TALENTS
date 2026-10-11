import { useCallback, useEffect, useState } from 'react'
import {
  Alert, Badge, Button, Card, Checkbox, Col, Form, Input, InputNumber, Modal,
  Popconfirm, Row, Space, Table, Tag, Typography, message,
} from 'antd'
import { useTranslation } from 'react-i18next'
import { KeyOutlined, PlusOutlined } from '@ant-design/icons'
import { apiKeysApi, type ApiKeyCreated, type ApiKeyListItem } from '../../services/api/apiKeys'
import { formatDBLocal } from '../../utils/datetime'
import '../../i18n/namespaces/system-config'
import { getErrorMessage } from './components/utils'

const { Text, Title } = Typography

// Domain × read/write scope matrix (mirrors backend scope strings);
// labels are resolved through the systemConfig namespace at render time.
const DOMAINS: { code: string; color: string }[] = [
  { code: 'academic', color: 'blue' },
  { code: 'open_source', color: 'purple' },
  { code: 'competition', color: 'gold' },
  { code: 'lab', color: 'cyan' },
  { code: 'industry', color: 'magenta' },
]

const ApiKeysTab: React.FC = () => {
  const { t } = useTranslation(['systemConfig', 'common'])
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
      message.error(getErrorMessage(e, t('apiKeys.loadFailed')))
    } finally {
      setLoading(false)
    }
  }, [t])

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
      message.error(getErrorMessage(e, t('apiKeys.createFailed')))
    } finally {
      setCreating(false)
    }
  }

  const handleSetActive = async (id: number, isActive: boolean) => {
    try {
      await apiKeysApi.setActive(id, isActive)
      message.success(isActive ? t('apiKeys.activated') : t('apiKeys.statusRevoked'))
      loadKeys()
    } catch (e) {
      message.error(getErrorMessage(e, t('apiKeys.operationFailed')))
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
    { title: t('apiKeys.columns.name'), dataIndex: 'key_name', key: 'key_name', width: 160 },
    {
      title: t('apiKeys.columns.scopes'),
      dataIndex: 'scopes',
      key: 'scopes',
      render: (scopes: string[]) => (
        <Space size={4} wrap>
          {scopes.map(s => {
            const [domain, action] = s.split(':')
            const d = DOMAINS.find(x => x.code === domain)
            return (
              <Tag key={s} style={{ margin: 0, fontSize: 11 }}>
                {(d ? t(`apiKeys.domains.${d.code}`) : domain)}·{action === 'write' ? t('apiKeys.scopeReadWrite') : t('apiKeys.scopeRead')}
              </Tag>
            )
          })}
        </Space>
      ),
    },
    {
      title: t('apiKeys.columns.status'),
      dataIndex: 'is_active',
      key: 'is_active',
      width: 90,
      render: (active: boolean) =>
        active ? (
          <Badge status="success" text={t('apiKeys.statusActive')} />
        ) : (
          <Badge status="error" text={t('apiKeys.statusRevoked')} />
        ),
    },
    {
      title: t('apiKeys.columns.rate'),
      dataIndex: 'rate_limit_per_minute',
      key: 'rate',
      width: 90,
      render: (v: number | null) => (v ? <Text>{v}</Text> : <Text type="secondary">{t('apiKeys.columns.rateDefault')}</Text>),
    },
    {
      title: t('apiKeys.columns.lastUsed'),
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      width: 160,
      render: (v: string | null) => (v ? formatDBLocal(v) : <Text type="secondary">{t('apiKeys.columns.neverUsed')}</Text>),
    },
    {
      title: t('apiKeys.columns.actions'),
      key: 'actions',
      width: 100,
      render: (_: unknown, record: ApiKeyListItem) =>
        record.is_active ? (
          <Popconfirm
            title={t('apiKeys.revokeConfirmTitle')}
            description={t('apiKeys.revokeConfirmDescription')}
            okText={t('apiKeys.revoke')}
            cancelText={t('common.cancel')}
            okButtonProps={{ danger: true }}
            onConfirm={() => handleSetActive(record.api_key_id, false)}
          >
            <Button type="link" size="small" danger>{t('apiKeys.revoke')}</Button>
          </Popconfirm>
        ) : (
          <Button type="link" size="small" onClick={() => handleSetActive(record.api_key_id, true)}>
            {t('apiKeys.enable')}
          </Button>
        ),
    },
  ]

  return (
    <Card>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={5} style={{ margin: 0 }}>
          <KeyOutlined style={{ marginRight: 8 }} />
          {t('apiKeys.title')}
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}>
          {t('apiKeys.createButton')}
        </Button>
      </div>
      <Text type="secondary" style={{ display: 'block', marginBottom: 16, fontSize: 13 }}>
        {t('apiKeys.intro')}
      </Text>

      <Table
        dataSource={keys}
        columns={columns}
        rowKey="api_key_id"
        loading={loading}
        pagination={keys.length > 20 ? { pageSize: 20 } : false}
      />

      <Modal
        title={t('apiKeys.createModalTitle')}
        open={createVisible}
        onCancel={() => setCreateVisible(false)}
        onOk={handleCreate}
        confirmLoading={creating}
        okText={t('apiKeys.createOkText')}
        cancelText={t('common.cancel')}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="key_name"
            label={t('apiKeys.nameLabel')}
            rules={[{ required: true, message: t('apiKeys.nameRequired') }]}
          >
            <Input placeholder={t('apiKeys.namePlaceholder')} maxLength={100} />
          </Form.Item>
          <Form.Item
            name="scopes"
            label={t('apiKeys.scopesLabel')}
            rules={[{ required: true, message: t('apiKeys.scopesRequired') }]}
          >
            <Checkbox.Group style={{ width: '100%' }}>
              {DOMAINS.map(d => (
                <Row key={d.code} gutter={8} style={{ marginBottom: 4 }}>
                  <Col span={5}>
                    <Tag color={d.color} style={{ margin: 0 }}>{t(`apiKeys.domains.${d.code}`)}</Tag>
                  </Col>
                  <Col>
                    <Checkbox value={`${d.code}:read`}>{t('apiKeys.readOnly')}</Checkbox>
                    <Checkbox value={`${d.code}:write`} style={{ marginLeft: 16 }}>
                      {t('apiKeys.readWriteWithImport')}
                    </Checkbox>
                  </Col>
                </Row>
              ))}
            </Checkbox.Group>
          </Form.Item>
          <Form.Item name="rate_limit_per_minute" label={t('apiKeys.rateLimitLabel')}>
            <InputNumber min={1} max={10000} style={{ width: '100%' }} placeholder={t('apiKeys.rateLimitPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={t('apiKeys.createdModalTitle')}
        open={!!created}
        onCancel={() => setCreated(null)}
        footer={<Button type="primary" onClick={() => setCreated(null)}>{t('apiKeys.createdOkText')}</Button>}
      >
        <Alert
          type="warning"
          showIcon
          message={t('apiKeys.createdWarning')}
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
