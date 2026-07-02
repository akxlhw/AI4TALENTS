import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Statistic, Spin, Empty, Typography, Tag, Button } from 'antd'
import { ExperimentOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import { getErrorMessage } from '../../utils'
import type { LabStats } from '../../types'

const { Title, Text } = Typography

const ROLE_COLORS: Record<string, string> = {
  professor: '#e94560',
  student: '#42a5f5',
  graduate: '#ffa726',
  unknown: '#999',
}

const ROLE_LABELS: Record<string, string> = {
  professor: '教授',
  student: '学生',
  graduate: '博后/研究员',
  unknown: '其他',
}

const LEVEL_LABELS: Record<string, string> = {
  phd: '博士',
  master: '硕士',
  bachelor: '学士',
}

const LabOverviewPage: React.FC = () => {
  const navigate = useNavigate()
  const [stats, setStats] = useState<LabStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        setLoading(true)
        const res = await api.lab.getStats()
        setStats(res.data)
      } catch (e) {
        import('antd').then(({ message }) => message.error(getErrorMessage(e, '加载实验室概览失败')))
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [])

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!stats || stats.total_talents === 0) {
    return (
      <div style={{ padding: 48, textAlign: 'center' }}>
        <Empty
          description={
            <div>
              <Text>暂无 AI 实验室人才数据</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                请通过 hermes 推送或管理员上传导入实验室人才数据
              </Text>
            </div>
          }
        />
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>
        <ExperimentOutlined style={{ marginRight: 8 }} />
        AI 实验室人才库
      </Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="人才总数"
              value={stats.total_talents}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="顶级实验室"
              value={stats.total_parent_labs}
              prefix={<ExperimentOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="子实验室/研究组"
              value={stats.total_sub_labs}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col xs={24} sm={12}>
          <Card title="实验室分布" style={{ marginBottom: 16 }}>
            {stats.parent_lab_distribution.slice(0, 8).map((lab) => (
              <div
                key={lab.name}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '4px 0',
                  cursor: 'pointer',
                }}
                onClick={() => navigate(`/lab/search?parent_lab=${encodeURIComponent(lab.name)}`)}
              >
                <Text>{lab.name}</Text>
                <Tag>{lab.count}</Tag>
              </div>
            ))}
          </Card>
        </Col>
        <Col xs={24} sm={12}>
          <Card title="角色分布" style={{ marginBottom: 16 }}>
            {stats.role_distribution.map((r) => (
              <div
                key={r.name}
                style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}
              >
                <Tag color={ROLE_COLORS[r.name] || '#999'}>
                  {ROLE_LABELS[r.name] || r.name}
                </Tag>
                <Text>{r.count}</Text>
              </div>
            ))}
            {stats.academic_level_distribution.length > 0 && (
              <>
                <div style={{ marginTop: 12, marginBottom: 4 }}>
                  <Text type="secondary">学位层次</Text>
                </div>
                {stats.academic_level_distribution.map((l) => (
                  <div
                    key={l.name}
                    style={{ display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}
                  >
                    <Text>{LEVEL_LABELS[l.name] || l.name}</Text>
                    <Text type="secondary">{l.count}</Text>
                  </div>
                ))}
              </>
            )}
          </Card>
        </Col>
      </Row>

      <Card title="热门研究组" style={{ marginTop: 16 }}>
        {stats.top_labs.map((lab) => (
          <Tag
            key={lab.name}
            style={{ marginBottom: 8, cursor: 'pointer' }}
            onClick={() => navigate(`/lab/search?lab_name=${encodeURIComponent(lab.name)}`)}
          >
            {lab.name} ({lab.count})
          </Tag>
        ))}
      </Card>

      <div style={{ textAlign: 'center', marginTop: 24 }}>
        <Button type="primary" size="large" onClick={() => navigate('/lab/search')}>
          浏览全部人才
        </Button>
      </div>
    </div>
  )
}

export default LabOverviewPage
