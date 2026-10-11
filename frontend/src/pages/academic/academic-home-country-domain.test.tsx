import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import '../../i18n'

// Mock react-query hooks used by the homepage (API data in, labels translated out)
const highlightData = {
  hot_tech_domains: [
    { tech_domain_id: 2, domain_code: 'ai_models', domain_name: 'AI大模型', talent_count: 65867 },
    { tech_domain_id: 7, domain_code: 'trusted_security', domain_name: '可信安全', talent_count: 4660 },
  ],
  top_countries: [
    { country_code: 'CN', country_name: '中国', talent_count: 70533 },
    { country_code: 'US', country_name: '美国', talent_count: 41858 },
    { country_code: 'XY', country_name: '神秘之地', talent_count: 12 },
  ],
  top_schools: [],
  hot_research_topics: [],
}

vi.mock('../../hooks/useQueries', () => ({
  useHomepageHighlights: () => ({ data: highlightData, loading: false }),
  useOverviewStats: () => ({ data: { talent_count: 90000, country_count: 114 }, loading: false }),
}))

import AcademicHomePage from './academic-home-page'

describe('homepage distribution labels (domain/country) bilingual', () => {
  beforeEach(async () => {
    const { i18n } = await import('../../i18n')
    await i18n.changeLanguage('en')
  })

  it('renders English domain and country names from codes under en', async () => {
    render(<MemoryRouter><AcademicHomePage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText(/LLM \(65867\)/)).toBeTruthy())
    expect(screen.getByText(/Trusted Security \(4660\)/)).toBeTruthy()
    expect(screen.getByText(/China \(70533\)/)).toBeTruthy()
    expect(screen.getByText(/United States \(41858\)/)).toBeTruthy()
    // unknown country code falls back to API name
    expect(screen.getByText(/神秘之地 \(12\)/)).toBeTruthy()
  })

  it('renders Chinese names under zh (API-faithful)', async () => {
    const { i18n } = await import('../../i18n')
    await i18n.changeLanguage('zh')
    render(<MemoryRouter><AcademicHomePage /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText(/AI大模型 \(65867\)/)).toBeTruthy())
    expect(screen.getByText(/可信安全 \(4660\)/)).toBeTruthy()
    expect(screen.getByText(/中国 \(70533\)/)).toBeTruthy()
  })
})
