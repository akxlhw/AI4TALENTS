import { useEffect, useState } from 'react'
import { Typography, Spin, Alert, Card } from 'antd'
import { useTranslation } from 'react-i18next'
import { api } from '../../services/api'
import '../../i18n/namespaces/legal'

const { Title, Paragraph, Text } = Typography

const PrivacyPolicyPage: React.FC = () => {
  const { t } = useTranslation('legal')
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPolicy = async () => {
      try {
        const response = await api.privacy.getPolicy()
        setContent(response.data.content)
      } catch {
        setContent('')
      } finally {
        setLoading(false)
      }
    }
    fetchPolicy()
  }, [])

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '80px 0' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg-layout)',
        padding: '48px 24px',
      }}
    >
      <Card
        style={{
          maxWidth: 840,
          margin: '0 auto',
          borderRadius: 16,
          boxShadow: 'var(--shadow-md)',
        }}
      >
        <Text type="secondary" style={{ display: 'block', marginBottom: 16, fontSize: 12 }}>
          {t('referenceNote')}
        </Text>
        <Alert
          message={t('privacy.alertTitle')}
          description={t('privacy.alertDescription')}
          type="warning"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Typography>
          {content.split('\n').map((line, idx) => {
            if (line.startsWith('# ')) {
              return <Title key={idx}>{line.replace('# ', '')}</Title>
            }
            if (line.startsWith('## ')) {
              return (
                <Title level={3} key={idx} style={{ marginTop: 24 }}>
                  {line.replace('## ', '')}
                </Title>
              )
            }
            if (line.startsWith('### ')) {
              return (
                <Title level={4} key={idx} style={{ marginTop: 16 }}>
                  {line.replace('### ', '')}
                </Title>
              )
            }
            if (line.startsWith('> ')) {
              return (
                <Paragraph key={idx}>
                  <Text type="secondary">{line.replace('> ', '')}</Text>
                </Paragraph>
              )
            }
            if (
              line.startsWith('- ') ||
              line.startsWith('1. ') ||
              line.startsWith('2. ') ||
              line.startsWith('3. ') ||
              line.startsWith('4. ')
            ) {
              return (
                <Paragraph key={idx} style={{ paddingLeft: 16 }}>
                  {line}
                </Paragraph>
              )
            }
            if (line.startsWith('**') && line.endsWith('**')) {
              return (
                <Paragraph key={idx}>
                  <Text strong>{line.replace(/\*\*/g, '')}</Text>
                </Paragraph>
              )
            }
            if (line.trim() === '') {
              return <div key={idx} style={{ height: 8 }} />
            }
            return <Paragraph key={idx}>{line}</Paragraph>
          })}
        </Typography>
      </Card>
    </div>
  )
}

export default PrivacyPolicyPage
