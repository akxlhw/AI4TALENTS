import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Row, Col, Card, Descriptions, Tag, Typography, Button, Space, Divider } from 'antd'
import { ArrowLeftOutlined, HomeOutlined, MailOutlined } from '@ant-design/icons'
import { useLabTalent } from '../../hooks/useLabQueries'
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
    <div style={{ padding: 24, background: 'var(--color-bg-gray-light)', minHeight: '100vh' }}>
      <BreadcrumbNav
        items={[
          { label: '实验室', path: '/lab' },
          { label: '搜索', path: '/lab/search' },
          { label: talent.name },
        ]}
      />

      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} style={{ marginBottom: 16 }}>
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
            <Title level={4} style={{ marginTop: 0 }}>基本信息</Title>
            <Descriptions column={1} bordered size="small" labelStyle={{ width: 140 }}>
              <Descriptions.Item label="顶级实验室">{talent.parent_lab}</Descriptions.Item>
              {talent.lab_name && talent.lab_name !== talent.parent_lab && (
                <Descriptions.Item label="研究组">{talent.lab_name}</Descriptions.Item>
              )}
              {talent.department && <Descriptions.Item label="院系">{talent.department}</Descriptions.Item>}
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
                    <Link href={talent.homepage} target="_blank">{talent.homepage}</Link>
                  </Space>
                </Descriptions.Item>
              )}
            </Descriptions>

            {talent.research_areas && talent.research_areas.length > 0 && (
              <>
                <Divider />
                <Title level={4}>研究方向</Title>
                <Space size={8} wrap>
                  {talent.research_areas.map((a) => (
                    <Tag key={a} color="geekblue">{a}</Tag>
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
        </Col>
      </Row>
    </div>
  )
}

export default LabTalentDetailPage
