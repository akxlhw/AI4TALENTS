import { useCallback, useEffect, useState } from 'react'
import { Card, Table, Tag, Space, DatePicker, Select, Button } from 'antd'
import { FileTextOutlined, ReloadOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import { formatUTCToLocal } from '../../utils/datetime'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker

interface AuditLog {
  log_id: number
  event_time: string
  user_id: number | null
  user_ip: string | null
  event_type: string
  event_subtype: string | null
  resource_type: string | null
  resource_id: string | null
  operation: string
  status: string
  error_message: string | null
}

interface UserMapItem {
  username: string
  employee_id: string | null
}

const EVENT_TYPE_MAP: Record<string, string> = {
  authentication: '认证',
  authorization: '权限',
  data_operation: '数据',
}

const OPERATION_MAP: Record<string, string> = {
  login: '登录',
  logout: '登出',
  register: '注册',
  change_password: '修改密码',
  create: '创建用户',
  update: '更新用户',
  deactivate: '禁用用户',
  approve: '审批通过',
  reject: '审批拒绝',
  grant_scope: '授予权限',
  revoke_scope: '移除权限',
}

const STATUS_COLOR_MAP: Record<string, string> = {
  success: 'green',
  failure: 'red',
  partial: 'orange',
}

const STATUS_TEXT_MAP: Record<string, string> = {
  success: '成功',
  failure: '失败',
  partial: '部分',
}

const AuditLogPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [userMap, setUserMap] = useState<Map<number, UserMapItem>>(new Map())
  const [filters, setFilters] = useState({
    event_type: undefined as string | undefined,
    date_range: undefined as [dayjs.Dayjs, dayjs.Dayjs] | undefined,
  })

  const pageSize = 20

  const loadUserMap = useCallback(async () => {
    try {
      const response = await api.admin.listUsers({ page: 1, page_size: 100 })
      const map = new Map<number, UserMapItem>()
      for (const u of response.data.items) {
        map.set(u.user_id, { username: u.username, employee_id: u.employee_id })
      }
      setUserMap(map)
    } catch {
      // ignore
    }
  }, [])

  const loadLogs = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize }
      if (filters.event_type) params.event_type = filters.event_type
      if (filters.date_range) {
        params.start_time = filters.date_range[0].toISOString()
        params.end_time = filters.date_range[1].toISOString()
      }
      const response = await api.admin.listAuditLogs(params)
      setLogs(response.data.items)
      setTotal(response.data.total)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [page, filters])

  useEffect(() => {
    loadUserMap()
  }, [loadUserMap])

  useEffect(() => {
    loadLogs()
  }, [loadLogs])

  const formatEvent = (eventType: string, operation: string) => {
    const typeLabel = EVENT_TYPE_MAP[eventType] || eventType
    const opLabel = OPERATION_MAP[operation] || operation
    return `${typeLabel} · ${opLabel}`
  }

  const formatOperator = (userId: number | null) => {
    if (!userId) return '系统'
    const user = userMap.get(userId)
    if (!user) return `用户#${userId}`
    if (user.employee_id) {
      return `${user.username} (${user.employee_id})`
    }
    return user.username
  }

  const columns = [
    {
      title: '时间',
      dataIndex: 'event_time',
      key: 'event_time',
      width: 170,
      render: (date: string) => formatUTCToLocal(date),
    },
    {
      title: '操作人',
      dataIndex: 'user_id',
      key: 'user_id',
      width: 180,
      render: (id: number | null) => formatOperator(id),
    },
    {
      title: '事件',
      key: 'event',
      width: 160,
      render: (_: unknown, record: AuditLog) => (
        <Tag color={record.event_type === 'authentication' ? 'blue' : record.event_type === 'authorization' ? 'orange' : 'green'}>
          {formatEvent(record.event_type, record.operation)}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => (
        <Tag color={STATUS_COLOR_MAP[status] || 'default'}>
          {STATUS_TEXT_MAP[status] || status}
        </Tag>
      ),
    },
    {
      title: 'IP',
      dataIndex: 'user_ip',
      key: 'user_ip',
      width: 130,
      render: (ip: string | null) => ip || '-',
    },
    {
      title: '备注',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
      render: (msg: string | null) => msg || '-',
    },
  ]

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>审计日志</span>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder="事件类型"
            allowClear
            style={{ width: 140 }}
            value={filters.event_type}
            onChange={(val) => setFilters((f) => ({ ...f, event_type: val }))}
            options={[
              { value: 'authentication', label: '认证' },
              { value: 'authorization', label: '权限' },
              { value: 'data_operation', label: '数据' },
            ]}
          />
          <RangePicker
            showTime
            value={filters.date_range}
            onChange={(val) =>
              setFilters((f) => ({ ...f, date_range: val as [dayjs.Dayjs, dayjs.Dayjs] | undefined }))
            }
          />
          <Button icon={<ReloadOutlined />} onClick={loadLogs}>
            刷新
          </Button>
        </Space>

        <Table
          dataSource={logs}
          columns={columns}
          rowKey="log_id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 条记录`,
          }}
          onChange={(pagination) => setPage(pagination.current || 1)}
        />
      </Card>
    </div>
  )
}

export default AuditLogPage
