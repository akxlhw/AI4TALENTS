import { useCallback, useEffect, useState } from 'react'
import { Form, message } from 'antd'
import dayjs from 'dayjs'
import { api } from '../../services/api'
import { useAuth } from '../../contexts/AuthContext'
import UserTableSection from './components/user-table-section'
import UserFormModal from './components/user-form-modal'
import UserDetailDrawer from './components/user-detail-drawer'
import ScopeManageModal from './components/scope-manage-modal'
import { getApiErrorDetail } from './components/types'
import type { ActivityItem, Scope, User } from './components/types'

const AdminPage: React.FC = () => {
  const { isSuperAdmin } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)

  // User modal state
  const [activeTab, setActiveTab] = useState<'all' | 'pending'>('all')
  const [userModalVisible, setUserModalVisible] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [userForm] = Form.useForm()

  // Scope modal state
  const [scopeModalVisible, setScopeModalVisible] = useState(false)
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null)
  const [userScopes, setUserScopes] = useState<Scope[]>([])
  const [scopeForm] = Form.useForm()

  // Filter state
  const [roleFilter, setRoleFilter] = useState<string | undefined>(undefined)
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined)
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null)
  const [sortBy, setSortBy] = useState<string>('created_at')
  const [sortOrder, setSortOrder] = useState<string>('desc')

  // Detail drawer state
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false)
  const [detailUser, setDetailUser] = useState<User | null>(null)
  const [detailTab, setDetailTab] = useState<string>('profile')
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [activitiesLoading, setActivitiesLoading] = useState(false)
  const [activitiesTotal, setActivitiesTotal] = useState(0)
  const [activitiesPage, setActivitiesPage] = useState(1)

  const pageSize = 10

  const loadUsers = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = {
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      }
      if (activeTab === 'pending') {
        params.status = 'pending_approval'
      }
      if (roleFilter) {
        params.role = roleFilter
      }
      if (statusFilter && activeTab !== 'pending') {
        params.status = statusFilter
      }
      if (dateRange && dateRange[0]) {
        params.created_after = dateRange[0].format('YYYY-MM-DDTHH:mm:ss')
      }
      if (dateRange && dateRange[1]) {
        params.created_before = dateRange[1].format('YYYY-MM-DDTHH:mm:ss')
      }
      const response = await api.admin.listUsers(params)
      setUsers(response.data.items)
      setTotal(response.data.total)
    } catch {
      message.error('加载用户列表失败')
    } finally {
      setLoading(false)
    }
  }, [page, activeTab, roleFilter, statusFilter, dateRange, sortBy, sortOrder])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  const handleApproveUser = async (userId: number) => {
    try {
      await api.admin.approveUser(userId)
      message.success('用户已通过')
      loadUsers()
    } catch (error: unknown) {
      message.error(getApiErrorDetail(error) || '操作失败')
    }
  }

  const handleRejectUser = async (userId: number) => {
    try {
      await api.admin.rejectUser(userId)
      message.success('用户已拒绝')
      loadUsers()
    } catch (error: unknown) {
      message.error(getApiErrorDetail(error) || '操作失败')
    }
  }

  const handleCreateUser = () => {
    setEditingUser(null)
    userForm.resetFields()
    setUserModalVisible(true)
  }

  const handleEditUser = (user: User) => {
    setEditingUser(user)
    userForm.setFieldsValue({
      display_name: user.display_name,
      department: user.department,
      role: user.role,
      default_view: user.default_view,
    })
    setUserModalVisible(true)
  }

  const handleSaveUser = async (values: Record<string, unknown>) => {
    try {
      if (editingUser) {
        await api.admin.updateUser(editingUser.user_id, values)
        message.success('用户更新成功')
      } else {
        await api.admin.createUser(values as Parameters<typeof api.admin.createUser>[0])
        message.success('用户创建成功')
      }
      setUserModalVisible(false)
      loadUsers()
    } catch (error: unknown) {
      message.error(getApiErrorDetail(error) || '操作失败')
    }
  }

  const handleDeactivateUser = async (userId: number) => {
    try {
      await api.admin.deactivateUser(userId)
      message.success('用户已禁用')
      loadUsers()
    } catch (error: unknown) {
      message.error(getApiErrorDetail(error) || '操作失败')
    }
  }

  const handleActivateUser = async (userId: number) => {
    try {
      await api.admin.activateUser(userId)
      message.success('用户已启用')
      loadUsers()
    } catch (error: unknown) {
      message.error(getApiErrorDetail(error) || '操作失败')
    }
  }

  const handleManageScopes = async (userId: number) => {
    setSelectedUserId(userId)
    try {
      const response = await api.admin.getUserScopes(userId)
      setUserScopes(response.data.items)
    } catch {
      message.error('加载权限失败')
    }
    setScopeModalVisible(true)
  }

  const handleViewDetail = async (user: User) => {
    setDetailUser(user)
    setDetailDrawerVisible(true)
    setDetailTab('profile')
    setActivitiesPage(1)
    await loadActivities(user.user_id, 1)
  }

  const loadActivities = async (userId: number, pageNum: number) => {
    setActivitiesLoading(true)
    try {
      const response = await api.admin.getUserActivities(userId, {
        page: pageNum,
        page_size: 10,
      })
      setActivities(response.data.items)
      setActivitiesTotal(response.data.total)
      setActivitiesPage(pageNum)
    } catch {
      message.error('加载活动记录失败')
    } finally {
      setActivitiesLoading(false)
    }
  }

  const handleAddScope = async (values: Record<string, unknown>) => {
    if (!selectedUserId) return

    try {
      await api.admin.addUserScope(selectedUserId, {
        ...(values as Omit<Parameters<typeof api.admin.addUserScope>[1], 'user_id'>),
      })
      message.success('权限添加成功')
      scopeForm.resetFields()
      // Reload scopes
      const response = await api.admin.getUserScopes(selectedUserId)
      setUserScopes(response.data.items)
    } catch (error: unknown) {
      message.error(getApiErrorDetail(error) || '添加失败')
    }
  }

  const handleRemoveScope = async (scopeId: number) => {
    if (!selectedUserId) return

    try {
      await api.admin.removeUserScope(selectedUserId, scopeId)
      message.success('权限已移除')
      // Reload scopes
      const response = await api.admin.getUserScopes(selectedUserId)
      setUserScopes(response.data.items)
    } catch (error: unknown) {
      message.error(getApiErrorDetail(error) || '移除失败')
    }
  }

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <UserTableSection
        users={users}
        total={total}
        page={page}
        pageSize={pageSize}
        loading={loading}
        activeTab={activeTab}
        isSuperAdmin={isSuperAdmin}
        roleFilter={roleFilter}
        statusFilter={statusFilter}
        dateRange={dateRange}
        sortBy={sortBy}
        sortOrder={sortOrder}
        onTabChange={key => {
          setActiveTab(key)
          setPage(1)
        }}
        onPageChange={setPage}
        onRoleFilterChange={v => {
          setRoleFilter(v)
          setPage(1)
        }}
        onStatusFilterChange={v => {
          setStatusFilter(v)
          setPage(1)
        }}
        onDateRangeChange={dates => {
          setDateRange(dates)
          setPage(1)
        }}
        onSortByChange={v => {
          setSortBy(v)
          setPage(1)
        }}
        onSortOrderChange={v => {
          setSortOrder(v)
          setPage(1)
        }}
        onCreateUser={handleCreateUser}
        onApproveUser={handleApproveUser}
        onRejectUser={handleRejectUser}
        onViewDetail={handleViewDetail}
        onManageScopes={handleManageScopes}
        onEditUser={handleEditUser}
        onDeactivateUser={handleDeactivateUser}
        onActivateUser={handleActivateUser}
      />

      <UserFormModal
        open={userModalVisible}
        editingUser={editingUser}
        form={userForm}
        isSuperAdmin={isSuperAdmin}
        onCancel={() => setUserModalVisible(false)}
        onSave={handleSaveUser}
      />

      <UserDetailDrawer
        open={detailDrawerVisible}
        user={detailUser}
        activeTab={detailTab}
        activities={activities}
        activitiesLoading={activitiesLoading}
        activitiesTotal={activitiesTotal}
        activitiesPage={activitiesPage}
        userScopes={userScopes}
        onClose={() => setDetailDrawerVisible(false)}
        onTabChange={setDetailTab}
        onActivitiesPageChange={p => {
          if (detailUser) {
            loadActivities(detailUser.user_id, p)
          }
        }}
        onEditUser={handleEditUser}
        onManageScopes={handleManageScopes}
      />

      <ScopeManageModal
        open={scopeModalVisible}
        userScopes={userScopes}
        form={scopeForm}
        onCancel={() => setScopeModalVisible(false)}
        onAddScope={handleAddScope}
        onRemoveScope={handleRemoveScope}
      />
    </div>
  )
}

export default AdminPage
