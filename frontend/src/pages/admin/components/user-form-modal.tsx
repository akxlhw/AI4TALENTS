import { Form, Input, Modal, Select } from 'antd'
import type { FormInstance } from 'antd'
import { useTranslation } from 'react-i18next'
import '../../../i18n/namespaces/admin'
import type { User } from './types'

interface UserFormModalProps {
  open: boolean
  editingUser: User | null
  form: FormInstance
  isSuperAdmin: boolean
  onCancel: () => void
  onSave: (values: Record<string, unknown>) => void
}

const UserFormModal: React.FC<UserFormModalProps> = ({
  open,
  editingUser,
  form,
  isSuperAdmin,
  onCancel,
  onSave,
}) => {
  const { t } = useTranslation(['admin', 'common'])
  return (
    <Modal
      title={editingUser ? t('users.form.editTitle') : t('users.form.createTitle')}
      open={open}
      onCancel={onCancel}
      onOk={() => form.submit()}
    >
      <Form form={form} layout="vertical" onFinish={onSave}>
        {!editingUser && (
          <>
            <Form.Item
              name="username"
              label={t('users.form.username')}
              rules={[{ required: true, message: t('users.form.usernameRequired') }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="email"
              label={t('users.form.email')}
              rules={[
                { required: true, message: t('users.form.emailRequired') },
                { type: 'email', message: t('users.form.emailInvalid') },
              ]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="password"
              label={t('users.form.password')}
              rules={[
                { required: true, message: t('users.form.passwordRequired') },
                { min: 8, message: t('users.form.passwordMin') },
              ]}
            >
              <Input.Password />
            </Form.Item>
          </>
        )}
        <Form.Item name="display_name" label={t('users.form.displayName')}>
          <Input />
        </Form.Item>
        <Form.Item name="department" label={t('users.form.department')}>
          <Input />
        </Form.Item>
        {isSuperAdmin && (
          <Form.Item name="role" label={t('users.form.role')}>
            <Select
              options={[
                { value: 'user', label: t('users.roles.user') },
                { value: 'admin', label: t('users.roles.admin') },
                { value: 'super_admin', label: t('users.roles.super_admin') },
              ]}
            />
          </Form.Item>
        )}
        <Form.Item name="default_view" label={t('users.form.defaultView')}>
          <Select
            options={[
              { value: 'tech_domain', label: t('users.views.tech_domain') },
              { value: 'country_school', label: t('users.views.country_school') },
            ]}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}

export default UserFormModal
