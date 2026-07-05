import { useNavigate } from 'react-router-dom'
import { Button, Typography, Space } from 'antd'
import { ExperimentOutlined, ArrowRightOutlined, UploadOutlined } from '@ant-design/icons'
import { useAuth } from '../../../contexts/AuthContext'

const { Title, Paragraph } = Typography

const LabHero: React.FC = () => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const isAdmin = user?.role === 'super_admin'

  return (
    <div
      style={{
        background: 'var(--domain-gradient)',
        padding: '64px 32px 48px',
        color: '#fff',
        position: 'relative',
        overflow: 'hidden',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.06,
          backgroundImage:
            'radial-gradient(circle at 2px 2px, rgba(255,255,255,0.8) 1px, transparent 0)',
          backgroundSize: '28px 28px',
        }}
      />
      <div style={{ position: 'relative', zIndex: 1, maxWidth: 800, margin: '0 auto' }}>
        <Title level={1} style={{ color: '#fff', margin: 0, marginBottom: 12, fontWeight: 800 }}>
          <ExperimentOutlined style={{ marginRight: 12 }} />
          AI 实验室人才库
        </Title>
        <Paragraph style={{ color: 'rgba(255,255,255,0.85)', fontSize: 16, marginBottom: 32 }}>
          汇聚全球顶尖 AI 实验室的研究人才
        </Paragraph>
        <Space size={16}>
          <Button
            type="primary"
            size="large"
            style={{ background: '#fff', color: 'var(--domain-primary)', fontWeight: 600 }}
            icon={<ArrowRightOutlined />}
            onClick={() => navigate('/lab/search')}
          >
            浏览全部人才
          </Button>
          {isAdmin && (
            <Button
              size="large"
              style={{
                background: 'rgba(255,255,255,0.15)',
                color: '#fff',
                borderColor: 'rgba(255,255,255,0.3)',
              }}
              icon={<UploadOutlined />}
              onClick={() => navigate('/system-config?tab=lab-import')}
            >
              导入数据
            </Button>
          )}
        </Space>
      </div>
    </div>
  )
}

export default LabHero
