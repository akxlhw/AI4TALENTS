import { useCallback, useEffect, useState } from 'react'
import { Card, Table, Tag, Space, DatePicker, Select, Button } from 'antd'
import { FileTextOutlined, ReloadOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { api } from '../../services/api'
import { formatUTCToLocal } from '../../utils/datetime'
import '../../i18n/namespaces/admin'
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
  operation_detail?: Record<string, unknown>
}

interface UserMapItem {
  username: string
  employee_id: string | null
}

const STATUS_COLOR_MAP: Record<string, string> = {
  success: 'green',
  failure: 'red',
  partial: 'orange',
}

const AuditLogPage: React.FC = () => {
  const { t } = useTranslation(['admin', 'common'])
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

  const formatEvent = (record: AuditLog) => {
    const typeLabel = t(`audit.eventTypes.${record.event_type}`, {
      defaultValue: record.event_type,
    })
    const opLabel = t(`audit.operations.${record.operation}`, {
      defaultValue: record.operation,
    })
    const resourceLabel =
      record.resource_type === 'talent' || record.resource_type === 'os_developer'
        ? t(`audit.resources.${record.resource_type}`)
        : ''
    const base = t('audit.eventPlain', {
      type: typeLabel,
      operation: opLabel,
      resource: resourceLabel,
    })
    if (
      record.event_type === 'data_operation' &&
      record.operation === 'export' &&
      record.operation_detail
    ) {
      const count = record.operation_detail.count as number | undefined
      const fmt = record.operation_detail.format as string | undefined
      const countText = fmt
        ? t('audit.exportCountFormat', { count: count || '?', format: fmt })
        : t('audit.exportCountPlain', { count: count || '?' })
      return `${base} ${countText}`
    }
    return base
  }

  const formatOperator = (userId: number | null) => {
    if (!userId) return t('audit.system')
    const user = userMap.get(userId)
    if (!user) return t('audit.userNo', { id: userId })
    if (user.employee_id) {
      return `${user.username} (${user.employee_id})`
    }
    return user.username
  }

  const columns = [
    {
      title: t('audit.columns.time'),
      dataIndex: 'event_time',
      key: 'event_time',
      width: 170,
      render: (date: string) => formatUTCToLocal(date),
    },
    {
      title: t('audit.columns.operator'),
      dataIndex: 'user_id',
      key: 'user_id',
      width: 180,
      render: (id: number | null) => formatOperator(id),
    },
    {
      title: t('audit.columns.event'),
      key: 'event',
      width: 200,
      render: (_: unknown, record: AuditLog) => (
        <Tag
          color={
            record.event_type === 'authentication'
              ? 'blue'
              : record.event_type === 'authorization'
                ? 'orange'
                : 'green'
          }
        >
          {formatEvent(record)}
        </Tag>
      ),
    },
    {
      title: t('audit.columns.status'),
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (status: string) => (
        <Tag color={STATUS_COLOR_MAP[status] || 'default'}>
          {t(`audit.statuses.${status}`, { defaultValue: status })}
        </Tag>
      ),
    },
    {
      title: t('audit.columns.ip'),
      dataIndex: 'user_ip',
      key: 'user_ip',
      width: 130,
      render: (ip: string | null) => ip || '-',
    },
    {
      title: t('audit.columns.detail'),
      key: 'detail',
      ellipsis: true,
      render: (_: unknown, record: AuditLog) => {
        if (record.error_message) {
          return <span style={{ color: '#ff4d4f' }}>{record.error_message}</span>
        }
        if (record.operation_detail) {
          const detail = record.operation_detail
          if (detail.count !== undefined) {
            const count = detail.count as number
            const fmt = detail.format as string | undefined
            return fmt
              ? t('audit.exportDetailFormat', { count, format: fmt })
              : t('audit.exportDetail', { count })
          }
          return JSON.stringify(detail).slice(0, 60)
        }
        return '-'
      },
    },
  ]

  return (
    <div style={{ padding: '88px 32px 80px' }}>
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>{t('audit.title')}</span>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder={t('audit.filter.eventType')}
            allowClear
            style={{ width: 140 }}
            value={filters.event_type}
            onChange={val => setFilters(f => ({ ...f, event_type: val }))}
            options={[
              { value: 'authentication', label: t('audit.eventTypes.authentication') },
              { value: 'authorization', label: t('audit.eventTypes.authorization') },
              { value: 'data_operation', label: t('audit.eventTypes.data_operation') },
            ]}
          />
          <RangePicker
            showTime
            value={filters.date_range}
            onChange={val =>
              setFilters(f => ({ ...f, date_range: val as [dayjs.Dayjs, dayjs.Dayjs] | undefined }))
            }
          />
          <Button icon={<ReloadOutlined />} onClick={loadLogs}>
            {t('actions.refresh')}
          </Button>
        </Space>

        <Table
          dataSource={logs}
          columns={columns}
          rowKey="log_id"
          loading={loading}
          expandable={{
            expandedRowRender: (record: AuditLog) => {
              if (!record.operation_detail && !record.error_message) {
                return null
              }
              return (
                <div style={{ padding: '8px 16px' }}>
                  {record.error_message && (
                    <div style={{ color: '#ff4d4f', marginBottom: 8 }}>
                      <strong>{t('audit.errorMessage')}</strong>
                      {record.error_message}
                    </div>
                  )}
                  {record.operation_detail && (
                    <pre
                      style={{
                        background: '#f6f6f6',
                        padding: 12,
                        borderRadius: 4,
                        margin: 0,
                        fontSize: 12,
                      }}
                    >
                      {JSON.stringify(record.operation_detail, null, 2)}
                    </pre>
                  )}
                </div>
              )
            },
            rowExpandable: (record: AuditLog) =>
              !!record.operation_detail || !!record.error_message,
          }}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: false,
            showTotal: records => t('audit.totalRecords', { n: records }),
          }}
          onChange={pagination => setPage(pagination.current || 1)}
        />
      </Card>
    </div>
  )
}

export default AuditLogPage
