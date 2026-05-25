import { useEffect, useState } from 'react'
import { Typography, Spin, Alert, Card } from 'antd'
import { api } from '../../services/api'

const { Title, Paragraph, Text } = Typography

const TermsOfUsePage: React.FC = () => {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchTerms = async () => {
      try {
        const response = await api.privacy.getTerms()
        setContent(response.data.content)
      } catch {
        setContent('')
      } finally {
        setLoading(false)
      }
    }
    fetchTerms()
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
        <Alert
          message="法律约束"
          description="违反人才数据使用限制条款可能导致账号封禁及法律责任。"
          type="error"
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
            if (line.startsWith('- ') || /^\d+\.\s/.test(line)) {
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

export default TermsOfUsePage
