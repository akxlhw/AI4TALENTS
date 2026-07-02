import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card,
  Descriptions,
  Spin,
  Tag,
  Typography,
  Button,
  Space,
  Empty,
  Divider,
} from 'antd'
import { ArrowLeftOutlined, HomeOutlined, MailOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import { getErrorMessage } from '../../utils'
import type { LabTalentDetail } from '../../types'

const { Title, Text, Link } = Typography

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

const LabTalentDetailPage: React.FC = () => {
  const { talentId } = useParams<{ talentId: string }>()
  const navigate = useNavigate()
  const [talent, setTalent] = useState<LabTalentDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      if (!talentId) return
      try {
        setLoading(true)
        const res = await api.lab.getTalent(Number(talentId))
        setTalent(res.data)
      } catch (e) {
        import('antd').then(({ message }) => message.error(getErrorMessage(e, '加载详情失败')))
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [talentId])

  if (loading) {
    return (
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!talent) {
    return (
      <div style={{ padding: 48, textAlign: 'center' }}>
        <Empty description="未找到该人才" />
        <Button onClick={() => navigate('/lab/search')} style={{ marginTop: 16 }}>
          返回搜索
        </Button>
      </div>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate('/lab/search')}
        style={{ marginBottom: 16 }}
      >
        返回
      </Button>

      <Card>
        <Title level={3}>
          {talent.name}
          <Space style={{ marginLeft: 12 }}>
            <Tag>{ROLE_LABELS[talent.role_type] || talent.role_type}</Tag>
            {talent.academic_level && (
              <Tag color="blue">{LEVEL_LABELS[talent.academic_level] || talent.academic_level}</Tag>
            )}
          </Space>
        </Title>
        {talent.current_title && (
          <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
            {talent.current_title}
          </Text>
        )}

        <Descriptions column={1} bordered size="small">
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
                {talent.email}
              </Space>
            </Descriptions.Item>
          )}
          {talent.homepage && (
            <Descriptions.Item label="个人主页">
              <Link href={talent.homepage} target="_blank">
                <Space>
                  <HomeOutlined />
                  {talent.homepage}
                </Space>
              </Link>
            </Descriptions.Item>
          )}
        </Descriptions>

        {talent.research_areas && talent.research_areas.length > 0 && (
          <>
            <Divider />
            <Text strong>研究方向</Text>
            <div style={{ marginTop: 8 }}>
              <Space size={8} wrap>
                {talent.research_areas.map((a) => (
                  <Tag key={a} color="geekblue">
                    {a}
                  </Tag>
                ))}
              </Space>
            </div>
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
    </div>
  )
}

export default LabTalentDetailPage
