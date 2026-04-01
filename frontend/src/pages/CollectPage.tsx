/**
 * 采集配置管理页面 - MVP v1.2
 *
 * 功能说明：
 * - 技术要素配置：管理技术要素关联的顶会顶刊
 * - 采集任务：基于技术要素触发采集，可配置年份范围
 * - 固定参数：数据类型（学者+论文+机构）
 * - 可配置参数：时间范围（起始年份~截止年份/至今）
 */
import { useEffect, useState } from 'react'
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
import {
  getTaskStatusConfig,
  getVenueTypeConfig,
  getStartYearOptions,
  getEndYearOptions,
  TIME_RANGE_CONFIG,
} from '../constants'
import type { VenueItem, VenueBinding, TechElementCollect, CollectTask } from '../types'

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
  // Tech Elements state
  const [techElements, setTechElements] = useState<TechElementCollect[]>([])
  const [venueModalVisible, setVenueModalVisible] = useState(false)
  const [collectModalVisible, setCollectModalVisible] = useState(false)
  const [selectedElement, setSelectedElement] = useState<TechElementCollect | null>(null)

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
  const [activeTab, setActiveTab] = useState('tech-elements')

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
    if (activeTab === 'tech-elements') {
      loadTechElements()
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

  // Tech Element operations
  const loadTechElements = async () => {
    setLoading(true)
    try {
      const response = await api.collect.listTechElements()
      setTechElements(response.data.items || [])
    } catch (error) {
      message.error('加载技术要素失败')
    } finally {
      setLoading(false)
    }
  }

  // Load tech element's bound venues (these are the venues available for this tech element)
  const loadTechElementVenues = async (techElementId: number) => {
    setVenueLoading(true)
    try {
      console.log('[loadTechElementVenues] 加载技术要素关联的顶刊顶会...')
      const response = await api.venues.getTechElementBindings(techElementId)
      const bindings = response.data.items || []
      console.log('[loadTechElementVenues] 响应:', bindings)

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
    } catch (error) {
      console.error('[loadTechElementVenues] 加载失败', error)
      message.error(`加载顶会顶刊列表失败: ${getErrorMessage(error, '未知错误')}`)
      setAllVenues([])
      setSelectedVenueIds([])
    } finally {
      setVenueLoading(false)
    }
  }

  // Open venue config modal
  const handleConfigVenues = async (element: TechElementCollect) => {
    setSelectedElement(element)
    setSelectedVenueIds([])
    setAllVenues([])
    setVenueModalVisible(true)
    await loadTechElementVenues(element.tech_element_id)
  }

  // Save venue bindings - update enabled status
  const handleSaveVenues = async () => {
    if (!selectedElement) return

    try {
      // 更新绑定：传入选中的 venue_ids（未选中的会被禁用）
      console.log('[handleSaveVenues] 更新绑定状态:', { tech_element_id: selectedElement.tech_element_id, selectedVenueIds })
      await api.venues.batchCreateBindings(selectedElement.tech_element_id, selectedVenueIds.map(id => parseInt(id, 10)))
      message.success('配置更新成功')
      setVenueModalVisible(false)
      loadTechElements()
    } catch (error) {
      console.error('[handleSaveVenues] 保存失败', error)
      message.error(getErrorMessage(error, '更新失败'))
    }
  }

  const handleOpenCollect = (element: TechElementCollect) => {
    setSelectedElement(element)
    setStartYear(TIME_RANGE_CONFIG.DEFAULT_START_YEAR)
    setEndYear(null)
    setCollectModalVisible(true)
  }

  const handleTriggerCollect = async () => {
    if (!selectedElement) return

    try {
      await api.collect.triggerTask({
        tech_element_id: selectedElement.tech_element_id,
        start_year: startYear,
        end_year: endYear,
      })
      message.success('采集任务已启动')
      setCollectModalVisible(false)
      setActiveTab('tasks')
      loadTasks()
    } catch (error) {
      message.error(getErrorMessage(error, '启动失败'))
    }
  }

  // Task operations
  const loadTasks = async () => {
    setLoading(true)
    try {
      const response = await api.collect.listTasks({ page: taskPage, page_size: 10 })
      setTasks(response.data.items || [])
      setTaskTotal(response.data.total || 0)
    } catch (error) {
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
    } catch (error) {
      message.error(getErrorMessage(error, '取消失败'))
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
    } catch (error) {
      message.error(getErrorMessage(error, '删除失败'))
    }
  }

  // Collaboration sync operations
  const loadCollabSyncStatus = async () => {
    setCollabSyncLoading(true)
    try {
      const response = await api.talents.getCollaborationSyncStatus()
      setCollabSyncStatus(response.data.sync_progress)
      setCollabDataStatus(response.data.data_status)
    } catch (error) {
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

      const response = await api.talents.syncCollaborations()
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
        } catch (err) {
          console.error('轮询状态失败:', err)
        }
      }, 1000)

      // 60秒后停止轮询（防止无限轮询）
      setTimeout(() => clearInterval(pollInterval), 60000)
    } catch (error) {
      message.error(getErrorMessage(error, '启动同步失败'))
      setCollabSyncStatus(null)
    }
  }

  // Tech Element columns
  const elementColumns = [
    {
      title: '技术要素',
      dataIndex: 'element_name',
      key: 'element_name',
      render: (name: string, record: TechElementCollect) => (
        <Space>
          <Text strong>{name}</Text>
          {record.element_name_en && <Text type="secondary">({record.element_name_en})</Text>}
        </Space>
      ),
    },
    {
      title: '关联顶会顶刊',
      key: 'venues',
      render: (_: unknown, record: TechElementCollect) => {
        const sources = record.collect_sources || []
        if (sources.length === 0) {
          return <Text type="secondary">未配置</Text>
        }
        const displayVenues = sources.slice(0, 3)
        return (
          <Space size={[4, 4]} wrap>
            {displayVenues.map((v) => (
              <Tooltip key={v.id} title={v.id}>
                <Tag color={getVenueTypeConfig(v.type).color}>
                  {v.name || v.id}
                </Tag>
              </Tooltip>
            ))}
            {sources.length > 3 && <Tag>+{sources.length - 3}</Tag>}
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
      render: (_: unknown, record: TechElementCollect) => (
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
      width: 220,
    },
    {
      title: '技术要素',
      dataIndex: 'tech_element_name',
      key: 'tech_element_name',
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
      render: (date: string) => new Date(date).toLocaleString(),
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
            key: 'tech-elements',
            label: (
              <span>
                <SettingOutlined />
                技术要素配置
              </span>
            ),
            children: (
              <Card>
                <Spin spinning={loading}>
                  <Table
                    dataSource={techElements}
                    columns={elementColumns}
                    rowKey="tech_element_id"
                    pagination={false}
                    locale={{
                      emptyText: <Empty description="暂无技术要素数据" />,
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
                          value={collabDataStatus?.last_sync ? new Date(collabDataStatus.last_sync).toLocaleString() : '-'}
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
                                  已处理 {collabSyncStatus.processed.toLocaleString()} / {collabSyncStatus.total.toLocaleString()} 篇论文
                                </Text>
                                <Text type="secondary">
                                  新增 {collabSyncStatus.collaborations.toLocaleString()} 条合作关系
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
                            已处理 <Text strong>{collabSyncStatus.processed?.toLocaleString()}</Text> 篇论文，
                            新增 <Text strong type="success">{collabSyncStatus.collaborations?.toLocaleString()}</Text> 条合作关系
                          </Text>
                          {collabSyncStatus.total_works && (
                            <Text type="secondary">
                              共 {collabSyncStatus.total_works.toLocaleString()} 篇论文数据
                            </Text>
                          )}
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
        title={`配置采集范围 - ${selectedElement?.element_name || ''}`}
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
              title: v.venue_name,
              description: v.venue_name_en || v.venue_code,
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
                {item.title}
                {item.description && <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>({item.description})</Text>}
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
              notFoundContent: '该技术要素暂无关联的顶会顶刊',
            }}
          />
        </Spin>
      </Modal>

      {/* Collect Confirm Modal */}
      <Modal
        title={`启动采集 - ${selectedElement?.element_name || ''}`}
        open={collectModalVisible}
        onCancel={() => setCollectModalVisible(false)}
        onOk={handleTriggerCollect}
        okText="确认采集"
      >
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="采集范围">
            <Space size={[4, 4]} wrap>
              {(selectedElement?.collect_sources || []).slice(0, 5).map(v => (
                <Tag key={v.id} color={getVenueTypeConfig(v.type).color}>
                  {v.name || v.id}
                </Tag>
              ))}
              {(selectedElement?.collect_sources?.length || 0) > 5 && <Tag>+{selectedElement!.collect_sources!.length - 5}</Tag>}
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
              <Descriptions.Item label="技术要素">{selectedTask.tech_element_name}</Descriptions.Item>
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
              <Space size="large">
                <div>
                  <Text type="secondary">采集论文</Text>
                  <div style={{ fontSize: 24, fontWeight: 'bold' }}>{selectedTask.total_records}</div>
                </div>
                <div>
                  <Text type="secondary">入库人才</Text>
                  <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>{selectedTask.success_records}</div>
                </div>
                <div>
                  <Text type="secondary">标准化院校机构</Text>
                  <div style={{ fontSize: 24, fontWeight: 'bold' }}>{selectedTask.skipped_records}</div>
                </div>
                <div>
                  <Text type="secondary">标准化作者</Text>
                  <div style={{ fontSize: 24, fontWeight: 'bold' }}>{selectedTask.processed_records}</div>
                </div>
              </Space>
            </Card>

            {/* 时间信息 */}
            <Card title="时间信息" size="small" style={{ marginTop: 16 }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="触发时间">
                  {new Date(selectedTask.triggered_at).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="开始时间">
                  {selectedTask.started_at ? new Date(selectedTask.started_at).toLocaleString() : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="完成时间">
                  {selectedTask.completed_at ? new Date(selectedTask.completed_at).toLocaleString() : '-'}
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
                      dataIndex: 'venue_name',
                      key: 'venue_name',
                      width: 200,
                      ellipsis: true,
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
                            {new Date(log.timestamp).toLocaleString()}
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
