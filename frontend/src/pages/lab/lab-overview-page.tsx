import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Row, Col, Card, Tag, Typography } from 'antd'
import { UserOutlined, ExperimentOutlined, TeamOutlined } from '@ant-design/icons'
import { useLabStats } from '../../hooks/useLabQueries'
import { applyDomainCssVars } from '../../theme'
import LabHero from './components/lab-hero'
import LabStatCard from './components/lab-stat-card'
import LabDistributionChart from './components/lab-distribution-chart'
import RoleDistributionChart from './components/role-distribution-chart'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import { useAuth } from '../../contexts/AuthContext'

const { Text } = Typography

const LabOverviewPage: React.FC = () => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { data: stats, isLoading, error, refetch } = useLabStats()

  useEffect(() => {
    applyDomainCssVars('lab')
  }, [])

  if (isLoading) return <PageSkeleton />

  if (error) {
    return (
      <EmptyPlaceholder
        title="加载失败"
        description={error.message || '请稍后重试'}
        action={{ label: '重试', onClick: () => refetch() }}
      />
    )
  }

  if (!stats || stats.total_talents === 0) {
    return (
      <EmptyPlaceholder
        title="暂无 AI 实验室人才数据"
        description="请通过 hermes 推送或管理员上传导入实验室人才数据"
        action={
          user?.role === 'super_admin'
            ? { label: '去导入', onClick: () => navigate('/system-config?tab=lab-import') }
            : undefined
        }
      />
    )
  }

  const roleData = stats.role_distribution.map(r => ({ name: r.name, value: r.count }))
  const labData = stats.parent_lab_distribution.map(l => ({ name: l.name, value: l.count }))

  return (
    <div>
      <LabHero />
      <div
        style={{
          padding: 24,
          background: 'var(--color-bg-gray-light)',
          minHeight: 'calc(100vh - 300px)',
        }}
      >
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={8}>
            <LabStatCard title="人才总数" value={stats.total_talents} icon={<UserOutlined />} />
          </Col>
          <Col xs={24} sm={8}>
            <LabStatCard
              title="顶级实验室"
              value={stats.total_parent_labs}
              icon={<ExperimentOutlined />}
            />
          </Col>
          <Col xs={24} sm={8}>
            <LabStatCard
              title="子实验室/研究组"
              value={stats.total_sub_labs}
              icon={<TeamOutlined />}
            />
          </Col>
        </Row>

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card title="实验室分布" style={{ borderRadius: 12, height: '100%' }}>
              <LabDistributionChart
                data={labData}
                onBarClick={name => navigate(`/lab/search?parent_lab=${encodeURIComponent(name)}`)}
              />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="角色分布" style={{ borderRadius: 12, height: '100%' }}>
              <RoleDistributionChart
                data={roleData}
                onSliceClick={name => navigate(`/lab/search?role_type=${encodeURIComponent(name)}`)}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <Card title="学位层次" style={{ borderRadius: 12 }}>
              {stats.academic_level_distribution.map(l => (
                <div
                  key={l.name}
                  style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}
                >
                  <Text>{l.name}</Text>
                  <Tag color="blue">{l.count}</Tag>
                </div>
              ))}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title="热门研究组" style={{ borderRadius: 12 }}>
              {stats.top_labs.map(lab => (
                <Tag
                  key={lab.name}
                  style={{ marginBottom: 8, cursor: 'pointer', fontSize: 13 }}
                  onClick={() => navigate(`/lab/search?lab_name=${encodeURIComponent(lab.name)}`)}
                >
                  {lab.name} ({lab.count})
                </Tag>
              ))}
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  )
}

export default LabOverviewPage
