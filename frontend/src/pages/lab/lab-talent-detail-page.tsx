import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import type { TabsProps } from 'antd'
import {
  Row,
  Col,
  Card,
  Descriptions,
  Tag,
  Typography,
  Button,
  Space,
  Divider,
  Spin,
  Tabs,
} from 'antd'
import {
  ArrowLeftOutlined,
  HomeOutlined,
  TeamOutlined,
  UserSwitchOutlined,
} from '@ant-design/icons'
import { useLabTalent, useHomepagePreview, useMentorship } from '../../hooks/useLabQueries'
import { applyDomainCssVars } from '../../theme'
import { getErrorMessage } from '../../utils'
import { navigateBack } from '../../utils/navigation'
import { useLabRoles } from './constants/lab-role'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import BreadcrumbNav from '../../components/BreadcrumbNav'
import LabTalentHeader from './components/lab-talent-header'
import { useTranslation } from 'react-i18next'
import '../../i18n/namespaces/lab'

const { Title, Text, Link } = Typography

const LabTalentDetailPage: React.FC = () => {
  const { t } = useTranslation('lab')
  const { roleLabel, levelLabel } = useLabRoles()
  const { talentId } = useParams<{ talentId: string }>()
  const navigate = useNavigate()
  const id = talentId ? Number(talentId) : undefined
  const { data: talent, isLoading, error, refetch } = useLabTalent(id)

  // Tab state: 'info' | 'mentorship' | 'homepage'
  const [activeTab, setActiveTab] = useState('info')
  // Load preview when user switches to homepage tab
  const {
    data: preview,
    isLoading: previewLoading,
    error: previewError,
  } = useHomepagePreview(id, activeTab === 'homepage')
  // Load mentorship data (lazy — only when mentorship tab is active)
  const { data: mentorship, isLoading: mentorshipLoading } = useMentorship(
    activeTab === 'mentorship' ? id : undefined
  )

  useEffect(() => {
    applyDomainCssVars('lab')
  }, [])

  if (isLoading) return <PageSkeleton />

  if (error) {
    return (
      <EmptyPlaceholder
        title={t('common.loadFailed')}
        description={getErrorMessage(error, t('detail.loadFailed'))}
        action={{ label: t('common.retry'), onClick: () => refetch() }}
      />
    )
  }

  if (!talent) {
    return (
      <EmptyPlaceholder
        title={t('detail.notFoundTitle')}
        description={t('detail.notFoundDescription')}
        action={{ label: t('detail.backToSearch'), onClick: () => navigate('/lab/search') }}
      />
    )
  }

  const tabItems: TabsProps['items'] = [
    {
      key: 'info',
      label: t('detail.tabs.info'),
      children: (
        <Card style={{ borderRadius: 12, border: 'none' }}>
          <Descriptions column={1} bordered size="small" labelStyle={{ width: 140 }}>
            <Descriptions.Item label={t('detail.fields.parentLab')}>
              {talent.parent_lab}
            </Descriptions.Item>
            {talent.lab_name && talent.lab_name !== talent.parent_lab && (
              <Descriptions.Item label={t('detail.fields.labGroup')}>
                {talent.lab_name}
              </Descriptions.Item>
            )}
            {talent.department && (
              <Descriptions.Item label={t('detail.fields.department')}>
                {talent.department}
              </Descriptions.Item>
            )}
            {talent.cohort_year && (
              <Descriptions.Item label={t('detail.fields.cohortYear')}>
                {talent.cohort_year}
              </Descriptions.Item>
            )}
            {talent.cohort_source && (
              <Descriptions.Item label={t('detail.fields.cohortSource')}>
                {talent.cohort_source}
              </Descriptions.Item>
            )}
          </Descriptions>

          {talent.research_areas && talent.research_areas.length > 0 && (
            <>
              <Divider />
              <Title level={5}>{t('detail.researchAreas')}</Title>
              <Space size={8} wrap>
                {talent.research_areas.map(a => (
                  <Tag
                    key={a}
                    color="geekblue"
                    style={{
                      maxWidth: 400,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={a}
                  >
                    {a}
                  </Tag>
                ))}
              </Space>
            </>
          )}

          <Divider />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {t('detail.dataSource', { lab: talent.parent_lab })}
            {talent.collected_at &&
              ` · ${t('detail.collectedAt', { date: talent.collected_at.slice(0, 10) })}`}
          </Text>
          {talent.source_detail_url && (
            <div>
              <Link href={talent.source_detail_url} target="_blank" style={{ fontSize: 12 }}>
                {t('detail.viewSource')}
              </Link>
            </div>
          )}
        </Card>
      ),
    },
  ]

  // Add mentorship tab (always present — data may have advisor or students)
  tabItems.push({
    key: 'mentorship',
    label: (
      <span>
        <TeamOutlined style={{ marginRight: 4 }} />
        {t('detail.tabs.mentorship')}
      </span>
    ),
    children: (
      <div style={{ minHeight: 200 }}>
        {mentorshipLoading ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin tip={t('detail.loadingMentorship')} />
          </div>
        ) : mentorship ? (
          <>
            {/* Advisors */}
            <div style={{ marginBottom: 24 }}>
              <Title level={5}>
                <UserSwitchOutlined style={{ marginRight: 6 }} />
                {t('detail.advisor')}
              </Title>
              {mentorship.advisor ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <Tag color="blue">{t('detail.advisor')}</Tag>
                  {mentorship.advisor_talent_id ? (
                    <Link onClick={() => navigate(`/lab/talents/${mentorship.advisor_talent_id}`)}>
                      {mentorship.advisor}
                    </Link>
                  ) : (
                    <Text>{mentorship.advisor}</Text>
                  )}
                </div>
              ) : (
                <Text type="secondary">{t('detail.noAdvisor')}</Text>
              )}
              {mentorship.co_advisor && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Tag color="cyan">{t('detail.coAdvisor')}</Tag>
                  {mentorship.co_advisor_talent_id ? (
                    <Link
                      onClick={() => navigate(`/lab/talents/${mentorship.co_advisor_talent_id}`)}
                    >
                      {mentorship.co_advisor}
                    </Link>
                  ) : (
                    <Text>{mentorship.co_advisor}</Text>
                  )}
                </div>
              )}
            </div>

            <Divider />

            {/* Students */}
            <div>
              <Title level={5}>
                <TeamOutlined style={{ marginRight: 6 }} />
                {t('detail.students')}
                {mentorship.students.length > 0 && (
                  <Tag style={{ marginLeft: 8 }}>
                    {t('detail.peopleCount', { n: mentorship.students.length })}
                  </Tag>
                )}
              </Title>
              {mentorship.students.length > 0 ? (
                <Row gutter={[12, 12]}>
                  {mentorship.students.map(s => (
                    <Col xs={24} sm={12} md={8} key={s.talent_id}>
                      <Card
                        size="small"
                        hoverable
                        onClick={() => navigate(`/lab/talents/${s.talent_id}`)}
                        style={{ borderRadius: 8 }}
                      >
                        <Space direction="vertical" size={2}>
                          <Text strong>{s.name}</Text>
                          <Space size={4}>
                            <Tag style={{ fontSize: 11 }}>{roleLabel(s.role_type)}</Tag>
                            {s.academic_level && (
                              <Tag color="blue" style={{ fontSize: 11 }}>
                                {levelLabel(s.academic_level)}
                              </Tag>
                            )}
                          </Space>
                          {s.cohort_year && (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {t('detail.cohortGrade', { year: s.cohort_year })}
                            </Text>
                          )}
                        </Space>
                      </Card>
                    </Col>
                  ))}
                </Row>
              ) : (
                <Text type="secondary">{t('detail.noStudents')}</Text>
              )}
            </div>
          </>
        ) : (
          <Text type="secondary">{t('detail.noMentorship')}</Text>
        )}
      </div>
    ),
  })

  // Add homepage tab only if talent has a homepage
  if (talent.homepage) {
    tabItems.push({
      key: 'homepage',
      label: (
        <span>
          <HomeOutlined style={{ marginRight: 4 }} />
          {t('detail.tabs.homepage')}
        </span>
      ),
      children: (
        <div>
          {previewLoading && (
            <div style={{ textAlign: 'center', padding: 48 }}>
              <Spin tip={t('detail.loadingHomepage')} />
            </div>
          )}
          {!previewLoading && preview?.status === 'ok' && (
            <iframe
              title="homepage-preview"
              srcDoc={preview.html}
              style={{
                width: '100%',
                minHeight: 600,
                border: '1px solid #e8e8e8',
                borderRadius: 8,
              }}
              sandbox="allow-same-origin allow-popups"
            />
          )}
          {!previewLoading && preview?.status === 'fetch_error' && (
            <Text type="secondary">{t('detail.homepageFetchError')}</Text>
          )}
          {!previewLoading && preview?.status?.startsWith('http_') && (
            <Text type="secondary">
              {t('detail.homepageHttpError', { status: preview.status })}
            </Text>
          )}
          {!previewLoading && preview?.status === 'no_homepage' && (
            <Text type="secondary">{t('detail.homepageMissing')}</Text>
          )}
          {!previewLoading && previewError && (
            <Text type="danger">{t('detail.homepagePreviewFailed')}</Text>
          )}
          {preview && (
            <div style={{ marginTop: 12, textAlign: 'right' }}>
              <Link href={talent.homepage} target="_blank" style={{ fontSize: 12 }}>
                {t('detail.openFullHomepage')}
              </Link>
            </div>
          )}
        </div>
      ),
    })
  }

  return (
    <div
      style={{
        padding: '80px 24px 24px',
        background: 'var(--color-bg-gray-light)',
        minHeight: '100vh',
      }}
    >
      <BreadcrumbNav
        items={[
          { label: t('common.labs'), path: '/lab' },
          { label: t('common.search'), path: '/lab/search' },
          { label: talent.name },
        ]}
      />

      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigateBack(navigate, '/lab/search')}
        style={{ marginBottom: 16 }}
      >
        {t('common.back')}
      </Button>

      <Row gutter={[24, 24]}>
        {/* Left: identity card (sticky) */}
        <Col xs={24} md={8} lg={7} xl={6}>
          <Card style={{ borderRadius: 12, position: 'sticky', top: 24 }}>
            <LabTalentHeader talent={talent} />
          </Card>
        </Col>

        {/* Right: tabbed content */}
        <Col xs={24} md={16} lg={17} xl={18}>
          <Card style={{ borderRadius: 12 }}>
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={tabItems}
              destroyInactiveTabPane={false}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default LabTalentDetailPage
