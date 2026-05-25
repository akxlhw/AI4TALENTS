import { Space, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'

const { Text } = Typography

interface FooterProps {
  onOpenConsent?: () => void
}

const Footer: React.FC<FooterProps> = ({ onOpenConsent }) => {
  const navigate = useNavigate()

  return (
    <footer
      style={{
        padding: '16px 32px',
        borderTop: '1px solid var(--border-secondary)',
        background: 'var(--bg-layout)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 8,
      }}
    >
      <Text type="secondary" style={{ fontSize: 12 }}>
        © 2026 AI4TALENT 智能人才库
      </Text>
      <Space size={16} style={{ fontSize: 12 }}>
        <Text
          type="secondary"
          style={{ cursor: 'pointer' }}
          onClick={() => navigate('/privacy-policy')}
        >
          隐私政策
        </Text>
        <Text
          type="secondary"
          style={{ cursor: 'pointer' }}
          onClick={() => navigate('/terms-of-use')}
        >
          用户协议
        </Text>
        <Text
          type="secondary"
          style={{ cursor: 'pointer' }}
          onClick={() => {
            if (onOpenConsent) {
              onOpenConsent()
            } else {
              window.dispatchEvent(new CustomEvent('open-consent-banner'))
            }
          }}
        >
          Cookie 设置
        </Text>
      </Space>
    </footer>
  )
}

export default Footer
