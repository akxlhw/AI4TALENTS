import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

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

describe('ApiKeysTab create flow', () => {
  beforeEach(() => {
    listMock.mockReset()
    createMock.mockReset()
    listMock.mockResolvedValue({ data: [] })
    createMock.mockResolvedValue({
      data: {
        api_key_id: 9,
        key_name: '测试',
        key_prefix: 'ak_xyz123',
        scopes: ['academic:read'],
        plaintext_key: 'ak_xyz123_full_plaintext',
      },
    })
  })

  it('shows plaintext modal after create', { timeout: 30000 }, async () => {
    render(<ApiKeysTab />)
    await waitFor(() => expect(listMock).toHaveBeenCalled(), { timeout: 15000 })

    fireEvent.click(screen.getByText('创建 Key'))
    const nameInput = await screen.findByPlaceholderText('如：洞察 Skill / 数据看板', undefined, {
      timeout: 15000,
    })
    fireEvent.change(nameInput, { target: { value: '测试' } })
    fireEvent.click(screen.getAllByText('只读')[0])

    fireEvent.click(screen.getByText('创 建'))

    await waitFor(() => expect(createMock).toHaveBeenCalled(), { timeout: 15000 })
    expect(await screen.findByText('Key 已创建', undefined, { timeout: 15000 })).toBeTruthy()
    expect(screen.getByText('ak_xyz123_full_plaintext')).toBeTruthy()
  })
})
