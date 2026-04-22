/**
 * 采集配置管理页面 - MVP v1.2
 *
 * 功能说明：
 * - 技术领域配置：管理技术领域关联的顶会顶刊
 * - 采集任务：基于技术领域触发采集，可配置年份范围
 * - 固定参数：数据类型（学者+论文+机构）
 * - 可配置参数：时间范围（起始年份~截止年份/至今）
 */
import { useEffect, useState, useRef } from 'react'
import {
  Card,
  Table,
  Typography,
  Tag,
  Space,
  Button,
  Modal,
  message,
  Popconfirm,
  Badge,
  Tabs,
  Progress,
  Descriptions,
  Tooltip,
  Empty,
  Spin,
  Select,
  Timeline,
  Alert,
  Transfer,
  Row,
  Col,
  Statistic,
} from 'antd'
import {
  SettingOutlined,
  ThunderboltOutlined,
  PlayCircleOutlined,
  StopOutlined,
  EyeOutlined,
  DeleteOutlined,
  ReloadOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  TeamOutlined,
  SyncOutlined,
} from '@ant-design/icons'
import { api } from '../services/api'
import { queryClient, queryKeys } from '../hooks/queryClient'
import {
  getTaskStatusConfig,
  getVenueTypeConfig,
  getStartYearOptions,
  getEndYearOptions,
  TIME_RANGE_CONFIG,
} from '../constants'
import type { VenueItem, VenueBinding, TechDomainCollect, CollectTask } from '../types'
import { formatUTCToLocal } from '../utils/datetime'
import { formatNumber } from '../utils/format'

const { Text, Title } = Typography

// Error message extractor helper
const getErrorMessage = (error: unknown, defaultMsg: string): string => {
  if (error && typeof error === 'object' && 'response' in error) {
    const axiosError = error as { response?: { data?: { detail?: string } }; message?: string }
    if (axiosError.response?.data?.detail) {
      const detail = axiosError.response.data.detail
      return typeof detail === 'string' ? detail : JSON.stringify(detail)
    }
    if (axiosError.message) {
      return axiosError.message
    }
  }
  return defaultMsg
}

