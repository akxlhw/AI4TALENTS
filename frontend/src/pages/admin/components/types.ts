export interface User {
  user_id: number
  username: string
  email: string
  role: string
  display_name: string | null
  department: string | null
  is_active: boolean
  status: string
  employee_id: string | null
  default_view: string
  last_login_at: string | null
  created_at: string | null
}

export interface ActivityItem {
  activity_id: number
  activity_time: string
  activity_type: string
  actor: { user_id: number; username: string } | null
  target_user_id: number
  description: string
  detail: Record<string, unknown>
  ip: string | null
  status: string
}

export interface Scope {
  scope_id: number
  user_id: number
  scope_type: string
  scope_value: string
  granted_by: number
  granted_at: string
  expires_at: string | null
  is_active: boolean
  notes: string | null
}

export const roleColorMap: Record<string, string> = {
  super_admin: 'red',
  admin: 'orange',
  user: 'blue',
}

export const roleTextMap: Record<string, string> = {
  super_admin: '超级管理员',
  admin: '管理员',
  user: '普通用户',
}

export const statusColorMap: Record<string, string> = {
  pending_approval: 'orange',
  active: 'green',
  inactive: 'red',
  rejected: 'default',
}

export const statusTextMap: Record<string, string> = {
  pending_approval: '待审核',
  active: '正常',
  inactive: '已禁用',
  rejected: '已拒绝',
}

export const activityTypeColorMap: Record<string, string> = {
  login: 'blue',
  login_failure: 'red',
  profile_update: 'orange',
  role_change: 'purple',
  account_activated: 'green',
  account_deactivated: 'red',
  account_created: 'cyan',
  account_approved: 'green',
  account_rejected: 'red',
  scope_grant: 'geekblue',
  scope_revoke: 'magenta',
  password_change: 'gold',
  other: 'default',
}

export const activityTypeTextMap: Record<string, string> = {
  login: '登录',
  login_failure: '登录失败',
  profile_update: '信息更新',
  role_change: '角色变更',
  account_activated: '账号启用',
  account_deactivated: '账号禁用',
  account_created: '账号创建',
  account_approved: '注册通过',
  account_rejected: '注册拒绝',
  scope_grant: '权限授予',
  scope_revoke: '权限移除',
  password_change: '密码重置',
  other: '其他',
}

/** 从 Axios 风格的错误对象中提取后端返回的 detail 文案 */
export function getApiErrorDetail(error: unknown): string | undefined {
  return error instanceof Error && 'response' in error
    ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
    : undefined
}
