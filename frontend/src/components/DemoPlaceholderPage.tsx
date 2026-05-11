import { Card, Row, Col, Typography, Button, Space } from 'antd'
import { ArrowLeftOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title, Text, Paragraph } = Typography

interface DemoPlaceholderPageProps {
  title: string
  description: string
  icon: React.ReactNode
  features: string[]
  children?: React.ReactNode
}

export function DemoPlaceholderPage({
  title,
  description,
  icon,
  features,
  children,
}: DemoPlaceholderPageProps) {
  const navigate = useNavigate()

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate(-1)}
        style={{ marginBottom: 24 }}
      >
        返回
      </Button>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card>
            <Space align="start" size="large">
              <div
                style={{
                  width: 64,
                  height: 64,
                  borderRadius: 12,
                  background: '#f0f5ff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 28,
                }}
              >
                {icon}
              </div>
              <div>
                <Title level={3} style={{ margin: 0 }}>
                  {title}
                </Title>
                <Paragraph type="secondary">{description}</Paragraph>
              </div>
            </Space>
          </Card>

          {children}
        </Col>

        <Col xs={24} lg={8}>
          <Card title="功能预览" bordered={false}>
            {features.map((f, i) => (
              <div
                key={i}
                style={{
                  padding: '12px 0',
                  borderBottom: i < features.length - 1 ? '1px solid #f0f0f0' : undefined,
                }}
              >
                <Text type="secondary">{f}</Text>
              </div>
            ))}
          </Card>

          <Card style={{ marginTop: 16 }} bordered={false}>
            <Space>
              <LockOutlined style={{ color: '#faad14' }} />
              <Text type="secondary">完整功能开发中，敬请期待</Text>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