const CollectPage: React.FC = () => {
  // Tech Domains state
  const [techDomains, setTechDomains] = useState<TechDomainCollect[]>([])
  const [venueModalVisible, setVenueModalVisible] = useState(false)
  const [collectModalVisible, setCollectModalVisible] = useState(false)
  const [selectedDomain, setSelectedDomain] = useState<TechDomainCollect | null>(null)

  // Time range state
  const [startYear, setStartYear] = useState<number>(TIME_RANGE_CONFIG.DEFAULT_START_YEAR)
  const [endYear, setEndYear] = useState<number | null>(null)  // null = 至今

  // Venue selection state
  const [allVenues, setAllVenues] = useState<VenueItem[]>([])
  const [selectedVenueIds, setSelectedVenueIds] = useState<string[]>([])
  const [venueLoading, setVenueLoading] = useState(false)

  // Task state
  const [tasks, setTasks] = useState<CollectTask[]>([])
  const [taskTotal, setTaskTotal] = useState(0)
  const [taskPage, setTaskPage] = useState(1)
  const [taskDetailVisible, setTaskDetailVisible] = useState(false)
  const [selectedTask, setSelectedTask] = useState<CollectTask | null>(null)

  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('tech-domains')

  // Track running task IDs to detect completion
  const runningTaskIdsRef = useRef<Set<number>>(new Set())

  // Collaboration sync state
  const [collabSyncStatus, setCollabSyncStatus] = useState<{
    status: string
    processed: number
    total: number
    collaborations: number
  } | null>(null)
  const [collabDataStatus, setCollabDataStatus] = useState<{
    total_collaborations: number
    talents_with_collaborations: number
    last_sync: string | null
  } | null>(null)
  const [collabSyncLoading, setCollabSyncLoading] = useState(false)

  useEffect(() => {
    if (activeTab === 'tech-domains') {
      loadTechDomains()
    } else if (activeTab === 'tasks') {
      loadTasks()
    } else if (activeTab === 'collaborations') {
      loadCollabSyncStatus()
    }
  }, [activeTab])

  // Auto-refresh for running tasks
  useEffect(() => {
    if (activeTab === 'tasks' && tasks.some(t => t.status === 'running')) {
      const interval = setInterval(() => {
        loadTasks()
      }, 5000) // 每5秒刷新一次
      return () => clearInterval(interval)
    }
  }, [activeTab, tasks])

  // Tech Domain operations
  const loadTechDomains = async () => {
    setLoading(true)
    try {
      const response = await api.collect.listTechDomains()
      setTechDomains(response.data.items || [])
    } catch (_error) {
      message.error('加载技术领域失败')
    } finally {
      setLoading(false)
    }
  }

  // Load tech domain's bound venues (these are the venues available for this tech domain)
  const loadTechDomainVenues = async (techDomainId: number) => {
    setVenueLoading(true)
    try {
      const response = await api.venues.getTechDomainBindings(techDomainId)
      const bindings = response.data.items || []

      // 提取绑定的顶刊顶会信息
      const venues: VenueItem[] = bindings
        .filter((b: VenueBinding) => b.venue)
        .map((b: VenueBinding) => ({
          venue_id: b.venue_id,
          venue_code: b.venue!.venue_code,
          venue_name: b.venue!.venue_name,
          venue_name_en: b.venue!.venue_name_en,
          venue_type: b.venue!.venue_type,
          openalex_source_id: b.venue!.openalex_source_id,
          is_enabled: b.venue!.is_enabled,
        }))
      setAllVenues(venues)

      // 设置已启用的绑定
      const enabledIds = bindings
        .filter((b: VenueBinding) => b.is_enabled)
        .map((b: VenueBinding) => String(b.venue_id))
      setSelectedVenueIds(enabledIds)
    } catch (_error) {
      console.error("[API Error]", _error)
      message.error(`加载顶会顶刊列表失败: ${getErrorMessage(_error, '未知错误')}`)
      setAllVenues([])
      setSelectedVenueIds([])
    } finally {
      setVenueLoading(false)
    }
  }

  // Open venue config modal
  const handleConfigVenues = async (domain: TechDomainCollect) => {
    setSelectedDomain(domain)
    setSelectedVenueIds([])
    setAllVenues([])
    setVenueModalVisible(true)
    await loadTechDomainVenues(domain.tech_domain_id)
  }

  // Save venue bindings - update enabled status
  const handleSaveVenues = async () => {
    if (!selectedDomain) return

    try {
      // 更新绑定：传入选中的 venue_ids（未选中的会被禁用）
      console.log('[handleSaveVenues] 更新绑定状态:', { tech_domain_id: selectedDomain.tech_domain_id, selectedVenueIds })
      await api.venues.batchCreateBindings(selectedDomain.tech_domain_id, selectedVenueIds.map(id => parseInt(id, 10)))
      message.success('配置更新成功')
      setVenueModalVisible(false)
      loadTechDomains()
    } catch (_error) {
      console.error("[API Error]", _error)
      message.error(getErrorMessage(_error, '更新失败'))
    }
  }

  const handleOpenCollect = (domain: TechDomainCollect) => {
    setSelectedDomain(domain)
    setStartYear(TIME_RANGE_CONFIG.DEFAULT_START_YEAR)
    setEndYear(null)
    setCollectModalVisible(true)
  }

  const handleTriggerCollect = async () => {
    if (!selectedDomain) return

    try {
      await api.collect.triggerTask({
        tech_domain_id: selectedDomain.tech_domain_id,
        start_year: startYear,
        end_year: endYear,
      })
      message.success('采集任务已启动')
      setCollectModalVisible(false)
      setActiveTab('tasks')
      loadTasks()
    } catch (_error) {
      message.error(getErrorMessage(_error, '启动失败'))
    }
  }

  // Task operations
  const loadTasks = async () => {
    setLoading(true)
    try {
      const response = await api.collect.listTasks({ page: taskPage, page_size: 10 })
      const newTasks = response.data.items || []
      setTasks(newTasks)
      setTaskTotal(response.data.total || 0)

      // Check for newly completed tasks
      const currentRunningIds = new Set<number>(
        newTasks.filter((t: CollectTask) => t.status === 'running').map((t: CollectTask) => t.task_id)
      )
      const completedTaskIds = [...runningTaskIdsRef.current].filter(
        (id: number) => !currentRunningIds.has(id) && newTasks.some((t: CollectTask) => t.task_id === id && t.status === 'completed')
      )

      // If any task just completed, invalidate homepage cache
      if (completedTaskIds.length > 0) {
        console.log('[CollectPage] Tasks completed:', completedTaskIds, 'Invalidating homepage cache')
        queryClient.invalidateQueries({ queryKey: queryKeys.homepage.overview })
        queryClient.invalidateQueries({ queryKey: queryKeys.homepage.highlights })
        queryClient.invalidateQueries({ queryKey: queryKeys.techDomains.stats() })
        queryClient.invalidateQueries({ queryKey: queryKeys.techDomains.overallStats })
        queryClient.invalidateQueries({ queryKey: queryKeys.techDomains.overallTalents() })
      }

      // Update running task tracking
      runningTaskIdsRef.current = currentRunningIds
    } catch (_error) {
      message.error('加载任务列表失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCancelTask = async (taskId: number) => {
    try {
      await api.collect.cancelTask(taskId)
      message.success('任务已取消')
      loadTasks()
    } catch (_error) {
      message.error(getErrorMessage(_error, '取消失败'))
    }
  }

  const handleViewTask = (task: CollectTask) => {
    setSelectedTask(task)
    setTaskDetailVisible(true)
  }

  const handleDeleteTask = async (taskId: number) => {
    try {
      await api.collect.deleteTask(taskId)
      message.success('任务已删除')
      setTaskDetailVisible(false)
      loadTasks()
    } catch (_error) {
      message.error(getErrorMessage(_error, '删除失败'))
    }
  }

  // Collaboration sync operations
  const loadCollabSyncStatus = async () => {
    setCollabSyncLoading(true)
    try {
      const response = await api.talents.getCollaborationSyncStatus()
      setCollabSyncStatus(response.data.sync_progress)
      setCollabDataStatus(response.data.data_status)
    } catch (_error) {
      message.error('加载同步状态失败')
    } finally {
      setCollabSyncLoading(false)
    }
  }

  const handleSyncAllCollaborations = async () => {
    try {
      // 立即显示启动状态
      setCollabSyncStatus({ status: 'pending', processed: 0, total: 0, collaborations: 0 })
      message.info('正在启动同步任务...')

      void api.talents.syncCollaborations()
      message.success('同步任务已启动')

      // 立即更新状态为 running
      setCollabSyncStatus({ status: 'running', processed: 0, total: 0, collaborations: 0 })

      // 开始轮询进度，间隔1秒
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await api.talents.getCollaborationSyncStatus()
          const progress = statusResponse.data.sync_progress
          setCollabSyncStatus(progress)
          setCollabDataStatus(statusResponse.data.data_status)

          // 只有 completed 或 error 时才停止轮询
          if (progress.status === 'completed' || progress.status.startsWith('error')) {
            clearInterval(pollInterval)
            if (progress.status === 'completed') {
              message.success(`同步完成！处理 ${progress.processed} 篇论文，创建 ${progress.collaborations} 条合作关系`)
            }
          }
        } catch (_error) {
          console.error("Operation failed")
        }
      }, 1000)

      // 60秒后停止轮询（防止无限轮询）
      setTimeout(() => clearInterval(pollInterval), 60000)
    } catch (_error) {
      message.error(getErrorMessage(_error, '启动同步失败'))
      setCollabSyncStatus(null)
    }
  }

  // Tech Domain columns
  const domainColumns = [
    {
      title: '技术领域',
      dataIndex: 'domain_name',
      key: 'domain_name',
      width: 120,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: '关联顶会顶刊',
      key: 'venues',
      render: (_: unknown, record: TechDomainCollect) => {
        const sources = record.collect_sources || []
        if (sources.length === 0) {
          return <Text type="secondary">未配置</Text>
        }
        const displayVenues = sources.slice(0, 10)
        return (
          <Space size={[4, 4]} wrap>
            {displayVenues.map((v) => (
              <Tooltip key={v.id} title={v.name || v.id}>
                <Tag color={getVenueTypeConfig(v.type).color}>
                  {v.id.toUpperCase()}
                </Tag>
              </Tooltip>
            ))}
            {sources.length > 10 && <Tag>+{sources.length - 10}</Tag>}
          </Space>
        )
      },
    },
    {
      title: '顶会顶刊数',
      dataIndex: 'venue_count',
      key: 'venue_count',
      width: 100,
      render: (count: number) => (
        <Badge count={count} showZero color="blue" style={{ marginRight: 8 }} />
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: TechDomainCollect) => (
        <Space>
          <Tooltip title="配置顶会顶刊">
            <Button
              type="link"
              size="small"
              icon={<SettingOutlined />}
              onClick={() => handleConfigVenues(record)}
            >
              配置
            </Button>
          </Tooltip>
          <Tooltip title="启动采集">
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleOpenCollect(record)}
              disabled={!record.collect_sources || record.collect_sources.length === 0}
            >
              采集
            </Button>
          </Tooltip>
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
      width: 180,
    },
    {
      title: '技术领域',
      dataIndex: 'tech_domain_name',
      key: 'tech_domain_name',
      width: 100,
    },
    {
      title: '顶刊顶会',
      key: 'venues',
      render: (_: unknown, record: CollectTask) => {
        // 使用任务创建时的快照，而非当前配置
        const sources = record.venue_snapshot || []
        if (sources.length === 0) return <Text type="secondary">-</Text>
        const displayVenues = sources.slice(0, 5)
        return (
          <Space size={[4, 4]} wrap>
            {displayVenues.map((v) => (
              <Tooltip key={v.id} title={v.name || v.id}>
                <Tag>{v.id.toUpperCase()}</Tag>
              </Tooltip>
            ))}
            {sources.length > 5 && <Tag>+{sources.length - 5}</Tag>}
          </Space>
        )
      },
    },
    {
      title: '时间范围',
      key: 'time_range',
      render: (_: unknown, record: CollectTask) => (
        <Text>
          {record.start_year}年 ~ {record.end_year ? `${record.end_year}年` : '至今'}
        </Text>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const item = getTaskStatusConfig(status)
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
      title: '采集统计',
      key: 'records',
      render: (_: unknown, record: CollectTask) => (
        <Space direction="vertical" size={0}>
          <Text>论文: {record.total_records}</Text>
          <Text>人才: <Text type="success">{record.success_records}</Text></Text>
          <Text>院校机构: {record.skipped_records}</Text>
        </Space>
      ),
    },
    {
      title: '触发时间',
      dataIndex: 'triggered_at',
      key: 'triggered_at',
      render: (date: string) => formatUTCToLocal(date),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: CollectTask) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => handleViewTask(record)}
            />
          </Tooltip>
          {(record.status === 'running' || record.status === 'pending') && (
            <Popconfirm
              title="确定取消此任务？"
              onConfirm={() => handleCancelTask(record.task_id)}
              okText="确定"
              cancelText="取消"
            >
              <Button type="link" size="small" danger icon={<StopOutlined />} />
            </Popconfirm>
          )}
          {['completed', 'failed', 'cancelled'].includes(record.status) && (
            <Popconfirm
              title="确定删除此任务记录？"
              description="删除后不可恢复"
              onConfirm={() => handleDeleteTask(record.task_id)}
              okText="确定"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 0 }}>
      <Title level={4}>采集配置管理</Title>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'tech-domains',
            label: (
              <span>
                <SettingOutlined />
                技术领域配置
              </span>
            ),
            children: (
              <Card>
                <Spin spinning={loading}>
                  <Table
                    dataSource={techDomains}
                    columns={domainColumns}
                    rowKey="tech_domain_id"
                    pagination={false}
                    locale={{
                      emptyText: <Empty description="暂无技术领域数据" />,
                    }}
                  />
                </Spin>
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
                <Spin spinning={loading}>
                  <Table
                    dataSource={tasks}
                    columns={taskColumns}
                    rowKey="task_id"
                    pagination={{
                      current: taskPage,
                      pageSize: 10,
                      total: taskTotal,
                      showTotal: (t) => `共 ${t} 个任务`,
                      onChange: (p) => {
                        setTaskPage(p)
                        loadTasks()
                      },
                    }}
                    locale={{
                      emptyText: <Empty description="暂无采集任务" />,
                    }}
                  />
                </Spin>
              </Card>
            ),
          },
          {
            key: 'collaborations',
            label: (
              <span>
                <TeamOutlined />
                合作网络同步
              </span>
            ),
            children: (
              <Card>
                <Spin spinning={collabSyncLoading}>
                  {/* 状态面板 */}
                  <Row gutter={16} style={{ marginBottom: 24 }}>
                    <Col span={8}>
                      <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                        <Statistic
                          title="已同步学者数"
                          value={collabDataStatus?.talents_with_collaborations || 0}
                          prefix={<TeamOutlined />}
                        />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                        <Statistic
                          title="合作关系数"
                          value={collabDataStatus?.total_collaborations || 0}
                          prefix={<TeamOutlined />}
                        />
                      </Card>
                    </Col>
                    <Col span={8}>
                      <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                        <Statistic
                          title="最后同步时间"
                          value={formatUTCToLocal(collabDataStatus?.last_sync)}
                          valueStyle={{ fontSize: 16 }}
                        />
                      </Card>
                    </Col>
                  </Row>

                  {/* 同步进度 */}
                  {(collabSyncStatus?.status === 'running' || collabSyncStatus?.status === 'pending') && (
                    <Alert
                      type="info"
                      showIcon
                      icon={<SyncOutlined spin />}
                      style={{ marginBottom: 16 }}
                      message={collabSyncStatus?.status === 'pending' ? '正在启动同步任务...' : '同步进行中...'}
                      description={
                        <div>
                          {collabSyncStatus?.total > 0 && (
                            <>
                              <Progress
                                percent={Math.round((collabSyncStatus.processed / collabSyncStatus.total) * 100)}
                                status="active"
                              />
                              <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                                <Text type="secondary">
                                  已处理 {formatNumber(collabSyncStatus.processed)} / {formatNumber(collabSyncStatus.total)} 篇论文
                                </Text>
                                <Text type="secondary">
                                  新增 {formatNumber(collabSyncStatus.collaborations)} 条合作关系
                                </Text>
                              </Space>
                            </>
                          )}
                          {collabSyncStatus?.total === 0 && (
                            <Text type="secondary">正在扫描论文数据...</Text>
                          )}
                        </div>
                      }
                    />
                  )}

                  {/* 同步完成提示 */}
                  {collabSyncStatus?.status === 'completed' && (
                    <Alert
                      type="success"
                      showIcon
                      icon={<CheckCircleOutlined />}
                      style={{ marginBottom: 16 }}
                      message="同步完成"
                      description={
                        <Space direction="vertical" size={4}>
                          <Text>
                            已处理 <Text strong>{formatNumber(collabSyncStatus.processed)}</Text> 篇论文，
                            新增 <Text strong type="success">{formatNumber(collabSyncStatus.collaborations)}</Text> 条合作关系
                          </Text>
                        </Space>
                      }
                    />
                  )}

                  {/* 错误提示 */}
                  {collabSyncStatus?.status?.startsWith('error') && (
                    <Alert
                      type="error"
                      showIcon
                      style={{ marginBottom: 16 }}
                      message="同步失败"
                      description={collabSyncStatus.status}
                    />
                  )}

                  {/* 操作按钮 */}
                  <Space>
                    <Button
                      type="primary"
                      icon={<SyncOutlined spin={collabSyncStatus?.status === 'running'} />}
                      onClick={handleSyncAllCollaborations}
                      loading={collabSyncStatus?.status === 'running'}
                      disabled={collabSyncStatus?.status === 'running'}
                    >
                      {collabSyncStatus?.status === 'running' ? '同步中...' : '批量同步所有学者'}
                    </Button>
                    <Button
                      icon={<ReloadOutlined />}
                      onClick={loadCollabSyncStatus}
                      loading={collabSyncLoading}
                    >
                      刷新状态
                    </Button>
                  </Space>

                  {/* 说明 */}
                  <Alert
                    type="info"
                    showIcon
                    style={{ marginTop: 24 }}
                    message="功能说明"
                    description={
                      <ul style={{ margin: 0, paddingLeft: 20 }}>
                        <li>从已采集的论文数据中提取学者合作关系，无需重复调用 API</li>
                        <li>请确保已执行过采集任务，有论文数据后才能提取合作关系</li>
                        <li>同步完成后，学者详情页的合作网络将自动展示数据</li>
                      </ul>
                    }
                  />
                </Spin>
              </Card>
            ),
          },
        ]}
      />

      {/* Venue Config Modal */}
      <Modal
        title={`配置采集范围 - ${selectedDomain?.domain_name || ''}`}
        open={venueModalVisible}
        onCancel={() => setVenueModalVisible(false)}
        onOk={handleSaveVenues}
        width={800}
        okText="保存配置"
        confirmLoading={venueLoading}
      >
        <div style={{ marginBottom: 16 }}>
          <Alert
            message="勾选需要采集的顶会顶刊，未勾选的将不会采集"
            type="info"
            showIcon
          />
          <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
            已关联 {allVenues.length} 个顶会顶刊，已选择 {selectedVenueIds.length} 个进行采集
          </Text>
        </div>
        <Spin spinning={venueLoading}>
          <Transfer
            dataSource={allVenues.map(v => ({
              key: String(v.venue_id),
              title: (v.venue_code || v.venue_name).toUpperCase(),
              description: v.venue_name,
              venue_type: v.venue_type,
            }))}
            titles={['不采集', '待采集']}
            targetKeys={selectedVenueIds}
            onChange={(newTargetKeys) => setSelectedVenueIds(newTargetKeys as string[])}
            render={(item) => (
              <span>
                <Tag color={getVenueTypeConfig(item.venue_type).color} style={{ marginRight: 4 }}>
                  {getVenueTypeConfig(item.venue_type).label}
                </Tag>
                <Text strong>{item.title}</Text>
                <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>({item.description})</Text>
              </span>
            )}
            listStyle={{
              width: 350,
              height: 400,
            }}
            showSearch
            filterOption={(input, item) =>
              item.title?.toLowerCase().includes(input.toLowerCase()) ||
              item.description?.toLowerCase().includes(input.toLowerCase())
            }
            locale={{
              itemUnit: '个',
              itemsUnit: '个',
              searchPlaceholder: '搜索...',
              notFoundContent: '该技术领域暂无关联的顶会顶刊',
            }}
          />
        </Spin>
      </Modal>

      {/* Collect Confirm Modal */}
      <Modal
        title={`启动采集 - ${selectedDomain?.domain_name || ''}`}
        open={collectModalVisible}
        onCancel={() => setCollectModalVisible(false)}
        onOk={handleTriggerCollect}
        okText="确认采集"
      >
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="采集范围">
            <Space size={[4, 4]} wrap>
              {(selectedDomain?.collect_sources || []).slice(0, 5).map(v => (
                <Tooltip key={v.id} title={v.name || v.id}>
                  <Tag color={getVenueTypeConfig(v.type).color}>{v.id}</Tag>
                </Tooltip>
              ))}
              {(selectedDomain?.collect_sources?.length || 0) > 5 && <Tag>+{selectedDomain!.collect_sources!.length - 5}</Tag>}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="数据类型">学者、论文、机构</Descriptions.Item>
          <Descriptions.Item label="时间范围">
            <Space>
              <Select
                value={startYear}
                onChange={(value) => {
                  setStartYear(value)
                  // 如果截止年份小于起始年份，自动调整
                  if (endYear !== null && endYear < value) {
                    setEndYear(null)
                  }
                }}
                style={{ width: 120 }}
                options={getStartYearOptions()}
              />
              <Text>至</Text>
              <Select
                value={endYear}
                onChange={setEndYear}
                style={{ width: 120 }}
                options={getEndYearOptions(startYear)}
                placeholder="至今"
              />
            </Space>
          </Descriptions.Item>
        </Descriptions>
      </Modal>

      {/* Task Detail Modal */}
      <Modal
        title="任务详情"
        open={taskDetailVisible}
        onCancel={() => setTaskDetailVisible(false)}
        footer={
          (selectedTask?.status === 'running' || selectedTask?.status === 'pending') ? (
            <Space>
              <Button onClick={() => {
                loadTasks()
                // Refresh selected task
                const updated = tasks.find(t => t.task_id === selectedTask?.task_id)
                if (updated) setSelectedTask(updated)
              }}>
                <ReloadOutlined /> 刷新状态
              </Button>
              <Popconfirm
                title="确定取消此任务？"
                onConfirm={() => {
                  handleCancelTask(selectedTask.task_id)
                  setTaskDetailVisible(false)
                }}
                okText="确定"
                cancelText="取消"
              >
                <Button danger>取消任务</Button>
              </Popconfirm>
            </Space>
          ) : ['completed', 'failed', 'cancelled'].includes(selectedTask?.status || '') ? (
            <Space>
              <Button onClick={() => setTaskDetailVisible(false)}>关闭</Button>
              <Popconfirm
                title="确定删除此任务记录？"
                description="删除后不可恢复"
                onConfirm={() => selectedTask && handleDeleteTask(selectedTask.task_id)}
                okText="确定删除"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button danger icon={<DeleteOutlined />}>删除任务</Button>
              </Popconfirm>
            </Space>
          ) : (
            <Button onClick={() => setTaskDetailVisible(false)}>关闭</Button>
          )
        }
        width={800}
      >
        {selectedTask && (
          <div>
            {/* 基本信息 */}
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="任务编码">{selectedTask.task_code}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge
                  status={getTaskStatusConfig(selectedTask.status).status}
                  text={getTaskStatusConfig(selectedTask.status).label}
                />
              </Descriptions.Item>
              <Descriptions.Item label="技术领域">{selectedTask.tech_domain_name}</Descriptions.Item>
              <Descriptions.Item label="时间范围">
                {selectedTask.start_year}年 ~ {selectedTask.end_year ? `${selectedTask.end_year}年` : '至今'}
              </Descriptions.Item>
              <Descriptions.Item label="进度" span={2}>
                <Progress
                  percent={selectedTask.progress_percent}
                  status={selectedTask.status === 'failed' ? 'exception' : selectedTask.status === 'completed' ? 'success' : 'active'}
                />
              </Descriptions.Item>
              <Descriptions.Item label="当前步骤" span={2}>
                {selectedTask.status === 'running' ? (
                  <Text>
                    <LoadingOutlined spin style={{ marginRight: 8 }} />
                    {selectedTask.current_step || '-'}
                  </Text>
                ) : (
                  selectedTask.current_step || '-'
                )}
              </Descriptions.Item>
            </Descriptions>

            {/* 统计信息 */}
            <Card title="采集统计" size="small" style={{ marginTop: 16 }}>
              <Row gutter={16}>
                <Col span={4}>
                  <Statistic title="采集论文" value={selectedTask.total_records || 0} />
                </Col>
                <Col span={4}>
                  <Statistic title="获取作者" value={selectedTask.result_summary?.total_authors || selectedTask.processed_records || 0} />
                </Col>
                <Col span={4}>
                  <Statistic title="标准化作者" value={selectedTask.processed_records || 0} />
                </Col>
                <Col span={4}>
                  <Statistic title="标准化院校" value={selectedTask.skipped_records || 0} />
                </Col>
                <Col span={4}>
                  <Statistic title="入库人才" value={selectedTask.success_records || 0} valueStyle={{ color: '#52c41a' }} />
                </Col>
                <Col span={4}>
                  <Statistic title="更新人才" value={selectedTask.result_summary?.updated_talents || 0} />
                </Col>
              </Row>
              {selectedTask.result_summary && (
                <Row gutter={16} style={{ marginTop: 16 }}>
                  <Col span={4}>
                    <Statistic title="新建人才" value={selectedTask.result_summary.created_talents || 0} valueStyle={{ color: '#1890ff' }} />
                  </Col>
                  <Col span={4}>
                    <Statistic title="技术标签" value={selectedTask.result_summary.created_tech_tags || 0} />
                  </Col>
                </Row>
              )}
            </Card>

            {/* 时间信息 */}
            <Card title="时间信息" size="small" style={{ marginTop: 16 }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="触发时间">
                  {formatUTCToLocal(selectedTask.triggered_at)}
                </Descriptions.Item>
                <Descriptions.Item label="开始时间">
                  {formatUTCToLocal(selectedTask.started_at)}
                </Descriptions.Item>
                <Descriptions.Item label="完成时间">
                  {formatUTCToLocal(selectedTask.completed_at)}
                </Descriptions.Item>
                <Descriptions.Item label="耗时">
                  {selectedTask.result_summary?.total_duration || '-'}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* 采集源详情 */}
            {selectedTask.result_summary?.venue_details && selectedTask.result_summary.venue_details.length > 0 && (
              <Card title="采集源详情" size="small" style={{ marginTop: 16 }}>
                <Table
                  dataSource={selectedTask.result_summary.venue_details}
                  rowKey="venue_id"
                  size="small"
                  pagination={false}
                  columns={[
                    {
                      title: '采集源',
                      key: 'venue_id',
                      width: 120,
                      render: (_: unknown, record: { venue_id: string; venue_name: string }) => (
                        <Tooltip title={record.venue_name}>
                          <Text strong>{record.venue_id.toUpperCase()}</Text>
                        </Tooltip>
                      ),
                    },
                    {
                      title: '状态',
                      dataIndex: 'status',
                      key: 'status',
                      width: 80,
                      render: (status: string) => {
                        const statusConfig: Record<string, { icon: React.ReactNode; color: string }> = {
                          running: { icon: <LoadingOutlined spin />, color: '#1890ff' },
                          completed: { icon: <CheckCircleOutlined />, color: '#52c41a' },
                          timeout: { icon: <ClockCircleOutlined />, color: '#faad14' },
                          error: { icon: <CloseCircleOutlined />, color: '#ff4d4f' },
                        }
                        const config = statusConfig[status] || { icon: null, color: undefined }
                        return (
                          <Tag color={config.color}>
                            {config.icon} {status}
                          </Tag>
                        )
                      },
                    },
                    {
                      title: '获取',
                      dataIndex: 'fetched',
                      key: 'fetched',
                      width: 60,
                      align: 'center',
                    },
                    {
                      title: '入库',
                      dataIndex: 'saved',
                      key: 'saved',
                      width: 60,
                      align: 'center',
                    },
                    {
                      title: '耗时',
                      dataIndex: 'duration',
                      key: 'duration',
                      width: 80,
                    },
                    {
                      title: '错误',
                      dataIndex: 'error',
                      key: 'error',
                      ellipsis: true,
                      render: (error: string) => error ? <Text type="danger">{error}</Text> : '-',
                    },
                  ]}
                />
              </Card>
            )}

            {/* 执行日志 */}
            {selectedTask.execution_logs && selectedTask.execution_logs.length > 0 && (
              <Card title="执行日志" size="small" style={{ marginTop: 16 }}>
                <Timeline
                  items={selectedTask.execution_logs.map((log) => ({
                    color: log.level === 'error' ? 'red' : log.level === 'warning' ? 'orange' : 'blue',
                    children: (
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <Tag color={log.level === 'error' ? 'error' : log.level === 'warning' ? 'warning' : 'processing'}>
                            {log.level.toUpperCase()}
                          </Tag>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {formatUTCToLocal(log.timestamp)}
                          </Text>
                        </div>
                        <div>{log.message}</div>
                        {log.details != null && (
                          <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                            {typeof log.details === 'object' ? JSON.stringify(log.details) : String(log.details)}
                          </div>
                        )}
                      </div>
                    ),
                  }))}
                />
              </Card>
            )}

            {/* 错误信息 */}
            {selectedTask.error_message && (
              <Alert
                type="error"
                message="错误信息"
                description={selectedTask.error_message}
                style={{ marginTop: 16 }}
                showIcon
              />
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}

export default CollectPage
