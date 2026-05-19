/**
 * API client for backend communication
 */
import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'

/**
 * 动态获取 API 基础地址
 *
 * 优先级：
 * 1. 环境变量 VITE_API_URL（生产环境手动配置）
 * 2. 自动检测：使用当前访问地址的 host + 后端端口 8003
 * 3. 开发环境：空字符串（使用 Vite 代理）
 */
function getApiBaseUrl(): string {
  const envUrl = import.meta.env.VITE_API_URL
  if (envUrl) {
    return envUrl
  }

  const { hostname, protocol } = window.location
  if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
    return `${protocol}//${hostname}:8003`
  }

  return ''
}

const API_BASE_URL = getApiBaseUrl()

function serializeParams(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      value.forEach((v) => searchParams.append(key, String(v)))
    } else if (value !== undefined && value !== null) {
      searchParams.append(key, String(value))
    }
  }
  return searchParams.toString()
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  paramsSerializer: serializeParams,
})

apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.name === 'AbortError' || error.code === 'ERR_CANCELED') {
      return Promise.reject(error)
    }
    if (error.response?.status === 401) {
      const isLoginPage = window.location.pathname === '/login'
      const isLoginRequest = error.config?.url?.includes('/auth/login')
      localStorage.removeItem('token')
      if (!isLoginPage && !isLoginRequest) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient

export function createCancellableRequest<T>(
  requestFn: (signal: AbortSignal) => Promise<T>
): {
  request: () => Promise<T>
  cancel: () => void
} {
  const controller = new AbortController()
  return {
    request: () => requestFn(controller.signal),
    cancel: () => controller.abort(),
  }
}

export interface CancellableRequestConfig extends AxiosRequestConfig {
  signal?: AbortSignal
}

export function isCancellationError(error: unknown): boolean {
  if (error && typeof error === 'object') {
    const axiosError = error as { name?: string; code?: string }
    return axiosError.name === 'AbortError' || axiosError.code === 'ERR_CANCELED'
  }
  return false
}
