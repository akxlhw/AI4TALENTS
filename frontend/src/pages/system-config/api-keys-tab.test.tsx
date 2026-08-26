import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const listMock = vi.fn()
const createMock = vi.fn()
const setActiveMock = vi.fn()

vi.mock('../../services/api/apiKeys', () => ({
  apiKeysApi: {
    list: (...a: unknown[]) => listMock(...a),
    create: (...a: unknown[]) => createMock(...a),
    setActive: (...a: unknown[]) => setActiveMock(...a),
  },
}))

vi.mock('antd', async importOriginal => {
  const antd = await importOriginal<typeof import('antd')>()
  return { ...antd, message: { ...antd.message, error: vi.fn(), success: vi.fn() } }
})

import ApiKeysTab from './api-keys-tab'

describe('ApiKeysTab', () => {
  beforeEach(() => {
    listMock.mockReset()
  })

  it('renders key rows with masked prefix and scope tags', async () => {
    listMock.mockResolvedValue({
      data: [
        {
          api_key_id: 1,
          key_name: '洞察 Skill',
          key_prefix: 'ak_abc12',
          scopes: ['academic:read', 'industry:write'],
          is_active: true,
          rate_limit_per_minute: null,
          expires_at: null,
          last_used_at: '2026-08-26 10:00:00',
          created_at: '2026-08-26 09:00:00',
        },
      ],
    })
    render(<ApiKeysTab />)
    expect(await screen.findByText('洞察 Skill')).toBeTruthy()
    expect(screen.getByText('ak_abc12…')).toBeTruthy()
    expect(screen.getByText('学术·读')).toBeTruthy()
    expect(screen.getByText('行业·读写')).toBeTruthy()
    expect(screen.getByText('创建 Key')).toBeTruthy()
  })

  it('shows revoked badge for inactive keys', async () => {
    listMock.mockResolvedValue({
      data: [
        {
          api_key_id: 2,
          key_name: '旧工具',
          key_prefix: 'ak_old99',
          scopes: ['lab:read'],
          is_active: false,
          rate_limit_per_minute: null,
          expires_at: null,
          last_used_at: null,
          created_at: null,
        },
      ],
    })
    render(<ApiKeysTab />)
    await waitFor(() => expect(screen.getByText('旧工具')).toBeTruthy())
    expect(screen.getByText('已吊销')).toBeTruthy()
    expect(screen.getByText('启用')).toBeTruthy()
  })
})
