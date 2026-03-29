/**
 * 采集配置管理页面 - MVP v1.1 简化版 (重构版)
 *
 * 已拆分的组件:
 * - TechElementTable: 技术要素配置表格
 * - VenueConfigModal: 顶会顶刊配置弹窗
 * - CollectTaskTable: 采集任务表格
 * - TaskDetailModal: 任务详情弹窗
 * - CollectConfirmModal: 采集确认弹窗
 */
import { useEffect, useState } from 'react'
import { Card, Typography, Tabs, message } from 'antd'
import { SettingOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { api } from '../services/api'
import type { VenueItem, VenueBinding, TechElementCollect, CollectTask, TaskStatusConfig, CollectModeConfig, VenueTypeConfig } from '../types'
import {
  TechElementTable,
  VenueConfigModal,
  CollectTaskTable,
  TaskDetailModal,
  CollectConfirmModal,
} from '../components/collect'

const { Title } = Typography

// Status and mode mappings
const taskStatusMap: Record<string, TaskStatusConfig> = {
  pending: { label: '待执行', color: 'default', status: 'default' },
  running: { label: '执行中', color: 'processing', status: 'processing' },
  completed: { label: '已完成', color: 'success', status: 'success' },
  failed: { label: '失败', color: 'error', status: 'error' },
  cancelled: { label: '已取消', color: 'warning', status: 'warning' },
}

const collectModeMap: Record<string, CollectModeConfig> = {
  full: { label: '全量采集', color: 'blue' },
  incremental: { label: '增量采集', color: 'green' },
}

const venueTypeMap: Record<string, VenueTypeConfig> = {
  conference: { label: '会议', color: 'blue' },
  journal: { label: '期刊', color: 'purple' },
}

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

const CollectPageRefactored: React.FC = () => {
  // Tech Elements state
  const [techElements, setTechElements] = useState<TechElementCollect[]>([])
  const [techElementsLoading, setTechElementsLoading] = useState(false)

  // Venue selection state
  const [venueModalVisible, setVenueModalVisible] = useState(false)
  const [selectedElement, setSelectedElement] = useState<TechElementCollect | null>(null)
  const [allVenues, setAllVenues] = useState<VenueItem[]>([])
  const [selectedVenueIds, setSelectedVenueIds] = useState<string[]>([])
  const [venueLoading, setVenueLoading] = useState(false)

  // Collect confirm state
  const [collectModalVisible, setCollectModalVisible] = useState(false)
  const [collectMode, setCollectMode] = useState<string>('full')

  // Task state
  const [tasks, setTasks] = useState<CollectTask[]>([])
  const [taskTotal, setTaskTotal] = useState(0)
  const [taskPage, setTaskPage] = useState(1)
  const [tasksLoading, setTasksLoading] = useState(false)

  // Task detail state
  const [taskDetailVisible, setTaskDetailVisible] = useState(false)
  const [selectedTask, setSelectedTask] = useState<CollectTask | null>(null)

  const [activeTab, setActiveTab] = useState('tech-elements')

  useEffect(() => {
    if (activeTab === 'tech-elements') {
      loadTechElements()
    } else {
      loadTasks()
    }
  }, [activeTab])

  // Auto-refresh for running tasks
  useEffect(() => {
    if (activeTab === 'tasks' && tasks.some(t => t.status === 'running')) {
      const interval = setInterval(() => {
        loadTasks()
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [activeTab, tasks])

  // Tech Element operations
  const loadTechElements = async () => {
    setTechElementsLoading(true)
    try {
      const response = await api.collect.listTechElements()
      setTechElements(response.data.items || [])
    } catch (error) {
      message.error('加载技术要素失败')
    } finally {
      setTechElementsLoading(false)
    }
  }

  // Load tech element's bound venues
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
    } catch (error) {
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

  // Save venue bindings
  const handleSaveVenues = async () => {
    if (!selectedElement) return

    try {
      await api.venues.batchCreateBindings(
        selectedElement.tech_element_id,
        selectedVenueIds.map(id => parseInt(id, 10))
      )
      message.success('配置更新成功')
      setVenueModalVisible(false)
      loadTechElements()
    } catch (error) {
      message.error(getErrorMessage(error, '更新失败'))
    }
  }

  // Open collect modal
  const handleOpenCollect = (element: TechElementCollect) => {
    setSelectedElement(element)
    setCollectMode('full')
    setCollectModalVisible(true)
  }

  // Trigger collect
  const handleTriggerCollect = async () => {
    if (!selectedElement) return

    try {
      await api.collect.triggerTask({
        tech_element_id: selectedElement.tech_element_id,
        collect_mode: collectMode,
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
    setTasksLoading(true)
    try {
      const response = await api.collect.listTasks({ page: taskPage, page_size: 10 })
      setTasks(response.data.items || [])
      setTaskTotal(response.data.total || 0)
    } catch (error) {
      message.error('加载任务列表失败')
    } finally {
      setTasksLoading(false)
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

  const handleRefreshTask = () => {
    loadTasks()
    // Refresh selected task
    const updated = tasks.find(t => t.task_id === selectedTask?.task_id)
    if (updated) setSelectedTask(updated)
  }

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
                <TechElementTable
                  data={techElements}
                  loading={techElementsLoading}
                  venueTypeMap={venueTypeMap}
                  onConfigVenues={handleConfigVenues}
                  onStartCollect={handleOpenCollect}
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
                <CollectTaskTable
                  data={tasks}
                  loading={tasksLoading}
                  total={taskTotal}
                  page={taskPage}
                  pageSize={10}
                  taskStatusMap={taskStatusMap}
                  collectModeMap={collectModeMap}
                  onViewTask={handleViewTask}
                  onCancelTask={handleCancelTask}
                  onDeleteTask={handleDeleteTask}
                  onPageChange={(p) => {
                    setTaskPage(p)
                    loadTasks()
                  }}
                />
              </Card>
            ),
          },
        ]}
      />

      {/* Venue Config Modal */}
      <VenueConfigModal
        visible={venueModalVisible}
        element={selectedElement}
        allVenues={allVenues}
        selectedVenueIds={selectedVenueIds}
        loading={venueLoading}
        venueTypeMap={venueTypeMap}
        onSelectionChange={setSelectedVenueIds}
        onSave={handleSaveVenues}
        onCancel={() => setVenueModalVisible(false)}
      />

      {/* Collect Confirm Modal */}
      <CollectConfirmModal
        visible={collectModalVisible}
        element={selectedElement}
        collectMode={collectMode}
        venueTypeMap={venueTypeMap}
        onModeChange={setCollectMode}
        onConfirm={handleTriggerCollect}
        onCancel={() => setCollectModalVisible(false)}
      />

      {/* Task Detail Modal */}
      <TaskDetailModal
        visible={taskDetailVisible}
        task={selectedTask}
        taskStatusMap={taskStatusMap}
        collectModeMap={collectModeMap}
        onRefresh={handleRefreshTask}
        onCancelTask={handleCancelTask}
        onDeleteTask={handleDeleteTask}
        onClose={() => setTaskDetailVisible(false)}
      />
    </div>
  )
}

export default CollectPageRefactored
