import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

const listCollectTasks = vi.fn()

vi.mock('../../../../services/api', () => ({
  api: {
    openSource: {
      listCollectTasks: (...args: unknown[]) => listCollectTasks(...args),
      cancelCollectTask: vi.fn(),
      deleteCollectTask: vi.fn(),
    },
  },
}))

// Silence antd message popups in jsdom
vi.mock('antd', async importOriginal => {
  const antd = await importOriginal<typeof import('antd')>()
  return { ...antd, message: { ...antd.message, error: vi.fn(), success: vi.fn() } }
})

import OSCollectTaskSubTab from '../os-collect-task-sub-tab'

const TOTAL = 196

function mockResponse(params: { page?: number; page_size?: number }, status = 'completed') {
  const page = params.page ?? 1
  const pageSize = params.page_size ?? 20
  const items = Array.from({ length: Math.min(pageSize, TOTAL - (page - 1) * pageSize) }, (_, i) => ({
    task_id: (page - 1) * pageSize + i + 1,
    task_name: `OS-20260820-${i}`,
    status,
    current_step: status,
    progress_percent: status === 'completed' ? 100 : 50,
    processed_records: 5,
    total_records: 5,
    created_at: '2026-08-20 10:00:00',
  }))
  return { data: { items, total: TOTAL, page, page_size: pageSize, total_pages: Math.ceil(TOTAL / pageSize) } }
}

async function renderAndGotoPage2() {
  listCollectTasks.mockImplementation((_params?: { page?: number; page_size?: number }) =>
    Promise.resolve(mockResponse(_params ?? {}))
  )
  render(<OSCollectTaskSubTab />)
  await waitFor(() => expect(listCollectTasks).toHaveBeenCalled())
  // Go to page 2 (default size 20)
  fireEvent.click(await screen.findByTitle('2'))
  await waitFor(() =>
    expect(listCollectTasks).toHaveBeenLastCalledWith({ page: 2, page_size: 20 })
  )
  return listCollectTasks.mock.calls.length
}

describe('OSCollectTaskSubTab pagination', () => {
  beforeEach(() => {
    listCollectTasks.mockClear()
  })

  it('changing page size settles instead of looping', { timeout: 20000 }, async () => {
    await renderAndGotoPage2()

    // Open the size changer select (antd opens on mousedown) and choose 100 条/页
    const sizeChanger = document.querySelector('.ant-pagination-options .ant-select')
    expect(sizeChanger).toBeTruthy()
    fireEvent.mouseDown(sizeChanger!.querySelector('.ant-select-selector') as HTMLElement)
    const option = await waitFor(() => {
      const el = document.querySelector('.ant-select-item-option[title="100 / page"]')
      if (!el) throw new Error('option not rendered yet')
      return el as HTMLElement
    })
    fireEvent.click(option)

    // Let any reactive cascade settle for a generous window
    await new Promise(r => setTimeout(r, 1500))
    const callsAfterSizeChange = listCollectTasks.mock.calls.length
    await new Promise(r => setTimeout(r, 1500))

    // A ping-pong loop fires request pairs every few hundred ms; a settled
    // component fires none. Allow small slack but nothing loop-like.
    expect(listCollectTasks.mock.calls.length).toBeLessThanOrEqual(callsAfterSizeChange + 1)
    expect(listCollectTasks).toHaveBeenLastCalledWith({ page: 1, page_size: 100 })
  })

  it('stops auto-refresh once no task is running', { timeout: 20000 }, async () => {
    let call = 0
    listCollectTasks.mockImplementation((params?: { page?: number; page_size?: number }) => {
      call += 1
      // First response has a running task (poll starts); later responses
      // report everything completed (poll must stop).
      return Promise.resolve(mockResponse(params ?? {}, call === 1 ? 'running' : 'completed'))
    })
    render(<OSCollectTaskSubTab />)

    await waitFor(
      () => expect(listCollectTasks.mock.calls.length).toBeGreaterThanOrEqual(2),
      { timeout: 6000 }
    )
    const settled = listCollectTasks.mock.calls.length
    await new Promise(r => setTimeout(r, 4000))
    expect(listCollectTasks.mock.calls.length).toBe(settled)
  })
})
