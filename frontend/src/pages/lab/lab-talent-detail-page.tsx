import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Row, Col, Card, Descriptions, Tag, Typography, Button, Space, Divider, Spin } from 'antd'
import { ArrowLeftOutlined, HomeOutlined, MailOutlined, EyeOutlined } from '@ant-design/icons'
import { useLabTalent, useHomepagePreview } from '../../hooks/useLabQueries'
import { applyDomainCssVars } from '../../theme'
import PageSkeleton from '../../components/PageSkeleton'
import EmptyPlaceholder from '../../components/EmptyPlaceholder'
import BreadcrumbNav from '../../components/BreadcrumbNav'
import LabTalentHeader from './components/lab-talent-header'

const { Title, Text, Link } = Typography

const LabTalentDetailPage: React.FC = () => {
  const { talentId } = useParams<{ talentId: string }>()
  const navigate = useNavigate()
  const id = talentId ? Number(talentId) : undefined
  const { data: talent, isLoading, error } = useLabTalent(id)
  const [showPreview, setShowPreview] = useState(false)
  const { data: preview, isLoading: previewLoading, error: previewError } = useHomepagePreview(
    id,
    showPreview
  )

  useEffect(() => {
    applyDomainCssVars('lab')
  }, [])

  if (isLoading) return <PageSkeleton />

  if (error || !talent) {
    return (
      <EmptyPlaceholder
        title="人才不存在或已删除"
        description="该人才可能已被移除或链接有误"
        action={{ label: '返回搜索页', onClick: () => navigate('/lab/search') }}
      />
    )
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
        onClick={() => navigate(-1)}
        style={{ marginBottom: 16 }}
      >
        返回
      </Button>

      <Row gutter={[24, 24]}>
        <Col xs={24} md={8} lg={7} xl={6}>
          <Card style={{ borderRadius: 12, position: 'sticky', top: 24 }}>
            <LabTalentHeader talent={talent} />
          </Card>
        </Col>
        <Col xs={24} md={16} lg={17} xl={18}>
          <Card style={{ borderRadius: 12 }}>
            <Title level={4} style={{ marginTop: 0 }}>
              基本信息
            </Title>
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
              {talent.email && (
                <Descriptions.Item label="邮箱">
                  <Space>
                    <MailOutlined />
                    <Link href={`mailto:${talent.email}`}>{talent.email}</Link>
                  </Space>
                </Descriptions.Item>
              )}
              {talent.homepage && (
                <Descriptions.Item label="个人主页">
                  <Space>
                    <HomeOutlined />
                    <Link href={talent.homepage} target="_blank">
                      {talent.homepage}
                    </Link>
                  </Space>
                </Descriptions.Item>
              )}
            </Descriptions>

            {talent.research_areas && talent.research_areas.length > 0 && (
              <>
                <Divider />
                <Title level={4}>研究方向</Title>
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

          {/* Homepage preview — lazy loaded on user request */}
          {talent.homepage && (
            <Card
              style={{ borderRadius: 12, marginTop: 24 }}
              title={
                <Space>
                  <HomeOutlined />
                  <span>个人主页预览</span>
                </Space>
              }
              extra={
                !showPreview && (
                  <Button
                    type="primary"
                    ghost
                    icon={<EyeOutlined />}
                    onClick={() => setShowPreview(true)}
                  >
                    加载预览
                  </Button>
                )
              }
            >
              {!showPreview && (
                <Text type="secondary">
                  点击"加载预览"在此页面内查看该人才的个人主页内容
                </Text>
              )}
              {showPreview && previewLoading && (
                <div style={{ textAlign: 'center', padding: 48 }}>
                  <Spin tip="正在抓取个人主页..." />
                </div>
              )}
              {showPreview && !previewLoading && preview?.status === 'ok' && (
                <iframe
                  title="homepage-preview"
                  srcDoc={preview.html}
                  style={{
                    width: '100%',
                    minHeight: 500,
                    border: '1px solid #e8e8e8',
                    borderRadius: 8,
                  }}
                  sandbox="allow-same-origin allow-popups"
                />
              )}
              {showPreview && !previewLoading && preview?.status === 'fetch_error' && (
                <Text type="secondary">
                  无法抓取该主页，可能是网络问题或目标网站限制访问。
                </Text>
              )}
              {showPreview && !previewLoading && preview?.status?.startsWith('http_') && (
                <Text type="secondary">
                  目标网站返回了 {preview.status}，暂时无法预览。
                </Text>
              )}
              {showPreview && !previewLoading && previewError && (
                <Text type="danger">预览加载失败，请稍后重试。</Text>
              )}
              {showPreview && preview && (
                <div style={{ marginTop: 12, textAlign: 'right' }}>
                  <Link href={talent.homepage} target="_blank" style={{ fontSize: 12 }}>
                    在新标签页打开完整主页 →
                  </Link>
                </div>
              )}
            </Card>
          )}
        </Col>
      </Row>
    </div>
  )
}

export default LabTalentDetailPage
