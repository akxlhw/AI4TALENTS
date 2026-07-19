import { useEffect, useRef } from 'react'
import { notification } from 'antd'
import { useActiveCollectTasks } from './useQueries'

interface ActiveTask {
  task_id: number
  task_name?: string
  status: string
}

const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled'])

/**
 * Global watcher for academic collect tasks: fires a notification when a
 * task transitions running → terminal, even when the user has navigated
 * away from the collection config page. Mounted once in MainLayout.
 */
export function useCollectTaskNotifier() {
  const { data } = useActiveCollectTasks()
  const prevStatuses = useRef<Map<number, string>>(new Map())

  useEffect(() => {
    // getActiveTasks may return a bare array or a paginated { items } payload
    const tasks: ActiveTask[] = Array.isArray(data) ? data : (data?.items ?? [])

    for (const task of tasks) {
      const prev = prevStatuses.current.get(task.task_id)
      // Only notify on a live transition; statuses seen for the first time
      // (e.g. on page load) are recorded silently.
      if (prev && !TERMINAL_STATUSES.has(prev) && TERMINAL_STATUSES.has(task.status)) {
        const name = task.task_name || `任务 #${task.task_id}`
        if (task.status === 'completed') {
          notification.success({ message: '采集任务完成', description: `「${name}」已完成` })
        } else if (task.status === 'failed') {
          notification.error({ message: '采集任务失败', description: `「${name}」已失败，请前往采集配置查看` })
        } else {
          notification.info({ message: '采集任务已取消', description: `「${name}」已取消` })
        }
      }
      prevStatuses.current.set(task.task_id, task.status)
    }

    // Drop tasks that disappeared from the active list (e.g. deleted)
    const ids = new Set(tasks.map((t) => t.task_id))
    for (const id of prevStatuses.current.keys()) {
      if (!ids.has(id)) prevStatuses.current.delete(id)
    }
  }, [data])
}
