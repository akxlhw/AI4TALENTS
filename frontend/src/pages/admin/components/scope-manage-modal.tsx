import {
  Button,
  Form,
  Input,
  List,
  Modal,
  Popconfirm,
  Select,
  Space,
  Tabs,
  Tag,
  Typography,
} from 'antd'
import type { FormInstance } from 'antd'
import { useTranslation } from 'react-i18next'
import { formatUTCToLocal } from '../../../utils/datetime'
import '../../../i18n/namespaces/admin'
import type { Scope } from './types'

const { Text } = Typography

interface ScopeManageModalProps {
  open: boolean
  userScopes: Scope[]
  form: FormInstance
  onCancel: () => void
  onAddScope: (values: Record<string, unknown>) => void
  onRemoveScope: (scopeId: number) => void
}

const ScopeManageModal: React.FC<ScopeManageModalProps> = ({
  open,
  userScopes,
  form,
  onCancel,
  onAddScope,
  onRemoveScope,
}) => {
  const { t } = useTranslation(['admin', 'common'])
  return (
    <Modal title={t('scopes.title')} open={open} onCancel={onCancel} footer={null} width={600}>
      <Tabs
        items={[
          {
            key: 'current',
            label: t('scopes.tabCurrent'),
            children: (
              <List
                dataSource={userScopes}
                renderItem={scope => (
                  <List.Item
                    actions={[
                      <Popconfirm
                        key="remove"
                        title={t('scopes.removeConfirm')}
                        onConfirm={() => onRemoveScope(scope.scope_id)}
                        okText={t('scopes.confirm')}
                        cancelText={t('scopes.cancel')}
                      >
                        <Button type="link" danger size="small">
                          {t('scopes.remove')}
                        </Button>
                      </Popconfirm>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Tag color={scope.scope_type === 'all' ? 'red' : 'blue'}>
                            {t(`scopes.types.${scope.scope_type}`, {
                              defaultValue: scope.scope_type,
                            })}
                          </Tag>
                          <Text>{scope.scope_value}</Text>
                        </Space>
                      }
                      description={
                        <Text type="secondary">
                          {t('scopes.grantedAt', { time: formatUTCToLocal(scope.granted_at) })}
                          {scope.expires_at &&
                            ` | ${t('scopes.expiresAt', { time: formatUTCToLocal(scope.expires_at) })}`}
                        </Text>
                      }
                    />
                  </List.Item>
                )}
                locale={{ emptyText: t('scopes.noScopes') }}
              />
            ),
          },
          {
            key: 'add',
            label: t('scopes.tabAdd'),
            children: (
              <Form form={form} layout="vertical" onFinish={onAddScope}>
                <Form.Item
                  name="scope_type"
                  label={t('scopes.form.type')}
                  rules={[{ required: true }]}
                >
                  <Select
                    options={[
                      { value: 'school', label: t('scopes.types.school') },
                      { value: 'country', label: t('scopes.types.country') },
                      { value: 'tech_domain', label: t('scopes.types.tech_domain') },
                      { value: 'all', label: t('scopes.types.all') },
                    ]}
                  />
                </Form.Item>
                <Form.Item
                  name="scope_value"
                  label={t('scopes.form.value')}
                  rules={[{ required: true }]}
                  extra={t('scopes.form.valueExtra')}
                >
                  <Input placeholder={t('scopes.form.valuePlaceholder')} />
                </Form.Item>
                <Form.Item name="notes" label={t('scopes.form.notes')}>
                  <Input.TextArea rows={2} />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit">
                    {t('scopes.form.submit')}
                  </Button>
                </Form.Item>
              </Form>
            ),
          },
        ]}
      />
    </Modal>
  )
}

export default ScopeManageModal
