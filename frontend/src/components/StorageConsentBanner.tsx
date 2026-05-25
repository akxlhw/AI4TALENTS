import { useState, useEffect } from 'react'
import { Button, Radio, Space, Typography, Modal } from 'antd'
import { useAuthStore } from '../stores/authStore'
import { api } from '../services/api'

const { Text } = Typography

type ConsentLevel = 'necessary' | 'functional' | 'analytics'

const STORAGE_KEY = 'storage_consent_level'

const StorageConsentBanner: React.FC = () => {
  const [visible, setVisible] = useState(false)
  const [level, setLevel] = useState<ConsentLevel>('necessary')
  const user = useAuthStore((s) => s.user)

  useEffect(() => {
    const handleOpen = () => setVisible(true)
    window.addEventListener('open-consent-banner', handleOpen)
    return () => window.removeEventListener('open-consent-banner', handleOpen)
  }, [])

  useEffect(() => {
    // Logged-in user: check server status first
    if (user) {
      api.privacy
        .getConsentStatus()
        .then((res) => {
          const serverLevel = res.data.storage_consent_level
          if (serverLevel) {
            localStorage.setItem(STORAGE_KEY, serverLevel)
            setVisible(false)
          } else {
            setVisible(true)
          }
        })
        .catch(() => {
          // Fallback to localStorage
          const local = localStorage.getItem(STORAGE_KEY) as ConsentLevel | null
          if (!local) setVisible(true)
        })
      return
    }

    // Guest: check localStorage only
    const local = localStorage.getItem(STORAGE_KEY) as ConsentLevel | null
    if (!local) setVisible(true)
  }, [user])

  const handleAccept = async () => {
    localStorage.setItem(STORAGE_KEY, level)

    if (user) {
      try {
        await api.privacy.updateConsent({
          policy_version: '2.1.0',
          terms_version: '2.1.0',
          storage_consent_level: level,
          accepted: true,
        })
      } catch {
        // Best-effort sync
      }
    }

    setVisible(false)
  }

  if (!visible) return null

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        background: 'rgba(255,255,255,0.96)',
        backdropFilter: 'blur(12px)',
        borderTop: '1px solid var(--border-secondary)',
        boxShadow: '0 -4px 20px rgba(0,0,0,0.06)',
        padding: '16px 24px',
      }}
    >
      <div
        style={{
          maxWidth: 1200,
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <Space direction="vertical" size={4} style={{ flex: 1, minWidth: 280 }}>
          <Text style={{ fontSize: 14, fontWeight: 500 }}>
            我们使用本地存储来改善您的体验
          </Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            您可以选择允许哪些类型的数据存储。必要类存储用于维持登录状态，功能类用于记住您的偏好设置。
          </Text>
          <Radio.Group
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            size="small"
          >
            <Radio value="necessary">仅必要</Radio>
            <Radio value="functional">功能偏好</Radio>
            <Radio value="analytics">分析统计</Radio>
          </Radio.Group>
        </Space>

        <Space>
          <Button
            type="link"
            size="small"
            onClick={() =>
              Modal.info({
                title: '隐私政策',
                content: (
                  <div style={{ maxHeight: 400, overflow: 'auto' }}>
                    <p>请访问「隐私政策」页面查看完整内容。</p>
                  </div>
                ),
                onOk: () => window.open('/privacy-policy', '_blank'),
                okText: '查看完整政策',
              })
            }
          >
            查看隐私政策
          </Button>
          <Button type="primary" size="small" onClick={handleAccept}>
            接受所选
          </Button>
        </Space>
      </div>
    </div>
  )
}

export default StorageConsentBanner
