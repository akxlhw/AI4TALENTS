import { useEffect, useState } from 'react'
import {
  Card,
  Table,
  Typography,
  Tag,
  Space,
  Button,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Badge,
  Tabs,
  Progress,
  Descriptions,
  Tooltip,
} from 'antd'
import {
  SettingOutlined,
  ThunderboltOutlined,
  ScheduleOutlined,
  PlusOutlined,
  PlayCircleOutlined,
  StopOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'

const { Text, Title } = Typography

// Types
interface CollectScope {
  scope_id: number
  scope_code: string
  scope_name: string
  scope_type: string
  scope_value: any[]
  is_enabled: boolean
  description: string | null
  created_by: number | null
  created_at: string
}

interface CollectStrategy {
  strategy_id: number
  strategy_code: string
  strategy_name: string
  strategy_type: string
  schedule_cron: string | null
  scope_ids: number[] | null
  data_types: string[]
  fetch_config: any
  is_enabled: boolean
  description: string | null
  created_by: number | null
  last_run_at: string | null
  last_run_status: string | null
  created_at: string
}

interface CollectTask {
  task_id: number
  task_code: string
  strategy_id: number | null
  task_type: string
  triggered_by: number | null
  triggered_at: string
  status: string
  progress_percent: number
  current_step: string | null
  total_records: number
  processed_records: number
  success_records: number
  failed_records: number
  skipped_records: number
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  error_details: any
  result_summary: any
  created_at: string
}

// Option mappings
const scopeTypeMap: Record<string, { label: string; color: string }> = {
  tech_element: { label: '技术要素', color: 'blue' },
  country: { label: '国家', color: 'green' },
  school: { label: '学校', color: 'orange' },
  custom: { label: '自定义', color: 'purple' },
}

const strategyTypeMap: Record<string, { label: string; color: string }> = {
  scheduled: { label: '定时任务', color: 'blue' },
  manual: { label: '手动触发', color: 'green' },
  event_triggered: { label: '事件触发', color: 'orange' },
}

const taskStatusMap: Record<string, { label: string; color: string; status: 'success' | 'processing' | 'error' | 'default' | 'warning' }> = {
  pending: { label: '待执行', color: 'default', status: 'default' },
  running: { label: '执行中', color: 'processing', status: 'processing' },
  completed: { label: '已完成', color: 'success', status: 'success' },
  failed: { label: '失败', color: 'error', status: 'error' },
  cancelled: { label: '已取消', color: 'warning', status: 'warning' },
}

const CollectPage: React.FC = () => {
  // Scope state
  const [scopes, setScopes] = useState<CollectScope[]>([])
  const [scopeModalVisible, setScopeModalVisible] = useState(false)
  const [editingScope, setEditingScope] = useState<CollectScope | null>(null)
  const [scopeForm] = Form.useForm()

  // Strategy state
  const [strategies, setStrategies] = useState<CollectStrategy[]>([])
  const [strategyModalVisible, setStrategyModalVisible] = useState(false)
  const [editingStrategy, setEditingStrategy] = useState<CollectStrategy | null>(null)
  const [strategyForm] = Form.useForm()

  // Task state
  const [tasks, setTasks] = useState<CollectTask[]>([])
  const [taskTotal, setTaskTotal] = useState(0)
  const [taskPage, setTaskPage] = useState(1)
  const [taskDetailVisible, setTaskDetailVisible] = useState(false)
  const [selectedTask, setSelectedTask] = useState<CollectTask | null>(null)

  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadAll()
  }, [])

  const loadAll = async () => {
    setLoading(true)
    try {
      await Promise.all([loadScopes(), loadStrategies(), loadTasks()])
    } finally {
      setLoading(false)
    }
  }

  // Scope operations
  const loadScopes = async () => {
    try {
      const response = await api.collect.listScopes()
      setScopes(response.data.items)
    } catch (error) {
      message.error('加载采集范围失败')
    }
  }

  const handleCreateScope = () => {
    setEditingScope(null)
    scopeForm.resetFields()
    setScopeModalVisible(true)
  }

  const handleEditScope = (scope: CollectScope) => {
    setEditingScope(scope)
    scopeForm.setFieldsValue({
      scope_code: scope.scope_code,
      scope_name: scope.scope_name,
      scope_type: scope.scope_type,
      scope_value: JSON.stringify(scope.scope_value),
      description: scope.description,
    })
    setScopeModalVisible(true)
  }

  const handleSaveScope = async (values: any) => {
    try {
      const scopeValue = typeof values.scope_value === 'string'
        ? JSON.parse(values.scope_value)
        : values.scope_value

      if (editingScope) {
        await api.collect.updateScope(editingScope.scope_id, {
          scope_name: values.scope_name,
          scope_value: scopeValue,
          description: values.description,
        })
        message.success('采集范围更新成功')
      } else {
        await api.collect.createScope({
          scope_code: values.scope_code,
          scope_name: values.scope_name,
          scope_type: values.scope_type,
          scope_value: scopeValue,
          description: values.description,
        })
        message.success('采集范围创建成功')
      }
      setScopeModalVisible(false)
      loadScopes()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const handleDeleteScope = async (scopeId: number) => {
    try {
      await api.collect.deleteScope(scopeId)
      message.success('采集范围已删除')
      loadScopes()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  // Strategy operations
  const loadStrategies = async () => {
    try {
      const response = await api.collect.listStrategies()
      setStrategies(response.data.items)
    } catch (error) {
      message.error('加载采集策略失败')
    }
  }

  const handleCreateStrategy = () => {
    setEditingStrategy(null)
    strategyForm.resetFields()
    setStrategyModalVisible(true)
  }

  const handleEditStrategy = (strategy: CollectStrategy) => {
    setEditingStrategy(strategy)
    strategyForm.setFieldsValue({
      strategy_code: strategy.strategy_code,
      strategy_name: strategy.strategy_name,
      strategy_type: strategy.strategy_type,
      data_types: strategy.data_types,
      scope_ids: strategy.scope_ids,
      schedule_cron: strategy.schedule_cron,
      description: strategy.description,
    })
    setStrategyModalVisible(true)
  }

  const handleSaveStrategy = async (values: any) => {
    try {
      if (editingStrategy) {
        await api.collect.updateStrategy(editingStrategy.strategy_id, {
          strategy_name: values.strategy_name,
          data_types: values.data_types,
          scope_ids: values.scope_ids,
          schedule_cron: values.schedule_cron,
          description: values.description,
        })
        message.success('采集策略更新成功')
      } else {
        await api.collect.createStrategy({
          strategy_code: values.strategy_code,
          strategy_name: values.strategy_name,
          strategy_type: values.strategy_type,
          data_types: values.data_types,
          scope_ids: values.scope_ids,
          schedule_cron: values.schedule_cron,
          description: values.description,
        })
        message.success('采集策略创建成功')
      }
      setStrategyModalVisible(false)
      loadStrategies()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '操作失败')
    }
  }

  const handleDeleteStrategy = async (strategyId: number) => {
    try {
      await api.collect.deleteStrategy(strategyId)
      message.success('采集策略已删除')
      loadStrategies()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '删除失败')
    }
  }

  // Task operations
  const loadTasks = async () => {
    try {
      const response = await api.collect.listTasks({ page: taskPage, page_size: 10 })
      setTasks(response.data.items)
      setTaskTotal(response.data.total)
    } catch (error) {
      message.error('加载采集任务失败')
    }
  }

  const handleTriggerTask = async (strategyId?: number) => {
    try {
      await api.collect.triggerTask({ strategy_id: strategyId, task_type: 'manual' })
      message.success('任务已触发')
      loadTasks()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '触发失败')
    }
  }

  const handleCancelTask = async (taskId: number) => {
    try {
      await api.collect.cancelTask(taskId)
      message.success('任务已取消')
      loadTasks()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '取消失败')
    }
  }

  const handleViewTask = (task: CollectTask) => {
    setSelectedTask(task)
    setTaskDetailVisible(true)
  }

  // Scope columns
  const scopeColumns = [
    {
      title: '范围编码',
      dataIndex: 'scope_code',
      key: 'scope_code',
      width: 150,
    },
    {
      title: '范围名称',
      dataIndex: 'scope_name',
      key: 'scope_name',
    },
    {
      title: '类型',
      dataIndex: 'scope_type',
      key: 'scope_type',
      render: (type: string) => {
        const item = scopeTypeMap[type] || { label: type, color: 'default' }
        return <Tag color={item.color}>{item.label}</Tag>
      },
    },
    {
      title: '范围值',
      dataIndex: 'scope_value',
      key: 'scope_value',
      ellipsis: true,
      render: (value: any[]) => (
        <Tooltip title={JSON.stringify(value)}>
          <Text code>{Array.isArray(value) ? `${value.length} 项` : JSON.stringify(value)}</Text>
        </Tooltip>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      render: (enabled: boolean) => (
        <Badge status={enabled ? 'success' : 'error'} text={enabled ? '启用' : '禁用'} />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: any, record: CollectScope) => (
        <Space>
          <Button type="link" size="small" onClick={() => handleEditScope(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确定删除此采集范围？"
            onConfirm={() => handleDeleteScope(record.scope_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // Strategy columns
  const strategyColumns = [
    {
      title: '策略编码',
      dataIndex: 'strategy_code',
      key: 'strategy_code',
      width: 150,
    },
    {
      title: '策略名称',
      dataIndex: 'strategy_name',
      key: 'strategy_name',
    },
    {
      title: '类型',
      dataIndex: 'strategy_type',
      key: 'strategy_type',
      render: (type: string) => {
        const item = strategyTypeMap[type] || { label: type, color: 'default' }
        return <Tag color={item.color}>{item.label}</Tag>
      },
    },
    {
      title: '数据类型',
      dataIndex: 'data_types',
      key: 'data_types',
      render: (types: string[]) => (
        <Space size={4}>
          {types.map((t) => (
            <Tag key={t}>{t}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      render: (enabled: boolean) => (
        <Badge status={enabled ? 'success' : 'error'} text={enabled ? '启用' : '禁用'} />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: any, record: CollectStrategy) => (
        <Space>
          <Tooltip title="执行任务">
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleTriggerTask(record.strategy_id)}
            />
          </Tooltip>
          <Button type="link" size="small" onClick={() => handleEditStrategy(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确定删除此采集策略？"
            onConfirm={() => handleDeleteStrategy(record.strategy_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // Task columns
  const taskColumns = [
    {
      title: '任务编码',
      dataIndex: 'task_code',
      key: 'task_code',
      width: 200,
    },
    {
      title: '类型',
      dataIndex: 'task_type',
      key: 'task_type',
      render: (type: string) => {
        const item = strategyTypeMap[type] || { label: type, color: 'default' }
        return <Tag color={item.color}>{item.label}</Tag>
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const item = taskStatusMap[status] || { label: status, color: 'default', status: 'default' as const }
        return <Badge status={item.status} text={item.label} />
      },
    },
    {
      title: '进度',
      dataIndex: 'progress_percent',
      key: 'progress_percent',
      width: 150,
      render: (percent: number, record: CollectTask) => (
        <Progress
          percent={percent}
          size="small"
          status={record.status === 'failed' ? 'exception' : record.status === 'completed' ? 'success' : 'active'}
        />
      ),
    },
    {
      title: '记录数',
      key: 'records',
      render: (_: any, record: CollectTask) => (
        <Text>
          {record.success_records}/{record.total_records}
          {record.failed_records > 0 && <Text type="danger"> ({record.failed_records} 失败)</Text>}
        </Text>
      ),
    },
    {
      title: '触发时间',
      dataIndex: 'triggered_at',
      key: 'triggered_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: CollectTask) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewTask(record)}
            />
          </Tooltip>
          {record.status === 'running' && (
            <Popconfirm
              title="确定取消此任务？"
              onConfirm={() => handleCancelTask(record.task_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" size="small" danger icon={<StopOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>采集配置管理</Title>

      <Tabs
        items={[
          {
            key: 'scopes',
            label: (
              <span>
                <SettingOutlined />
                采集范围
              </span>
            ),
            children: (
              <Card
                extra={
                  <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateScope}>
                    新建范围
                  </Button>
                }
              >
                <Table
                  dataSource={scopes}
                  columns={scopeColumns}
                  rowKey="scope_id"
                  loading={loading}
                  pagination={false}
                />
              </Card>
            ),
          },
          {
            key: 'strategies',
            label: (
              <span>
                <ScheduleOutlined />
                采集策略
              </span>
            ),
            children: (
              <Card
                extra={
                  <Space>
                    <Button icon={<PlayCircleOutlined />} onClick={() => handleTriggerTask()}>
                      手动触发
                    </Button>
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateStrategy}>
                      新建策略
                    </Button>
                  </Space>
                }
              >
                <Table
                  dataSource={strategies}
                  columns={strategyColumns}
                  rowKey="strategy_id"
                  loading={loading}
                  pagination={false}
                />
              </Card>
            ),
          },
          {
            key: 'tasks',
            label: (
              <span>
                <ThunderboltOutlined />
                采集任务
              </span>
            ),
            children: (
              <Card>
                <Table
                  dataSource={tasks}
                  columns={taskColumns}
                  rowKey="task_id"
                  loading={loading}
                  pagination={{
                    current: taskPage,
                    pageSize: 10,
                    total: taskTotal,
                    showTotal: (t) => `共 ${t} 个任务`,
                    onChange: (p) => setTaskPage(p),
                  }}
                />
              </Card>
            ),
          },
        ]}
      />

      {/* Scope Modal */}
      <Modal
        title={editingScope ? '编辑采集范围' : '新建采集范围'}
        open={scopeModalVisible}
        onCancel={() => setScopeModalVisible(false)}
        onOk={() => scopeForm.submit()}
      >
        <Form form={scopeForm} layout="vertical" onFinish={handleSaveScope}>
          <Form.Item
            name="scope_code"
            label="范围编码"
            rules={[{ required: true }]}
          >
            <Input disabled={!!editingScope} placeholder="如: SCOPE_AI_001" />
          </Form.Item>
          <Form.Item
            name="scope_name"
            label="范围名称"
            rules={[{ required: true }]}
          >
            <Input placeholder="如: 人工智能相关学校" />
          </Form.Item>
          <Form.Item
            name="scope_type"
            label="范围类型"
            rules={[{ required: true }]}
          >
            <Select
              disabled={!!editingScope}
              options={[
                { value: 'tech_element', label: '技术要素' },
                { value: 'country', label: '国家' },
                { value: 'school', label: '学校' },
                { value: 'custom', label: '自定义' },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="scope_value"
            label="范围值 (JSON数组)"
            rules={[{ required: true }]}
            extra='如: [1, 2, 3] 或 ["US", "CN"]'
          >
            <Input.TextArea rows={3} placeholder='[1, 2, 3]' />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Strategy Modal */}
      <Modal
        title={editingStrategy ? '编辑采集策略' : '新建采集策略'}
        open={strategyModalVisible}
        onCancel={() => setStrategyModalVisible(false)}
        onOk={() => strategyForm.submit()}
        width={600}
      >
        <Form form={strategyForm} layout="vertical" onFinish={handleSaveStrategy}>
          <Form.Item
            name="strategy_code"
            label="策略编码"
            rules={[{ required: true }]}
          >
            <Input disabled={!!editingStrategy} placeholder="如: STRATEGY_WEEKLY" />
          </Form.Item>
          <Form.Item
            name="strategy_name"
            label="策略名称"
            rules={[{ required: true }]}
          >
            <Input placeholder="如: 每周全量采集" />
          </Form.Item>
          <Form.Item
            name="strategy_type"
            label="策略类型"
            rules={[{ required: true }]}
          >
            <Select
              disabled={!!editingStrategy}
              options={[
                { value: 'manual', label: '手动触发' },
                { value: 'scheduled', label: '定时任务' },
                { value: 'event_triggered', label: '事件触发' },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="data_types"
            label="数据类型"
            rules={[{ required: true }]}
          >
            <Select
              mode="multiple"
              options={[
                { value: 'authors', label: '学者数据' },
                { value: 'works', label: '论文数据' },
                { value: 'institutions', label: '机构数据' },
              ]}
            />
          </Form.Item>
          <Form.Item name="schedule_cron" label="Cron表达式">
            <Input placeholder="如: 0 0 * * 0 (每周日凌晨)" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Task Detail Modal */}
      <Modal
        title="任务详情"
        open={taskDetailVisible}
        onCancel={() => setTaskDetailVisible(false)}
        footer={null}
        width={700}
      >
        {selectedTask && (
          <Descriptions bordered column={2}>
            <Descriptions.Item label="任务编码">{selectedTask.task_code}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Badge
                status={taskStatusMap[selectedTask.status]?.status}
                text={taskStatusMap[selectedTask.status]?.label}
              />
            </Descriptions.Item>
            <Descriptions.Item label="任务类型">
              {strategyTypeMap[selectedTask.task_type]?.label}
            </Descriptions.Item>
            <Descriptions.Item label="进度">
              <Progress percent={selectedTask.progress_percent} />
            </Descriptions.Item>
            <Descriptions.Item label="总记录数">{selectedTask.total_records}</Descriptions.Item>
            <Descriptions.Item label="已处理">{selectedTask.processed_records}</Descriptions.Item>
            <Descriptions.Item label="成功">{selectedTask.success_records}</Descriptions.Item>
            <Descriptions.Item label="失败">{selectedTask.failed_records}</Descriptions.Item>
            <Descriptions.Item label="触发时间">
              {new Date(selectedTask.triggered_at).toLocaleString()}
            </Descriptions.Item>
            <Descriptions.Item label="开始时间">
              {selectedTask.started_at ? new Date(selectedTask.started_at).toLocaleString() : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="完成时间">
              {selectedTask.completed_at ? new Date(selectedTask.completed_at).toLocaleString() : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="当前步骤">{selectedTask.current_step || '-'}</Descriptions.Item>
            {selectedTask.error_message && (
              <Descriptions.Item label="错误信息" span={2}>
                <Text type="danger">{selectedTask.error_message}</Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

export default CollectPage
