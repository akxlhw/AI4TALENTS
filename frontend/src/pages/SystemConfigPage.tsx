/**
 * System Configuration Page - v1.4
 *
 * 功能说明：
 * - 采集配置：技术要素配置、采集任务管理
 * - LLM 配置：LLM API 设置
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
  Alert,
  Transfer,
  Row,
  Col,
  Statistic,
  Form,
  Input,
  InputNumber,
  Switch,
} from 'antd'
import {
  SettingOutlined,
  ThunderboltOutlined,
  PlayCircleOutlined,
  StopOutlined,
  EyeOutlined,
  DeleteOutlined,
  ReloadOutlined,
  TeamOutlined,
  SyncOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CloudUploadOutlined,
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
import type { VenueItem, VenueBinding, TechElementCollect, CollectTask } from '../types'
import { formatUTCToLocal } from '../utils/datetime'

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

// LLM Config type
interface LLMConfig {
  enabled: boolean
  provider: string
  api_key_masked: string
  api_base: string
  model: string
  embedding_model: string
  embedding_api_base: string
  timeout: number
}

const SystemConfigPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('collect')

  // ========== Collect Config State ==========
  const [techElements, setTechElements] = useState<TechElementCollect[]>([])
  const [venueModalVisible, setVenueModalVisible] = useState(false)
  const [collectModalVisible, setCollectModalVisible] = useState(false)
  const [selectedElement, setSelectedElement] = useState<TechElementCollect | null>(null)
  const [startYear, setStartYear] = useState<number>(TIME_RANGE_CONFIG.DEFAULT_START_YEAR)
  const [endYear, setEndYear] = useState<number | null>(null)
  const [allVenues, setAllVenues] = useState<VenueItem[]>([])
  const [selectedVenueIds, setSelectedVenueIds] = useState<string[]>([])
  const [venueLoading, setVenueLoading] = useState(false)
  const [tasks, setTasks] = useState<CollectTask[]>([])
  const [taskTotal, setTaskTotal] = useState(0)
  const [taskPage, setTaskPage] = useState(1)
  const [taskDetailVisible, setTaskDetailVisible] = useState(false)
  const [selectedTask, setSelectedTask] = useState<CollectTask | null>(null)
  const [loading, setLoading] = useState(false)
  const [collectSubTab, setCollectSubTab] = useState('tech-elements')
  const runningTaskIdsRef = useRef<Set<number>>(new Set())
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

  // ========== LLM Config State ==========
  const [llmConfig, setLLMConfig] = useState<LLMConfig | null>(null)
  const [llmForm] = Form.useForm()
  const [llmLoading, setLLMLoading] = useState(false)
  const [testingLLM, setTestingLLM] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  // ========== Embedding Generation State ==========
  const [embeddingStatus, setEmbeddingStatus] = useState<{
    total_talents: number
    embedded_talents: number
    pending_talents: number
    last_generated: string | null
    progress_percent: number
  } | null>(null)
  const [embeddingProgress, setEmbeddingProgress] = useState<{
    status: string
    processed: number
    total: number
    failed: number
  } | null>(null)
  const [embeddingLoading, setEmbeddingLoading] = useState(false)

  // Load data based on active tab
  useEffect(() => {
    if (activeTab === 'collect') {
      if (collectSubTab === 'tech-elements') {
        loadTechElements()
      } else if (collectSubTab === 'tasks') {
        loadTasks()
      } else if (collectSubTab === 'collaborations') {
        loadCollabSyncStatus()
      } else if (collectSubTab === 'embeddings') {
        loadEmbeddingStatus()
      }
    } else if (activeTab === 'llm') {
      loadLLMConfig()
    }
  }, [activeTab, collectSubTab])

  // Auto-refresh for running tasks
  useEffect(() => {
    if (collectSubTab === 'tasks' && tasks.some(t => t.status === 'running')) {
      const interval = setInterval(() => {
        loadTasks()
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [collectSubTab, tasks])

  // ========== Collect Config Functions ==========
  const loadTechElements = async () => {
    setLoading(true)
    try {
      const response = await api.collect.listTechElements()
      setTechElements(response.data.items || [])
    } catch {
      message.error('加载技术要素失败')
    } finally {
      setLoading(false)
    }
  }

  const loadTechElementVenues = async (techElementId: number) => {
    setVenueLoading(true)
    try {
      const response = await api.venues.getTechElementBindings(techElementId)
      const bindings = response.data.items || []
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
      const enabledIds = bindings
        .filter((b: VenueBinding) => b.is_enabled)
        .map((b: VenueBinding) => String(b.venue_id))
      setSelectedVenueIds(enabledIds)
    } catch {
      message.error('加载顶会顶刊列表失败')
      setAllVenues([])
      setSelectedVenueIds([])
    } finally {
      setVenueLoading(false)
    }
  }

  const handleConfigVenues = async (element: TechElementCollect) => {
    setSelectedElement(element)
    setSelectedVenueIds([])
    setAllVenues([])
    setVenueModalVisible(true)
    await loadTechElementVenues(element.tech_element_id)
  }

  const handleSaveVenues = async () => {
    if (!selectedElement) return
    try {
      await api.venues.batchCreateBindings(selectedElement.tech_element_id, selectedVenueIds.map(id => parseInt(id, 10)))
      message.success('配置更新成功')
      setVenueModalVisible(false)
      loadTechElements()
    } catch (error) {
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
      setCollectSubTab('tasks')
      loadTasks()
    } catch (error) {
      message.error(getErrorMessage(error, '启动失败'))
    }
  }

  const loadTasks = async () => {
    setLoading(true)
    try {
      const response = await api.collect.listTasks({ page: taskPage, page_size: 10 })
      const newTasks = response.data.items || []
      setTasks(newTasks)
      setTaskTotal(response.data.total || 0)
      const currentRunningIds = new Set<number>(
        newTasks.filter((t: CollectTask) => t.status === 'running').map((t: CollectTask) => t.task_id)
      )
      const completedTaskIds = [...runningTaskIdsRef.current].filter(
        (id: number) => !currentRunningIds.has(id) && newTasks.some((t: CollectTask) => t.task_id === id && t.status === 'completed')
      )
      if (completedTaskIds.length > 0) {
        queryClient.invalidateQueries({ queryKey: queryKeys.homepage.overview })
        queryClient.invalidateQueries({ queryKey: queryKeys.homepage.highlights })
      }
      runningTaskIdsRef.current = currentRunningIds
    } catch {
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

  const loadCollabSyncStatus = async () => {
    setCollabSyncLoading(true)
    try {
      const response = await api.talents.getCollaborationSyncStatus()
      setCollabSyncStatus(response.data.sync_progress)
      setCollabDataStatus(response.data.data_status)
    } catch {
      message.error('加载同步状态失败')
    } finally {
      setCollabSyncLoading(false)
    }
  }

  const handleSyncAllCollaborations = async () => {
    try {
      setCollabSyncStatus({ status: 'pending', processed: 0, total: 0, collaborations: 0 })
      message.info('正在启动同步任务...')
      void api.talents.syncCollaborations()
      message.success('同步任务已启动')
      setCollabSyncStatus({ status: 'running', processed: 0, total: 0, collaborations: 0 })
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await api.talents.getCollaborationSyncStatus()
          const progress = statusResponse.data.sync_progress
          setCollabSyncStatus(progress)
          setCollabDataStatus(statusResponse.data.data_status)
          if (progress.status === 'completed' || progress.status.startsWith('error')) {
            clearInterval(pollInterval)
            if (progress.status === 'completed') {
              message.success(`同步完成！处理 ${progress.processed} 篇论文，创建 ${progress.collaborations} 条合作关系`)
            }
          }
        } catch { /* ignore */ }
      }, 1000)
      setTimeout(() => clearInterval(pollInterval), 60000)
    } catch (error) {
      message.error(getErrorMessage(error, '启动同步失败'))
      setCollabSyncStatus(null)
    }
  }

  // ========== LLM Config Functions ==========
  const loadLLMConfig = async () => {
    setLLMLoading(true)
    try {
      const response = await api.systemConfig.getLLMConfig()
      setLLMConfig(response.data)
      llmForm.setFieldsValue(response.data)
    } catch {
      message.error('加载 LLM 配置失败')
    } finally {
      setLLMLoading(false)
    }
  }

  const handleSaveLLMConfig = async () => {
    try {
      const values = await llmForm.validateFields()
      setLLMLoading(true)
      await api.systemConfig.updateLLMConfig(values)
      message.success('LLM 配置已保存')
      loadLLMConfig()
    } catch (error) {
      message.error(getErrorMessage(error, '保存失败'))
    } finally {
      setLLMLoading(false)
    }
  }

  const handleTestLLM = async () => {
    setTestingLLM(true)
    setTestResult(null)
    try {
      const response = await api.systemConfig.testLLM()
      setTestResult({
        success: response.data.success,
        message: response.data.message,
      })
      if (response.data.success) {
        message.success('LLM 连接测试成功')
      } else {
        message.warning(response.data.message)
      }
    } catch (error) {
      const errorMsg = getErrorMessage(error, '连接测试失败')
      setTestResult({ success: false, message: errorMsg })
      message.error(errorMsg)
    } finally {
      setTestingLLM(false)
    }
  }

  // ========== Embedding Generation Functions ==========
  const loadEmbeddingStatus = async () => {
    setEmbeddingLoading(true)
    try {
      const response = await api.embeddings.getStatus()
      setEmbeddingStatus(response.data)
      // Also check progress
      const progressResponse = await api.embeddings.getProgress()
      setEmbeddingProgress(progressResponse.data)
    } catch {
      message.error('加载嵌入状态失败')
    } finally {
      setEmbeddingLoading(false)
    }
  }

  const handleGenerateEmbeddings = async (force: boolean = false) => {
    try {
      setEmbeddingProgress({ status: 'pending', processed: 0, total: 0, failed: 0 })
      message.info('正在启动向量生成任务...')
      const response = await api.embeddings.generate(force, 100)
      message.success(`向量生成任务已启动，共 ${response.data.total_talents} 位人才`)
      setEmbeddingProgress({ status: 'running', processed: 0, total: response.data.total_talents, failed: 0 })

      // Start polling for progress
      const pollInterval = setInterval(async () => {
        try {
          const progressResponse = await api.embeddings.getProgress()
          setEmbeddingProgress(progressResponse.data)

          if (progressResponse.data.status === 'completed' || progressResponse.data.status === 'error') {
            clearInterval(pollInterval)
            loadEmbeddingStatus()
            if (progressResponse.data.status === 'completed') {
              message.success(`向量生成完成！处理 ${progressResponse.data.processed} 位人才`)
            }
          }
        } catch { /* ignore */ }
      }, 2000)

      // Stop after 10 minutes
      setTimeout(() => clearInterval(pollInterval), 600000)
    } catch (error) {
      message.error(getErrorMessage(error, '启动向量生成失败'))
      setEmbeddingProgress(null)
    }
  }

  const handleCancelEmbeddingGeneration = async () => {
    try {
      await api.embeddings.cancel()
      message.success('已取消向量生成任务')
      setEmbeddingProgress(null)
      loadEmbeddingStatus()
    } catch (error) {
      message.error(getErrorMessage(error, '取消失败'))
    }
  }

  // ========== Table Columns ==========
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
        if (sources.length === 0) return <Text type="secondary">未配置</Text>
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
            <Button type="link" size="small" icon={<SettingOutlined />} onClick={() => handleConfigVenues(record)}>
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

  const taskColumns = [
    { title: '任务编码', dataIndex: 'task_code', key: 'task_code', width: 220 },
    { title: '技术要素', dataIndex: 'tech_element_name', key: 'tech_element_name' },
    {
      title: '时间范围',
      key: 'time_range',
      render: (_: unknown, record: CollectTask) => (
        <Text>{record.start_year}年 ~ {record.end_year ? `${record.end_year}年` : '至今'}</Text>
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
            <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewTask(record)} />
          </Tooltip>
          {(record.status === 'running' || record.status === 'pending') && (
            <Popconfirm title="确定取消此任务？" onConfirm={() => handleCancelTask(record.task_id)} okText="确定" cancelText="取消">
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

  // ========== Render ==========
  return (
    <div style={{ padding: 0 }}>
      <Title level={4}>系统配置</Title>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'collect',
            label: <span><ThunderboltOutlined /> 采集配置</span>,
            children: (
              <Tabs
                activeKey={collectSubTab}
                onChange={setCollectSubTab}
                items={[
                  {
                    key: 'tech-elements',
                    label: <span><SettingOutlined /> 技术要素配置</span>,
                    children: (
                      <Card>
                        <Spin spinning={loading}>
                          <Table
                            dataSource={techElements}
                            columns={elementColumns}
                            rowKey="tech_element_id"
                            pagination={false}
                            locale={{ emptyText: <Empty description="暂无技术要素数据" /> }}
                          />
                        </Spin>
                      </Card>
                    ),
                  },
                  {
                    key: 'tasks',
                    label: <span><ThunderboltOutlined /> 采集任务</span>,
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
                              onChange: (p) => { setTaskPage(p); loadTasks() },
                            }}
                            locale={{ emptyText: <Empty description="暂无采集任务" /> }}
                          />
                        </Spin>
                      </Card>
                    ),
                  },
                  {
                    key: 'collaborations',
                    label: <span><TeamOutlined /> 合作网络同步</span>,
                    children: (
                      <Card>
                        <Spin spinning={collabSyncLoading}>
                          <Row gutter={16} style={{ marginBottom: 24 }}>
                            <Col span={8}>
                              <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                                <Statistic title="已同步学者数" value={collabDataStatus?.talents_with_collaborations || 0} prefix={<TeamOutlined />} />
                              </Card>
                            </Col>
                            <Col span={8}>
                              <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                                <Statistic title="合作关系数" value={collabDataStatus?.total_collaborations || 0} prefix={<TeamOutlined />} />
                              </Card>
                            </Col>
                            <Col span={8}>
                              <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                                <Statistic title="最后同步时间" value={formatUTCToLocal(collabDataStatus?.last_sync)} valueStyle={{ fontSize: 16 }} />
                              </Card>
                            </Col>
                          </Row>
                          {(collabSyncStatus?.status === 'running' || collabSyncStatus?.status === 'pending') && (
                            <div style={{ marginBottom: 16 }}>
                              <Alert type="info" showIcon icon={<SyncOutlined spin />} style={{ marginBottom: 8 }} message={collabSyncStatus?.status === 'pending' ? '正在启动同步任务...' : '同步进行中...'} />
                              {collabSyncStatus?.status === 'running' && collabSyncStatus?.total > 0 && (
                                <div style={{ marginTop: 8 }}>
                                  <Progress
                                    percent={Math.round((collabSyncStatus.processed / collabSyncStatus.total) * 100)}
                                    status="active"
                                    format={() => `${collabSyncStatus.processed}/${collabSyncStatus.total} 论文，${collabSyncStatus.collaborations} 条合作关系`}
                                  />
                                </div>
                              )}
                            </div>
                          )}
                          <Space>
                            <Button type="primary" icon={<SyncOutlined spin={collabSyncStatus?.status === 'running'} />} onClick={handleSyncAllCollaborations} loading={collabSyncStatus?.status === 'running'} disabled={collabSyncStatus?.status === 'running'}>
                              {collabSyncStatus?.status === 'running' ? '同步中...' : '批量同步所有学者'}
                            </Button>
                            <Button icon={<ReloadOutlined />} onClick={loadCollabSyncStatus} loading={collabSyncLoading}>刷新状态</Button>
                          </Space>
                        </Spin>
                      </Card>
                    ),
                  },
                  {
                    key: 'embeddings',
                    label: <span><CloudUploadOutlined /> 向量生成</span>,
                    children: (
                      <Card>
                        <Spin spinning={embeddingLoading}>
                          <Alert
                            message="向量嵌入说明"
                            description="生成人才向量嵌入用于语义搜索和智能推荐。需要先配置 LLM API。生成过程为后台异步执行，耗时取决于人才数量。"
                            type="info"
                            showIcon
                            style={{ marginBottom: 24 }}
                          />
                          <Row gutter={16} style={{ marginBottom: 24 }}>
                            <Col span={6}>
                              <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                                <Statistic title="人才总数" value={embeddingStatus?.total_talents || 0} />
                              </Card>
                            </Col>
                            <Col span={6}>
                              <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                                <Statistic title="已生成向量" value={embeddingStatus?.embedded_talents || 0} valueStyle={{ color: '#52c41a' }} />
                              </Card>
                            </Col>
                            <Col span={6}>
                              <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                                <Statistic title="待生成" value={embeddingStatus?.pending_talents || 0} valueStyle={{ color: '#faad14' }} />
                              </Card>
                            </Col>
                            <Col span={6}>
                              <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                                <Statistic title="覆盖率" value={embeddingStatus?.progress_percent || 0} suffix="%" />
                              </Card>
                            </Col>
                          </Row>
                          {(embeddingProgress?.status === 'running' || embeddingProgress?.status === 'pending') && (
                            <Alert
                              type="info"
                              showIcon
                              icon={<SyncOutlined spin />}
                              style={{ marginBottom: 16 }}
                              message={embeddingProgress?.status === 'pending' ? '正在启动向量生成...' : '向量生成进行中...'}
                              description={
                                <div>
                                  <Progress
                                    percent={embeddingProgress?.total > 0 ? Math.round((embeddingProgress.processed / embeddingProgress.total) * 100) : 0}
                                    status="active"
                                  />
                                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                                    <Text type="secondary">
                                      已处理 {embeddingProgress?.processed.toLocaleString() || 0} / {embeddingProgress?.total.toLocaleString() || 0} 位人才
                                    </Text>
                                    {embeddingProgress?.failed > 0 && (
                                      <Text type="danger">失败 {embeddingProgress.failed}</Text>
                                    )}
                                  </Space>
                                </div>
                              }
                            />
                          )}
                          {embeddingProgress?.status === 'completed' && (
                            <Alert type="success" showIcon icon={<CheckCircleOutlined />} style={{ marginBottom: 16 }} message="向量生成完成" description={`成功处理 ${embeddingProgress.processed} 位人才`} />
                          )}
                          {embeddingProgress?.status === 'error' && (
                            <Alert type="error" showIcon style={{ marginBottom: 16 }} message="向量生成失败" />
                          )}
                          <Space>
                            <Button
                              type="primary"
                              icon={<SyncOutlined spin={embeddingProgress?.status === 'running'} />}
                              onClick={() => handleGenerateEmbeddings(false)}
                              loading={embeddingProgress?.status === 'running'}
                              disabled={embeddingProgress?.status === 'running'}
                            >
                              {embeddingProgress?.status === 'running' ? '生成中...' : '生成向量'}
                            </Button>
                            <Button danger onClick={() => handleGenerateEmbeddings(true)} disabled={embeddingProgress?.status === 'running'}>
                              强制重新生成
                            </Button>
                            {embeddingProgress?.status === 'running' && (
                              <Button onClick={handleCancelEmbeddingGeneration}>取消</Button>
                            )}
                            <Button icon={<ReloadOutlined />} onClick={loadEmbeddingStatus} loading={embeddingLoading}>刷新状态</Button>
                          </Space>
                        </Spin>
                      </Card>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: 'llm',
            label: <span><ApiOutlined /> LLM 配置</span>,
            children: (
              <Card>
                <Spin spinning={llmLoading}>
                  <Alert
                    message="LLM 配置说明"
                    description="配置 LLM API 以启用岗位匹配、智能推荐等功能。API Key 将被加密存储，前端仅显示脱敏值。"
                    type="info"
                    showIcon
                    style={{ marginBottom: 24 }}
                  />
                  <Form
                    form={llmForm}
                    layout="vertical"
                    onFinish={handleSaveLLMConfig}
                    initialValues={{ enabled: false, provider: 'deepseek', model: 'deepseek-chat', timeout: 60 }}
                  >
                    <Row gutter={24}>
                      <Col span={12}>
                        <Form.Item name="enabled" label="启用 LLM" valuePropName="checked">
                          <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="provider" label="服务商">
                          <Select options={[
                            { value: 'deepseek', label: 'DeepSeek' },
                            { value: 'openai', label: 'OpenAI' },
                            { value: 'zhipu', label: '智谱 AI' },
                            { value: 'qwen', label: '通义千问' },
                            { value: 'minimax', label: 'MiniMax' },
                            { value: 'custom', label: '自定义' },
                          ]} />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={24}>
                      <Col span={12}>
                        <Form.Item name="api_key" label="API Key">
                          <Input.Password placeholder={llmConfig?.api_key_masked || '请输入 API Key'} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="api_base" label="API 地址（可选）">
                          <Input placeholder="留空使用默认地址" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={24}>
                      <Col span={12}>
                        <Form.Item name="model" label="对话模型">
                          <Input placeholder="如 deepseek-chat, gpt-4o" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="embedding_model" label="嵌入模型">
                          <Input placeholder="如 text-embedding-3-small" />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Row gutter={24}>
                      <Col span={12}>
                        <Form.Item
                          name="embedding_api_base"
                          label="嵌入 API 地址"
                          tooltip="如果嵌入模型使用不同的 API 服务，请填写此地址。留空则使用上方的 API 地址。"
                        >
                          <Input placeholder="如 https://api.openai.com/v1" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="timeout" label="超时时间（秒）">
                          <InputNumber min={10} max={300} style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>
                    <Form.Item>
                      <Space>
                        <Button type="primary" htmlType="submit" loading={llmLoading}>保存配置</Button>
                        <Button onClick={handleTestLLM} loading={testingLLM} icon={<ApiOutlined />}>测试连接</Button>
                      </Space>
                    </Form.Item>
                  </Form>
                  {testResult && (
                    <Alert
                      message={testResult.success ? '连接成功' : '连接失败'}
                      description={testResult.message}
                      type={testResult.success ? 'success' : 'error'}
                      showIcon
                      icon={testResult.success ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
                      style={{ marginTop: 16 }}
                    />
                  )}
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
        <Alert message="勾选需要采集的顶会顶刊" type="info" showIcon style={{ marginBottom: 16 }} />
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
              </span>
            )}
            listStyle={{ width: 350, height: 400 }}
            showSearch
            locale={{ itemUnit: '个', itemsUnit: '个', searchPlaceholder: '搜索...', notFoundContent: '暂无数据' }}
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
                <Tag key={v.id} color={getVenueTypeConfig(v.type).color}>{v.name || v.id}</Tag>
              ))}
              {(selectedElement?.collect_sources?.length || 0) > 5 && <Tag>+{selectedElement!.collect_sources!.length - 5}</Tag>}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="数据类型">学者、论文、机构</Descriptions.Item>
          <Descriptions.Item label="时间范围">
            <Space>
              <Select value={startYear} onChange={(value) => { setStartYear(value); if (endYear !== null && endYear < value) setEndYear(null) }} style={{ width: 120 }} options={getStartYearOptions()} />
              <Text>至</Text>
              <Select value={endYear} onChange={setEndYear} style={{ width: 120 }} options={getEndYearOptions(startYear)} placeholder="至今" />
            </Space>
          </Descriptions.Item>
        </Descriptions>
      </Modal>

      {/* Task Detail Modal */}
      <Modal
        title="任务详情"
        open={taskDetailVisible}
        onCancel={() => setTaskDetailVisible(false)}
        footer={<Button onClick={() => setTaskDetailVisible(false)}>关闭</Button>}
        width={800}
      >
        {selectedTask && (
          <>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="任务编码">{selectedTask.task_code}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Badge status={getTaskStatusConfig(selectedTask.status).status} text={getTaskStatusConfig(selectedTask.status).label} />
              </Descriptions.Item>
              <Descriptions.Item label="技术要素">{selectedTask.tech_element_name}</Descriptions.Item>
              <Descriptions.Item label="时间范围">{selectedTask.start_year}年 ~ {selectedTask.end_year ? `${selectedTask.end_year}年` : '至今'}</Descriptions.Item>
              <Descriptions.Item label="进度" span={2}>
                <Progress percent={selectedTask.progress_percent} status={selectedTask.status === 'failed' ? 'exception' : selectedTask.status === 'completed' ? 'success' : 'active'} />
              </Descriptions.Item>
            </Descriptions>

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

            <Card title="时间信息" size="small" style={{ marginTop: 16 }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="触发时间">{formatUTCToLocal(selectedTask.triggered_at)}</Descriptions.Item>
                <Descriptions.Item label="开始时间">{formatUTCToLocal(selectedTask.started_at)}</Descriptions.Item>
                <Descriptions.Item label="完成时间">{formatUTCToLocal(selectedTask.completed_at)}</Descriptions.Item>
                <Descriptions.Item label="耗时">{selectedTask.result_summary?.total_duration || '-'}</Descriptions.Item>
              </Descriptions>
            </Card>

            {selectedTask.result_summary?.venue_details && selectedTask.result_summary.venue_details.length > 0 && (
              <Card title="采集源详情" size="small" style={{ marginTop: 16 }}>
                <Table
                  dataSource={selectedTask.result_summary.venue_details}
                  rowKey="venue_id"
                  size="small"
                  pagination={false}
                  columns={[
                    { title: '采集源', dataIndex: 'venue_name', key: 'venue_name', ellipsis: true },
                    { title: '状态', dataIndex: 'status', key: 'status', width: 80 },
                    { title: '获取', dataIndex: 'fetched', key: 'fetched', width: 60, align: 'center' },
                    { title: '入库', dataIndex: 'saved', key: 'saved', width: 60, align: 'center' },
                    { title: '耗时', dataIndex: 'duration', key: 'duration', width: 80 },
                    { title: '错误', dataIndex: 'error', key: 'error', ellipsis: true, render: (e: string) => e ? <Text type="danger">{e}</Text> : '-' },
                  ]}
                />
              </Card>
            )}

            {selectedTask.error_message && (
              <Alert type="error" message="错误信息" description={selectedTask.error_message} style={{ marginTop: 16 }} showIcon />
            )}
          </>
        )}
      </Modal>
    </div>
  )
}

export default SystemConfigPage
