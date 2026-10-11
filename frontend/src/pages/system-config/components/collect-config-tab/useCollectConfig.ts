import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { message } from 'antd'
import { api } from '../../../../services/api'
import { queryClient, queryKeys } from '../../../../hooks/queryClient'
import { TIME_RANGE_CONFIG } from '../../../../constants'
import type { VenueItem, VenueBinding, TechDomainCollect, CollectTask } from '../../../../types'
import { getErrorMessage } from '../utils'
import { usePolling } from '../../../../hooks/usePolling'
import '../../../../i18n/namespaces/system-config'

export const useCollectConfig = (initialSubTab?: string) => {
  const { t } = useTranslation(['systemConfig', 'common'])

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
      message.error(t('collectConfig.messages.loadTasksFailed'))
    } finally {
      setLoading(false)
    }
  }, [taskPage, t])

  const loadTechDomains = async () => {
    setLoading(true)
    try {
      const response = await api.collect.listTechDomains()
      setTechDomains(response.data.items || [])
    } catch {
      message.error(t('collectConfig.messages.loadTechDomainsFailed'))
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
      message.error(t('collectConfig.messages.loadVenuesFailed'))
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
        selectedVenueIds.map(id => parseInt(id, 10))
      )
      message.success(t('collectConfig.messages.venueConfigSaved'))
      setVenueModalVisible(false)
      loadTechDomains()
    } catch (error) {
      message.error(getErrorMessage(error, t('collectConfig.messages.updateFailed')))
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
      message.success(t('collectConfig.messages.collectStarted'))
      setCollectModalVisible(false)
      setCollectSubTab('tasks')
      loadTasks()
    } catch (error) {
      message.error(getErrorMessage(error, t('collectConfig.messages.startFailed')))
    }
  }

  const handleCancelTask = async (taskId: number) => {
    try {
      await api.collect.cancelTask(taskId)
      message.success(t('collectConfig.messages.taskCancelled'))
      loadTasks()
    } catch (error) {
      message.error(getErrorMessage(error, t('collectConfig.messages.cancelFailed')))
    }
  }

  const handleViewTask = (task: CollectTask) => {
    setSelectedTask(task)
    setTaskDetailVisible(true)
  }

  const handleDeleteTask = async (taskId: number) => {
    try {
      await api.collect.deleteTask(taskId)
      message.success(t('collectConfig.messages.taskDeleted'))
      setTaskDetailVisible(false)
      loadTasks()
    } catch (error) {
      message.error(getErrorMessage(error, t('collectConfig.messages.deleteFailed')))
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
      message.error(t('collectConfig.messages.loadSyncStatusFailed'))
    } finally {
      setCollabSyncLoading(false)
    }
  }

  const handleSyncAllCollaborations = async () => {
    try {
      setCollabSyncStatus({ status: 'pending', processed: 0, total: 0, collaborations: 0 })
      message.info(t('collectConfig.messages.syncStarting'))
      // Await so startup failures surface instead of a fire-and-forget call
      await api.talents.syncCollaborations()
      message.success(t('collectConfig.messages.syncStarted'))
      // Status flips to 'running' → usePolling below picks it up until terminal
      setCollabSyncStatus({ status: 'running', processed: 0, total: 0, collaborations: 0 })
    } catch (error) {
      message.error(getErrorMessage(error, t('collectConfig.messages.syncStartFailed')))
      setCollabSyncStatus(null)
    }
  }

  const loadGenealogySyncStatus = async () => {
    setGenealogySyncLoading(true)
    try {
      const response = await api.talents.getGenealogySyncStatus()
      setGenealogySyncStatus(response.data)
    } catch {
      message.error(t('collectConfig.messages.loadGenealogyStatusFailed'))
    } finally {
      setGenealogySyncLoading(false)
    }
  }

  const handleSyncGenealogy = async () => {
    try {
      setGenealogySyncStatus({ status: 'pending', processed: 0, total: 0, edges: 0 })
      message.info(t('collectConfig.messages.genealogyStarting'))
      await api.talents.syncGenealogy()
      message.success(t('collectConfig.messages.genealogyStarted'))
      // Status flips to 'running' → usePolling below picks it up until terminal
      setGenealogySyncStatus({ status: 'running', processed: 0, total: 0, edges: 0 })
    } catch (error) {
      message.error(getErrorMessage(error, t('collectConfig.messages.genealogyStartFailed')))
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
      message.error(t('collectConfig.messages.loadEmbeddingStatusFailed'))
    } finally {
      setEmbeddingLoading(false)
    }
  }

  const handleGenerateEmbeddings = async (force: boolean = false) => {
    try {
      setEmbeddingProgress({ status: 'pending', processed: 0, total: 0, failed: 0 })
      message.info(t('collectConfig.messages.embeddingStarting'))
      const response = await api.embeddings.generate(force, 100)
      message.success(
        t('collectConfig.messages.embeddingStarted', { n: response.data.total_talents })
      )
      // Status flips to 'running' → usePolling below picks it up until terminal
      setEmbeddingProgress({
        status: 'running',
        processed: 0,
        total: response.data.total_talents,
        failed: 0,
      })
    } catch (error) {
      message.error(getErrorMessage(error, t('collectConfig.messages.embeddingStartFailed')))
      setEmbeddingProgress(null)
    }
  }

  const handleCancelEmbeddingGeneration = async () => {
    try {
      await api.embeddings.cancel()
      message.success(t('collectConfig.messages.embeddingCancelled'))
      setEmbeddingProgress(null)
      loadEmbeddingStatus()
    } catch (error) {
      message.error(getErrorMessage(error, t('collectConfig.messages.cancelFailed')))
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
      message.error(t('collectConfig.messages.loadOsEmbeddingStatusFailed'))
    } finally {
      setOsEmbeddingLoading(false)
    }
  }

  const handleGenerateOsEmbeddings = async (force: boolean = false) => {
    try {
      setOsEmbeddingProgress({ status: 'pending', processed: 0, total: 0, failed: 0 })
      message.info(t('collectConfig.messages.osEmbeddingStarting'))
      const response = await api.openSource.generateEmbeddings(50, force)
      message.success(response.data.message)
      // Status flips to 'running' → usePolling below picks it up until terminal
      setOsEmbeddingProgress({ status: 'running', processed: 0, total: 0, failed: 0 })
    } catch (error) {
      message.error(getErrorMessage(error, t('collectConfig.messages.osEmbeddingStartFailed')))
      setOsEmbeddingProgress(null)
    }
  }

  const handleCancelOsEmbeddingGeneration = async () => {
    try {
      await api.openSource.cancelEmbeddingGeneration()
      message.success(t('collectConfig.messages.osEmbeddingCancelled'))
      setOsEmbeddingProgress(null)
      loadOsEmbeddingStatus()
    } catch (error) {
      message.error(getErrorMessage(error, t('collectConfig.messages.cancelFailed')))
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
            t('collectConfig.messages.syncCompleted', {
              processed: progress.processed,
              collaborations: progress.collaborations,
            })
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
            t('collectConfig.messages.genealogyCompleted', {
              processed: progress.processed,
              edges: progress.edges,
            })
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
            message.success(
              t('collectConfig.messages.embeddingCompleted', { n: res.data.processed })
            )
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
            message.success(
              t('collectConfig.messages.osEmbeddingCompleted', { n: res.data.processed })
            )
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
