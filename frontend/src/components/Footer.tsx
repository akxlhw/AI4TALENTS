import { Space, Typography } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const { Text } = Typography

interface FooterProps {
  onOpenConsent?: () => void
}

const Footer: React.FC<FooterProps> = ({ onOpenConsent }) => {
  const navigate = useNavigate()
  const { t } = useTranslation('common')

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
        {t('footer.copyright', { year: 2026 })}
      </Text>
      <Space size={16} style={{ fontSize: 12 }}>
        <Text
          type="secondary"
          style={{ cursor: 'pointer' }}
          onClick={() => navigate('/privacy-policy')}
        >
          {t('footer.privacy')}
        </Text>
        <Text
          type="secondary"
          style={{ cursor: 'pointer' }}
          onClick={() => navigate('/terms-of-use')}
        >
          {t('footer.terms')}
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
          {t('footer.cookie')}
        </Text>
      </Space>
    </footer>
  )
}

export default Footer
