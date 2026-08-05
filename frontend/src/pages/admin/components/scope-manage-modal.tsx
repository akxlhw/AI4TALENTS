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
import { formatUTCToLocal } from '../../../utils/datetime'
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
  return (
    <Modal title="权限管理" open={open} onCancel={onCancel} footer={null} width={600}>
      <Tabs
        items={[
          {
            key: 'current',
            label: '当前权限',
            children: (
              <List
                dataSource={userScopes}
                renderItem={scope => (
                  <List.Item
                    actions={[
                      <Popconfirm
                        key="remove"
                        title="确定移除此权限？"
                        onConfirm={() => onRemoveScope(scope.scope_id)}
                        okText="确定"
                        cancelText="取消"
                      >
                        <Button type="link" danger size="small">
                          移除
                        </Button>
                      </Popconfirm>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Tag color={scope.scope_type === 'all' ? 'red' : 'blue'}>
                            {scope.scope_type === 'school'
                              ? '学校'
                              : scope.scope_type === 'country'
                                ? '国家'
                                : scope.scope_type === 'tech_domain'
                                  ? '技术领域'
                                  : '全部'}
                          </Tag>
                          <Text>{scope.scope_value}</Text>
                        </Space>
                      }
                      description={
                        <Text type="secondary">
                          授予于 {formatUTCToLocal(scope.granted_at)}
                          {scope.expires_at && ` | 过期: ${formatUTCToLocal(scope.expires_at)}`}
                        </Text>
                      }
                    />
                  </List.Item>
                )}
                locale={{ emptyText: '暂无权限' }}
              />
            ),
          },
          {
            key: 'add',
            label: '添加权限',
            children: (
              <Form form={form} layout="vertical" onFinish={onAddScope}>
                <Form.Item name="scope_type" label="权限类型" rules={[{ required: true }]}>
                  <Select
                    options={[
                      { value: 'school', label: '学校' },
                      { value: 'country', label: '国家' },
                      { value: 'tech_domain', label: '技术领域' },
                      { value: 'all', label: '全部' },
                    ]}
                  />
                </Form.Item>
                <Form.Item
                  name="scope_value"
                  label="权限值"
                  rules={[{ required: true }]}
                  extra="学校ID、国家代码(如US、CN)、技术领域ID 或 * (全部)"
                >
                  <Input placeholder="如: 1, US, 1, *" />
                </Form.Item>
                <Form.Item name="notes" label="备注">
                  <Input.TextArea rows={2} />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit">
                    添加权限
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
