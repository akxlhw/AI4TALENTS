import { useCallback, useEffect, useRef, useState } from 'react'
import { message } from 'antd'
import { api } from '../../../../services/api'
import { queryClient, queryKeys } from '../../../../hooks/queryClient'
import { TIME_RANGE_CONFIG } from '../../../../constants'
import type { VenueItem, VenueBinding, TechDomainCollect, CollectTask } from '../../../../types'
import { getErrorMessage } from '../utils'
import { usePolling } from '../../../../hooks/usePolling'

export const useCollectConfig = (initialSubTab?: string) => {
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
  const [collectSubTab, setCollectSubTab] = useState(initialSubTab ?? 'tech-domains')
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

  const [genealogySyncStatus, setGenealogySyncStatus] = useState<{
    status: string
    processed: number
    total: number
    edges: number
    current_phase?: string
  } | null>(null)
  const [genealogySyncLoading, setGenealogySyncLoading] = useState(false)

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
        newTasks
          .filter((t: CollectTask) => t.status === 'running')
          .map((t: CollectTask) => t.task_id)
      )
      const completedTaskIds = [...runningTaskIdsRef.current].filter(
        (id: number) =>
          !currentRunningIds.has(id) &&
          newTasks.some((t: CollectTask) => t.task_id === id && t.status === 'completed')
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
      await api.venues.batchCreateBindings(
        selectedDomain.tech_domain_id,
        selectedVenueIds.map((id) => parseInt(id, 10))
      )
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

  const handleStartYearChange = (value: number) => {
    setStartYear(value)
    if (endYear !== null && endYear < value) setEndYear(null)
  }

  const handleTaskPageChange = (p: number) => {
    setTaskPage(p)
    loadTasks()
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
      // Await so startup failures surface instead of a fire-and-forget call
      await api.talents.syncCollaborations()
      message.success('同步任务已启动')
      // Status flips to 'running' → usePolling below picks it up until terminal
      setCollabSyncStatus({ status: 'running', processed: 0, total: 0, collaborations: 0 })
    } catch (error) {
      message.error(getErrorMessage(error, '启动同步失败'))
      setCollabSyncStatus(null)
    }
  }

  const loadGenealogySyncStatus = async () => {
    setGenealogySyncLoading(true)
    try {
      const response = await api.talents.getGenealogySyncStatus()
      setGenealogySyncStatus(response.data)
    } catch {
      message.error('加载族谱计算状态失败')
    } finally {
      setGenealogySyncLoading(false)
    }
  }

  const handleSyncGenealogy = async () => {
    try {
      setGenealogySyncStatus({ status: 'pending', processed: 0, total: 0, edges: 0 })
      message.info('正在启动族谱计算任务...')
      await api.talents.syncGenealogy()
      message.success('族谱计算任务已启动')
      // Status flips to 'running' → usePolling below picks it up until terminal
      setGenealogySyncStatus({ status: 'running', processed: 0, total: 0, edges: 0 })
    } catch (error) {
      message.error(getErrorMessage(error, '启动族谱计算失败'))
      setGenealogySyncStatus(null)
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
      // Status flips to 'running' → usePolling below picks it up until terminal
      setEmbeddingProgress({
        status: 'running',
        processed: 0,
        total: response.data.total_talents,
        failed: 0,
      })
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
      // Status flips to 'running' → usePolling below picks it up until terminal
      setOsEmbeddingProgress({ status: 'running', processed: 0, total: 0, failed: 0 })
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
    if (collectSubTab === 'tasks' && tasks.some((t) => t.status === 'running')) {
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

  // Declarative polling for long-running sync/generation tasks. `enabled` is
  // derived from the running status: polling stops on any terminal state,
  // resumes automatically when revisiting the page mid-task, and always
  // cleans up on unmount (no more hard timeout leaving a stuck "running" UI).
  usePolling({
    interval: 1000,
    enabled: collabSyncStatus?.status === 'running',
    callback: async () => {
      try {
        const res = await api.talents.getCollaborationSyncStatus()
        const progress = res.data.sync_progress
        setCollabSyncStatus(progress)
        setCollabDataStatus(res.data.data_status)
        if (progress.status === 'completed') {
          message.success(
            `同步完成！处理 ${progress.processed} 篇论文，创建 ${progress.collaborations} 条合作关系`
          )
        }
      } catch {
        /* transient poll errors are ignored */
      }
    },
  })

  usePolling({
    interval: 2000,
    enabled: genealogySyncStatus?.status === 'running',
    callback: async () => {
      try {
        const res = await api.talents.getGenealogySyncStatus()
        const progress = res.data
        setGenealogySyncStatus(progress)
        if (progress.status === 'completed') {
          message.success(
            `族谱计算完成！处理 ${progress.processed} 篇论文，推断 ${progress.edges} 条关系`
          )
        }
      } catch {
        /* transient poll errors are ignored */
      }
    },
  })

  usePolling({
    interval: 2000,
    enabled: embeddingProgress?.status === 'running',
    callback: async () => {
      try {
        const res = await api.embeddings.getProgress()
        setEmbeddingProgress(res.data)
        if (res.data.status === 'completed' || res.data.status === 'error') {
          loadEmbeddingStatus()
          if (res.data.status === 'completed') {
            message.success(`向量生成完成！处理 ${res.data.processed} 位人才`)
          }
        }
      } catch {
        /* transient poll errors are ignored */
      }
    },
  })

  usePolling({
    interval: 2000,
    enabled: osEmbeddingProgress?.status === 'running',
    callback: async () => {
      try {
        const res = await api.openSource.getEmbeddingProgress()
        setOsEmbeddingProgress(res.data)
        if (['completed', 'error', 'cancelled'].includes(res.data.status)) {
          loadOsEmbeddingStatus()
          if (res.data.status === 'completed') {
            message.success(`开源向量生成完成！处理 ${res.data.processed} 位开发者`)
          }
        }
      } catch {
        /* transient poll errors are ignored */
      }
    },
  })

  return {
    techDomains,
    loading,
    collectSubTab,
    setCollectSubTab,
    tasks,
    taskTotal,
    taskPage,
    selectedTask,
    taskDetailVisible,
    setTaskDetailVisible,
    handleViewTask,
    handleCancelTask,
    handleDeleteTask,
    handleTaskPageChange,
    selectedDomain,
    venueModalVisible,
    setVenueModalVisible,
    allVenues,
    selectedVenueIds,
    setSelectedVenueIds,
    venueLoading,
    handleConfigVenues,
    handleSaveVenues,
    collectModalVisible,
    setCollectModalVisible,
    startYear,
    endYear,
    setEndYear,
    handleStartYearChange,
    handleOpenCollect,
    handleTriggerCollect,
    collabSyncStatus,
    collabDataStatus,
    collabSyncLoading,
    loadCollabSyncStatus,
    handleSyncAllCollaborations,
    genealogySyncStatus,
    genealogySyncLoading,
    loadGenealogySyncStatus,
    handleSyncGenealogy,
    embeddingStatus,
    embeddingProgress,
    embeddingLoading,
    loadEmbeddingStatus,
    handleGenerateEmbeddings,
    handleCancelEmbeddingGeneration,
    osEmbeddingStatus,
    osEmbeddingProgress,
    osEmbeddingLoading,
    loadOsEmbeddingStatus,
    handleGenerateOsEmbeddings,
    handleCancelOsEmbeddingGeneration,
  }
}
