import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Row, Col, Card, Tag, Typography, Spin } from 'antd'
import { useLabStats, useLabList } from '../../hooks/useLabQueries'
import { applyDomainCssVars } from '../../theme'
import LabHero from './components/lab-hero'
import LabDistributionChart from './components/lab-distribution-chart'
import RoleDistributionChart from './components/role-distribution-chart'
import LabCard from './components/lab-card'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import { useAuth } from '../../contexts/AuthContext'

const { Text } = Typography

const LabOverviewPage: React.FC = () => {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { data: stats, isLoading, error, refetch } = useLabStats()
  const { data: labs, isLoading: labsLoading, error: labsError } = useLabList()

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
        description="请通过管理员上传导入实验室人才数据"
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
    <div style={{ paddingTop: 64 }}>
      <LabHero />
      <div
        style={{
          padding: 24,
          background: 'var(--color-bg-gray-light)',
          minHeight: 'calc(100vh - 300px)',
        }}
      >
        <Card
          title="收录实验室"
          style={{ borderRadius: 12, marginBottom: 24 }}
          bodyStyle={{ padding: 20 }}
        >
          <Spin spinning={labsLoading}>
            {labsError ? (
              <EmptyPlaceholder
                title="加载失败"
                description={labsError.message || '请稍后重试'}
                action={{ label: '重试', onClick: () => window.location.reload() }}
              />
            ) : (
              <Row gutter={[16, 16]}>
                {labs?.map(lab => (
                  <Col key={lab.name} xs={24} sm={12} lg={8} xl={6}>
                    <LabCard lab={lab} />
                  </Col>
                ))}
              </Row>
            )}
          </Spin>
        </Card>

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
