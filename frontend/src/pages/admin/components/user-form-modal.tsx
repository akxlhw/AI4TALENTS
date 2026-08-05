import { Form, Input, Modal, Select } from 'antd'
import type { FormInstance } from 'antd'
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
  return (
    <Modal
      title={editingUser ? '编辑用户' : '新建用户'}
      open={open}
      onCancel={onCancel}
      onOk={() => form.submit()}
    >
      <Form form={form} layout="vertical" onFinish={onSave}>
        {!editingUser && (
          <>
            <Form.Item
              name="username"
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="email"
              label="邮箱"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              name="password"
              label="密码"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 8, message: '密码至少8位' },
              ]}
            >
              <Input.Password />
            </Form.Item>
          </>
        )}
        <Form.Item name="display_name" label="显示名称">
          <Input />
        </Form.Item>
        <Form.Item name="department" label="部门">
          <Input />
        </Form.Item>
        {isSuperAdmin && (
          <Form.Item name="role" label="角色">
            <Select
              options={[
                { value: 'user', label: '普通用户' },
                { value: 'admin', label: '管理员' },
                { value: 'super_admin', label: '超级管理员' },
              ]}
            />
          </Form.Item>
        )}
        <Form.Item name="default_view" label="默认视角">
          <Select
            options={[
              { value: 'tech_domain', label: '技术领域' },
              { value: 'country_school', label: '国家院校' },
            ]}
          />
        </Form.Item>
      </Form>
    </Modal>
  )
}

export default UserFormModal
