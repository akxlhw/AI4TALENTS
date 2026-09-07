import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const insightsMock = vi.fn()

vi.mock('../../../services/api', () => ({
  api: {
    openSource: {
      getDeveloperInsights: (p: unknown) => insightsMock(p),
    },
  },
}))

// jsdom 无 canvas 实现，echarts.init 会抛错；本测试关注面板行为（按需加载/统计渲染），
// 与图表渲染无关，故将图表组件替换为空占位（不断言图表内部）。
vi.mock('echarts-for-react', () => ({
  default: () => <div data-testid="echarts-mock" />,
}))

import OsInsightsPanel from './os-insights-panel'
import type { OSSearchQuery } from '../../../types'

const baseQuery: OSSearchQuery = { q: '', page: 1, page_size: 20 }

describe('OsInsightsPanel', () => {
  beforeEach(() => {
    insightsMock.mockReset()
    insightsMock.mockResolvedValue({
      data: {
        total: 3,
        contactable: 2,
        tech_element_distribution: { models: 2, robot_control: 1 },
        repo_distribution: [{ repo_full_name: 'pytorch/pytorch', developer_count: 2 }],
        company_distribution: { Google: 2, SomeSmallCo: 1 },
      },
    })
  })

  it('does not fetch while collapsed, fetches on expand', async () => {
    render(<OsInsightsPanel query={baseQuery} />)
    expect(insightsMock).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText(/命中人才洞察/))
    await waitFor(() => expect(insightsMock).toHaveBeenCalledTimes(1), { timeout: 15000 })
    expect(await screen.findByText('2 / 3', undefined, { timeout: 15000 })).toBeTruthy()
    expect(screen.getByText('66.7%')).toBeTruthy()
  }, 30000)

  it('shows error state with retry button, recovers on retry', async () => {
    insightsMock.mockRejectedValueOnce(new Error('boom'))
    render(<OsInsightsPanel query={baseQuery} />)
    fireEvent.click(screen.getByText(/命中人才洞察/))
    expect(await screen.findByText('洞察加载失败', undefined, { timeout: 15000 })).toBeTruthy()
    // antd 对两字符中文按钮自动插空格，可访问名为「重 试」
    fireEvent.click(screen.getByRole('button', { name: /重\s*试/ }))
    await waitFor(() => expect(insightsMock).toHaveBeenCalledTimes(2), { timeout: 15000 })
    expect(await screen.findByText('2 / 3', undefined, { timeout: 15000 })).toBeTruthy()
  }, 30000)
})
