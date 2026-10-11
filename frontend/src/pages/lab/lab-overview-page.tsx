import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Row, Col, Card, Tag, Typography, Spin } from 'antd'
import { useTranslation } from 'react-i18next'
import { useLabStats, useLabList } from '../../hooks/useLabQueries'
import { applyDomainCssVars } from '../../theme'
import LabHero from './components/lab-hero'
import LabDistributionChart from './components/lab-distribution-chart'
import RoleDistributionChart from './components/role-distribution-chart'
import LabCard from './components/lab-card'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import { useAuth } from '../../contexts/AuthContext'
import { useLabRoles } from './constants/lab-role'
import '../../i18n/namespaces/lab'

const { Text } = Typography

const LabOverviewPage: React.FC = () => {
  const navigate = useNavigate()
  const { t } = useTranslation('lab')
  const { levelLabel } = useLabRoles()
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
        title={t('common.loadFailed')}
        description={error.message || t('common.retryLater')}
        action={{ label: t('common.retry'), onClick: () => refetch() }}
      />
    )
  }

  if (!stats || stats.total_talents === 0) {
    return (
      <EmptyPlaceholder
        title={t('overview.emptyTitle')}
        description={t('overview.emptyDescription')}
        action={
          user?.role === 'super_admin'
            ? {
                label: t('overview.goImport'),
                onClick: () => navigate('/system-config?tab=lab-import'),
              }
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
          title={t('overview.featuredLabs')}
          style={{ borderRadius: 12, marginBottom: 24 }}
          bodyStyle={{ padding: 20 }}
        >
          <Spin spinning={labsLoading}>
            {labsError ? (
              <EmptyPlaceholder
                title={t('common.loadFailed')}
                description={labsError.message || t('common.retryLater')}
                action={{ label: t('common.retry'), onClick: () => window.location.reload() }}
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
            <Card
              title={t('overview.labDistribution')}
              style={{ borderRadius: 12, height: '100%' }}
            >
              <LabDistributionChart
                data={labData}
                onBarClick={name => navigate(`/lab/search?parent_lab=${encodeURIComponent(name)}`)}
              />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card
              title={t('overview.roleDistribution')}
              style={{ borderRadius: 12, height: '100%' }}
            >
              <RoleDistributionChart
                data={roleData}
                onSliceClick={name => navigate(`/lab/search?role_type=${encodeURIComponent(name)}`)}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}>
            <Card title={t('overview.levelDistribution')} style={{ borderRadius: 12 }}>
              {stats.academic_level_distribution.map(l => (
                <div
                  key={l.name}
                  style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}
                >
                  <Text>{levelLabel(l.name)}</Text>
                  <Tag color="blue">{l.count}</Tag>
                </div>
              ))}
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card title={t('overview.topLabs')} style={{ borderRadius: 12 }}>
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
