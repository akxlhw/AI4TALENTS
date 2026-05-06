import { useCallback, useEffect, useRef, useState } from 'react'
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
  CloudUploadOutlined,
  CheckCircleOutlined,
  GithubOutlined,
} from '@ant-design/icons'
import { api } from '../../../services/api'
import { queryClient, queryKeys } from '../../../hooks/queryClient'
import {
  getTaskStatusConfig,
  getVenueTypeConfig,
  getStartYearOptions,
  getEndYearOptions,
  TIME_RANGE_CONFIG,
} from '../../../constants'
import type { VenueItem, VenueBinding, TechDomainCollect, CollectTask } from '../../../types'
import { formatUTCToLocal } from '../../../utils/datetime'
import { formatNumber } from '../../../utils/format'
import { getErrorMessage } from './utils'
import OSRepoConfigSubTab from './os-repo-config-sub-tab'
import OSCollectTaskSubTab from './os-collect-task-sub-tab'

const { Text } = Typography

const CollectConfigTab: React.FC = () => {
  // ========== State ==========
  const [techDomains, setTechDomains] = useState<TechDomainCollect[]>([])
  const [venueModalVisible, setVenueModalVisible] = useState(false)
  const [collectModalVisible, setCollectModalVisible] = useState(false)
  const [selectedDomain, setSelectedDomain] = useState<TechDomainCollect | null>(null)
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
  const [collectSubTab, setCollectSubTab] = useState('tech-domains')
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

  const [osEmbeddingStatus, setOsEmbeddingStatus] = useState<{
    total_developers: number
    embedded_count: number
    pending_count: number
    progress_percent: number
    dimension: number
    model_name: string
  } | null>(null)
  const [osEmbeddingProgress, setOsEmbeddingProgress] = useState<{
    status: string
    processed: number
    total: number
    failed: number
  } | null>(null)
  const [osEmbeddingLoading, setOsEmbeddingLoading] = useState(false)

  // ========== Functions ==========
  const loadTasks = useCallback(async () => {
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
  }, [taskPage])

  const loadTechDomains = async () => {
    setLoading(true)
    try {
      const response = await api.collect.listTechDomains()
      setTechDomains(response.data.items || [])
    } catch {
      message.error('加载技术领域失败')
    } finally {
      setLoading(false)
    }
  }

  const loadTechDomainVenues = async (techDomainId: number) => {
    setVenueLoading(true)
    try {
      const response = await api.venues.getTechDomainBindings(techDomainId)
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
      const enabledIds = bindings.filter((b: VenueBinding) => b.is_enabled).map((b: VenueBinding) => String(b.venue_id))
      setSelectedVenueIds(enabledIds)
    } catch {
      message.error('加载顶会顶刊列表失败')
      setAllVenues([])
      setSelectedVenueIds([])
    } finally {
      setVenueLoading(false)
    }
  }

  const handleConfigVenues = async (domain: TechDomainCollect) => {
    setSelectedDomain(domain)
    setSelectedVenueIds([])
    setAllVenues([])
    setVenueModalVisible(true)
    await loadTechDomainVenues(domain.tech_domain_id)
  }

  const handleSaveVenues = async () => {
    if (!selectedDomain) return
    try {
      await api.venues.batchCreateBindings(selectedDomain.tech_domain_id, selectedVenueIds.map(id => parseInt(id, 10)))
      message.success('配置更新成功')
      setVenueModalVisible(false)
      loadTechDomains()
    } catch (error) {
      message.error(getErrorMessage(error, '更新失败'))
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
      setCollectSubTab('tasks')
      loadTasks()
    } catch (error) {
      message.error(getErrorMessage(error, '启动失败'))
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

  const loadEmbeddingStatus = async () => {
    setEmbeddingLoading(true)
    try {
      const response = await api.embeddings.getStatus()
      setEmbeddingStatus(response.data)
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

  const loadOsEmbeddingStatus = async () => {
    setOsEmbeddingLoading(true)
    try {
      const response = await api.openSource.getEmbeddingStatus()
      setOsEmbeddingStatus(response.data)
      const progressResponse = await api.openSource.getEmbeddingProgress()
      setOsEmbeddingProgress(progressResponse.data)
    } catch {
      message.error('加载开源嵌入状态失败')
    } finally {
      setOsEmbeddingLoading(false)
    }
  }

  const handleGenerateOsEmbeddings = async (force: boolean = false) => {
    try {
      setOsEmbeddingProgress({ status: 'pending', processed: 0, total: 0, failed: 0 })
      message.info('正在启动开源向量生成任务...')
      const response = await api.openSource.generateEmbeddings(50, force)
      message.success(response.data.message)
      setOsEmbeddingProgress({ status: 'running', processed: 0, total: 0, failed: 0 })

      const pollInterval = setInterval(async () => {
        try {
          const progressResponse = await api.openSource.getEmbeddingProgress()
          setOsEmbeddingProgress(progressResponse.data)
          if (progressResponse.data.status === 'completed' || progressResponse.data.status === 'error' || progressResponse.data.status === 'cancelled') {
            clearInterval(pollInterval)
            loadOsEmbeddingStatus()
            if (progressResponse.data.status === 'completed') {
              message.success(`开源向量生成完成！处理 ${progressResponse.data.processed} 位开发者`)
            }
          }
        } catch { /* ignore */ }
      }, 2000)
      setTimeout(() => clearInterval(pollInterval), 600000)
    } catch (error) {
      message.error(getErrorMessage(error, '启动开源向量生成失败'))
      setOsEmbeddingProgress(null)
    }
  }

  const handleCancelOsEmbeddingGeneration = async () => {
    try {
      await api.openSource.cancelEmbeddingGeneration()
      message.success('已取消开源向量生成任务')
      setOsEmbeddingProgress(null)
      loadOsEmbeddingStatus()
    } catch (error) {
      message.error(getErrorMessage(error, '取消失败'))
    }
  }

  // Auto-refresh for running tasks
  useEffect(() => {
    if (collectSubTab === 'tasks' && tasks.some(t => t.status === 'running')) {
      const interval = setInterval(() => {
        loadTasks()
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [collectSubTab, tasks, loadTasks])

  // Load data on sub tab change
  useEffect(() => {
    if (collectSubTab === 'tech-domains') {
      loadTechDomains()
    } else if (collectSubTab === 'tasks') {
      loadTasks()
    } else if (collectSubTab === 'collaborations') {
      loadCollabSyncStatus()
    } else if (collectSubTab === 'embeddings') {
      loadEmbeddingStatus()
      loadOsEmbeddingStatus()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [collectSubTab])

  // ========== Table Columns ==========
  const elementColumns = [
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
        if (sources.length === 0) return <Text type="secondary">未配置</Text>
        const displayVenues = sources.slice(0, 10)
        return (
          <Space size={[4, 4]} wrap>
            {displayVenues.map((v) => (
              <Tooltip key={v.id} title={v.name || v.id}>
                <Tag color={getVenueTypeConfig(v.type).color}>{v.id.toUpperCase()}</Tag>
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
      render: (count: number) => <Badge count={count} showZero color="blue" style={{ marginRight: 8 }} />,
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: TechDomainCollect) => (
        <Space>
          <Tooltip title="配置顶会顶刊">
            <Button type="link" size="small" icon={<SettingOutlined />} onClick={() => handleConfigVenues(record)}>配置</Button>
          </Tooltip>
          <Tooltip title="启动采集">
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleOpenCollect(record)}
              disabled={!record.collect_sources || record.collect_sources.length === 0}
            >采集</Button>
          </Tooltip>
        </Space>
      ),
    },
  ]

  const taskColumns = [
    { title: '任务编码', dataIndex: 'task_code', key: 'task_code', width: 180 },
    { title: '技术领域', dataIndex: 'tech_domain_name', key: 'tech_domain_name' },
    {
      title: '顶刊顶会',
      key: 'venues',
      render: (_: unknown, record: CollectTask) => {
        const sources = record.venue_snapshot || []
        if (sources.length === 0) return <Text type="secondary">-</Text>
        const displayVenues = sources.slice(0, 5)
        return (
          <Space size={[4, 4]} wrap>
            {displayVenues.map((v) => (
              <Tooltip key={v.id} title={v.name || v.id}><Tag>{v.id.toUpperCase()}</Tag></Tooltip>
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
    <div>
      <Tabs
        activeKey={collectSubTab}
        onChange={setCollectSubTab}
        destroyInactiveTabPane
        items={[
          {
            key: 'tech-domains',
            label: <span><SettingOutlined /> 技术领域配置</span>,
            children: (
              <Card>
                <Spin spinning={loading}>
                  <Table
                    dataSource={techDomains}
                    columns={elementColumns}
                    rowKey="tech_domain_id"
                    pagination={false}
                    locale={{ emptyText: <Empty description="暂无技术领域数据" /> }}
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
            key: 'opensource-repos',
            label: <span><GithubOutlined /> 开源仓库配置</span>,
            children: <OSRepoConfigSubTab />,
          },
          {
            key: 'opensource-tasks',
            label: <span><PlayCircleOutlined /> 开源采集任务</span>,
            children: <OSCollectTaskSubTab />,
          },
          {
            key: 'embeddings',
            label: <span><CloudUploadOutlined /> 向量生成</span>,
            children: (
              <Tabs
                type="card"
                items={[
                  {
                    key: 'academic',
                    label: '学术人才库',
                    children: (
                      <Card>
                        <Spin spinning={embeddingLoading}>
                          <Alert
                            message="学术人才向量嵌入"
                            description="生成学术人才向量嵌入用于语义搜索和智能推荐。需要先配置 LLM API。生成过程为后台异步执行，耗时取决于人才数量。"
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
                                      已处理 {formatNumber(embeddingProgress?.processed)} / {formatNumber(embeddingProgress?.total)} 位人才
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
                  {
                    key: 'open-source',
                    label: '开源人才库',
                    children: (
                      <Card>
                        <Spin spinning={osEmbeddingLoading}>
                          <Alert
                            message="开源人才向量嵌入"
                            description={`生成开源开发者向量嵌入用于语义搜索和智能推荐。当前模型：${osEmbeddingStatus?.model_name || '未配置'}。生成过程为后台异步执行，耗时取决于开发者数量。`}
                            type="info"
                            showIcon
                            style={{ marginBottom: 24 }}
                          />
                          <Row gutter={16} style={{ marginBottom: 24 }}>
                            <Col span={6}>
                              <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                                <Statistic title="开发者总数" value={osEmbeddingStatus?.total_developers || 0} />
                              </Card>
                            </Col>
                            <Col span={6}>
                              <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                                <Statistic title="已生成向量" value={osEmbeddingStatus?.embedded_count || 0} valueStyle={{ color: '#52c41a' }} />
                              </Card>
                            </Col>
                            <Col span={6}>
                              <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                                <Statistic title="待生成" value={osEmbeddingStatus?.pending_count || 0} valueStyle={{ color: '#faad14' }} />
                              </Card>
                            </Col>
                            <Col span={6}>
                              <Card size="small" bordered={false} style={{ background: '#f5f5f5' }}>
                                <Statistic title="覆盖率" value={osEmbeddingStatus?.progress_percent || 0} suffix="%" />
                              </Card>
                            </Col>
                          </Row>
                          {(osEmbeddingProgress?.status === 'running' || osEmbeddingProgress?.status === 'pending') && (
                            <Alert
                              type="info"
                              showIcon
                              icon={<SyncOutlined spin />}
                              style={{ marginBottom: 16 }}
                              message={osEmbeddingProgress?.status === 'pending' ? '正在启动向量生成...' : '向量生成进行中...'}
                              description={
                                <div>
                                  <Progress
                                    percent={osEmbeddingProgress?.total > 0 ? Math.round((osEmbeddingProgress.processed / osEmbeddingProgress.total) * 100) : 0}
                                    status="active"
                                  />
                                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                                    <Text type="secondary">
                                      已处理 {formatNumber(osEmbeddingProgress?.processed)} / {formatNumber(osEmbeddingProgress?.total)} 位开发者
                                    </Text>
                                    {osEmbeddingProgress?.failed > 0 && (
                                      <Text type="danger">失败 {osEmbeddingProgress.failed}</Text>
                                    )}
                                  </Space>
                                </div>
                              }
                            />
                          )}
                          {osEmbeddingProgress?.status === 'completed' && (
                            <Alert type="success" showIcon icon={<CheckCircleOutlined />} style={{ marginBottom: 16 }} message="向量生成完成" description={`成功处理 ${osEmbeddingProgress.processed} 位开发者`} />
                          )}
                          {osEmbeddingProgress?.status === 'error' && (
                            <Alert type="error" showIcon style={{ marginBottom: 16 }} message="向量生成失败" />
                          )}
                          <Space>
                            <Button
                              type="primary"
                              icon={<SyncOutlined spin={osEmbeddingProgress?.status === 'running'} />}
                              onClick={() => handleGenerateOsEmbeddings(false)}
                              loading={osEmbeddingProgress?.status === 'running'}
                              disabled={osEmbeddingProgress?.status === 'running'}
                            >
                              {osEmbeddingProgress?.status === 'running' ? '生成中...' : '生成向量'}
                            </Button>
                            <Button danger onClick={() => handleGenerateOsEmbeddings(true)} disabled={osEmbeddingProgress?.status === 'running'}>
                              强制重新生成
                            </Button>
                            {osEmbeddingProgress?.status === 'running' && (
                              <Button onClick={handleCancelOsEmbeddingGeneration}>取消</Button>
                            )}
                            <Button icon={<ReloadOutlined />} onClick={loadOsEmbeddingStatus} loading={osEmbeddingLoading}>刷新状态</Button>
                          </Space>
                        </Spin>
                      </Card>
                    ),
                  },
                ]}
              />
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
        <Alert message="勾选需要采集的顶会顶刊" type="info" showIcon style={{ marginBottom: 16 }} />
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
            listStyle={{ width: 350, height: 400 }}
            showSearch
            locale={{ itemUnit: '个', itemsUnit: '个', searchPlaceholder: '搜索...', notFoundContent: '暂无数据' }}
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
                  <Tag color={getVenueTypeConfig(v.type).color}>{v.id.toUpperCase()}</Tag>
                </Tooltip>
              ))}
              {(selectedDomain?.collect_sources?.length || 0) > 5 && <Tag>+{selectedDomain!.collect_sources!.length - 5}</Tag>}
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
              <Descriptions.Item label="技术领域">{selectedTask.tech_domain_name}</Descriptions.Item>
              <Descriptions.Item label="时间范围">{selectedTask.start_year}年 ~ {selectedTask.end_year ? `${selectedTask.end_year}年` : '至今'}</Descriptions.Item>
              <Descriptions.Item label="当前阶段">{selectedTask.current_step || '-'}</Descriptions.Item>
              <Descriptions.Item label="进度">
                <Progress percent={selectedTask.progress_percent} status={selectedTask.status === 'failed' ? 'exception' : selectedTask.status === 'completed' ? 'success' : 'active'} style={{ minWidth: 120 }} />
              </Descriptions.Item>
            </Descriptions>

            <Card title="采集统计" size="small" style={{ marginTop: 16 }}>
              <Row gutter={16}>
                <Col span={4}><Statistic title="采集论文" value={selectedTask.total_records || 0} /></Col>
                <Col span={4}><Statistic title="获取作者" value={selectedTask.result_summary?.total_authors || selectedTask.processed_records || 0} /></Col>
                <Col span={4}><Statistic title="标准化作者" value={selectedTask.processed_records || 0} /></Col>
                <Col span={4}><Statistic title="标准化院校" value={selectedTask.skipped_records || 0} /></Col>
                <Col span={4}><Statistic title="入库人才" value={selectedTask.success_records || 0} valueStyle={{ color: '#52c41a' }} /></Col>
                <Col span={4}><Statistic title="更新人才" value={selectedTask.result_summary?.updated_talents || 0} /></Col>
              </Row>
              {selectedTask.result_summary && (
                <Row gutter={16} style={{ marginTop: 16 }}>
                  <Col span={4}><Statistic title="新建人才" value={selectedTask.result_summary.created_talents || 0} valueStyle={{ color: '#1890ff' }} /></Col>
                  <Col span={4}><Statistic title="技术标签" value={selectedTask.result_summary.created_tech_tags || 0} /></Col>
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
                    {
                      title: '采集源',
                      key: 'venue_id',
                      width: 120,
                      render: (_: unknown, record: { venue_id: number; venue_name: string }) => (
                        <Tooltip title={record.venue_name}>
                          <Text strong>{String(record.venue_id).toUpperCase()}</Text>
                        </Tooltip>
                      ),
                    },
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

export default CollectConfigTab
