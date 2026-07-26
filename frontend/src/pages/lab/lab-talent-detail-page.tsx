import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import type { TabsProps } from 'antd'
import { Row, Col, Card, Descriptions, Tag, Typography, Button, Space, Divider, Spin, Tabs } from 'antd'
import { ArrowLeftOutlined, HomeOutlined, TeamOutlined, UserSwitchOutlined } from '@ant-design/icons'
import { useLabTalent, useHomepagePreview, useMentorship } from '../../hooks/useLabQueries'
import { applyDomainCssVars } from '../../theme'
import { getErrorMessage } from '../../utils'
import { navigateBack } from '../../utils/navigation'
import { ROLE_LABELS, LEVEL_LABELS } from './constants/lab-role'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import BreadcrumbNav from '../../components/BreadcrumbNav'
import LabTalentHeader from './components/lab-talent-header'

const { Title, Text, Link } = Typography

const LabTalentDetailPage: React.FC = () => {
  const { talentId } = useParams<{ talentId: string }>()
  const navigate = useNavigate()
  const id = talentId ? Number(talentId) : undefined
  const { data: talent, isLoading, error, refetch } = useLabTalent(id)

  // Tab state: 'info' | 'mentorship' | 'homepage'
  const [activeTab, setActiveTab] = useState('info')
  // Load preview when user switches to homepage tab
  const { data: preview, isLoading: previewLoading, error: previewError } = useHomepagePreview(
    id,
    activeTab === 'homepage'
  )
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
        title="加载失败"
        description={getErrorMessage(error, '加载人才详情失败，请稍后重试')}
        action={{ label: '重试', onClick: () => refetch() }}
      />
    )
  }

  if (!talent) {
    return (
      <EmptyPlaceholder
        title="人才不存在或已删除"
        description="该人才可能已被移除或链接有误"
        action={{ label: '返回搜索页', onClick: () => navigate('/lab/search') }}
      />
    )
  }

  const tabItems: TabsProps['items'] = [
    {
      key: 'info',
      label: '基本信息',
      children: (
        <Card style={{ borderRadius: 12, border: 'none' }}>
          <Descriptions column={1} bordered size="small" labelStyle={{ width: 140 }}>
            <Descriptions.Item label="顶级实验室">{talent.parent_lab}</Descriptions.Item>
            {talent.lab_name && talent.lab_name !== talent.parent_lab && (
              <Descriptions.Item label="研究组">{talent.lab_name}</Descriptions.Item>
            )}
            {talent.department && (
              <Descriptions.Item label="院系">{talent.department}</Descriptions.Item>
            )}
            {talent.cohort_year && (
              <Descriptions.Item label="入学/加入年份">{talent.cohort_year}</Descriptions.Item>
            )}
            {talent.cohort_source && (
              <Descriptions.Item label="届别来源">{talent.cohort_source}</Descriptions.Item>
            )}
          </Descriptions>

          {talent.research_areas && talent.research_areas.length > 0 && (
            <>
              <Divider />
              <Title level={5}>研究方向</Title>
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
            数据来源：{talent.parent_lab} 官网
            {talent.collected_at && ` · 采集于 ${talent.collected_at.slice(0, 10)}`}
          </Text>
          {talent.source_detail_url && (
            <div>
              <Link href={talent.source_detail_url} target="_blank" style={{ fontSize: 12 }}>
                查看来源页面
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
        师承关系
      </span>
    ),
    children: (
      <div style={{ minHeight: 200 }}>
        {mentorshipLoading ? (
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin tip="加载师承关系..." />
          </div>
        ) : mentorship ? (
          <>
            {/* Advisors */}
            <div style={{ marginBottom: 24 }}>
              <Title level={5}>
                <UserSwitchOutlined style={{ marginRight: 6 }} />
                导师
              </Title>
              {mentorship.advisor ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <Tag color="blue">导师</Tag>
                  {mentorship.advisor_talent_id ? (
                    <Link onClick={() => navigate(`/lab/talents/${mentorship.advisor_talent_id}`)}>
                      {mentorship.advisor}
                    </Link>
                  ) : (
                    <Text>{mentorship.advisor}</Text>
                  )}
                </div>
              ) : (
                <Text type="secondary">未收录导师信息</Text>
              )}
              {mentorship.co_advisor && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Tag color="cyan">共同导师</Tag>
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
                指导的学生
                {mentorship.students.length > 0 && (
                  <Tag style={{ marginLeft: 8 }}>{mentorship.students.length} 人</Tag>
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
                            <Tag style={{ fontSize: 11 }}>
                              {ROLE_LABELS[s.role_type] || s.role_type}
                            </Tag>
                            {s.academic_level && (
                              <Tag color="blue" style={{ fontSize: 11 }}>
                                {LEVEL_LABELS[s.academic_level] || s.academic_level}
                              </Tag>
                            )}
                          </Space>
                          {s.cohort_year && (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {s.cohort_year} 级
                            </Text>
                          )}
                        </Space>
                      </Card>
                    </Col>
                  ))}
                </Row>
              ) : (
                <Text type="secondary">暂无收录指导的学生</Text>
              )}
            </div>
          </>
        ) : (
          <Text type="secondary">暂无师承关系数据</Text>
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
          个人主页
        </span>
      ),
      children: (
        <div>
          {previewLoading && (
            <div style={{ textAlign: 'center', padding: 48 }}>
              <Spin tip="正在加载个人主页..." />
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
            <Text type="secondary">
              无法加载该主页，可能是网络问题或目标网站限制访问。
            </Text>
          )}
          {!previewLoading && preview?.status?.startsWith('http_') && (
            <Text type="secondary">
              目标网站返回了 {preview.status}，暂时无法预览。
            </Text>
          )}
          {!previewLoading && preview?.status === 'no_homepage' && (
            <Text type="secondary">该人才未提供个人主页。</Text>
          )}
          {!previewLoading && previewError && (
            <Text type="danger">预览加载失败，请稍后重试。</Text>
          )}
          {preview && (
            <div style={{ marginTop: 12, textAlign: 'right' }}>
              <Link href={talent.homepage} target="_blank" style={{ fontSize: 12 }}>
                在新标签页打开完整主页 →
              </Link>
            </div>
          )}
        </div>
      ),
    })
  }

  return (
    <div style={{ padding: '80px 24px 24px', background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      <BreadcrumbNav
        items={[
          { label: '实验室', path: '/lab' },
          { label: '搜索', path: '/lab/search' },
          { label: talent.name },
        ]}
      />

      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigateBack(navigate, '/lab/search')}
        style={{ marginBottom: 16 }}
      >
        返回
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
