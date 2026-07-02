import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Input,
  Select,
  Spin,
  Empty,
  Typography,
  Pagination,
  Tag,
  Space,
} from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { api } from '../../services/api'
import { getErrorMessage } from '../../utils'
import type { LabTalent } from '../../types'

const { Text } = Typography

const ROLE_OPTIONS = [
  { label: '全部角色', value: '' },
  { label: '教授', value: 'professor' },
  { label: '学生', value: 'student' },
  { label: '博后/研究员', value: 'graduate' },
]

const LEVEL_OPTIONS = [
  { label: '全部学位', value: '' },
  { label: '博士', value: 'phd' },
  { label: '硕士', value: 'master' },
  { label: '学士', value: 'bachelor' },
]

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

const LabSearchPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [items, setItems] = useState<LabTalent[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [keyword, setKeyword] = useState(searchParams.get('keyword') || '')
  const [parentLab, setParentLab] = useState(searchParams.get('parent_lab') || '')
  const [labName, setLabName] = useState(searchParams.get('lab_name') || '')
  const [roleType, setRoleType] = useState(searchParams.get('role_type') || '')
  const [academicLevel, setAcademicLevel] = useState(searchParams.get('academic_level') || '')
  const [page, setPage] = useState(1)
  const pageSize = 20

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const params: Record<string, unknown> = { page, page_size: pageSize }
      if (keyword) params.keyword = keyword
      if (parentLab) params.parent_lab = parentLab
      if (labName) params.lab_name = labName
      if (roleType) params.role_type = roleType
      if (academicLevel) params.academic_level = academicLevel
      const res = await api.lab.listTalents(params)
      setItems(res.data.items || [])
      setTotal(res.data.total || 0)
    } catch (e) {
      import('antd').then(({ message }) => message.error(getErrorMessage(e, '加载失败')))
    } finally {
      setLoading(false)
    }
  }, [keyword, parentLab, labName, roleType, academicLevel, page])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Sync filters to URL
  useEffect(() => {
    const params: Record<string, string> = {}
    if (keyword) params.keyword = keyword
    if (parentLab) params.parent_lab = parentLab
    if (labName) params.lab_name = labName
    if (roleType) params.role_type = roleType
    if (academicLevel) params.academic_level = academicLevel
    setSearchParams(params, { replace: true })
  }, [keyword, parentLab, labName, roleType, academicLevel, setSearchParams])

  return (
    <div style={{ padding: 24 }}>
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col xs={24} sm={6}>
            <Input
              placeholder="姓名关键词"
              prefix={<SearchOutlined />}
              value={keyword}
              onChange={(e) => {
                setKeyword(e.target.value)
                setPage(1)
              }}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6}>
            <Input
              placeholder="顶级实验室"
              value={parentLab}
              onChange={(e) => {
                setParentLab(e.target.value)
                setPage(1)
              }}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6}>
            <Input
              placeholder="研究组"
              value={labName}
              onChange={(e) => {
                setLabName(e.target.value)
                setPage(1)
              }}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6}>
            <Select
              placeholder="角色"
              style={{ width: '100%' }}
              value={roleType || undefined}
              onChange={(v) => {
                setRoleType(v || '')
                setPage(1)
              }}
              options={ROLE_OPTIONS}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6}>
            <Select
              placeholder="学位层次"
              style={{ width: '100%' }}
              value={academicLevel || undefined}
              onChange={(v) => {
                setAcademicLevel(v || '')
                setPage(1)
              }}
              options={LEVEL_OPTIONS}
              allowClear
            />
          </Col>
        </Row>
      </Card>

      <Spin spinning={loading}>
        {items.length === 0 && !loading ? (
          <Empty description="未找到匹配的人才" />
        ) : (
          <>
            <Row gutter={[16, 16]}>
              {items.map((t) => (
                <Col xs={24} sm={12} md={8} lg={6} key={t.talent_id}>
                  <Card
                    hoverable
                    size="small"
                    onClick={() => navigate(`/lab/talents/${t.talent_id}`)}
                  >
                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      <Text strong>{t.name}</Text>
                      <Space size={4} wrap>
                        <Tag>{ROLE_LABELS[t.role_type] || t.role_type}</Tag>
                        {t.academic_level && (
                          <Tag color="blue">{LEVEL_LABELS[t.academic_level] || t.academic_level}</Tag>
                        )}
                      </Space>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {t.parent_lab}
                      </Text>
                      {t.lab_name && t.lab_name !== t.parent_lab && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {t.lab_name}
                        </Text>
                      )}
                      {t.current_title && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {t.current_title}
                        </Text>
                      )}
                      {t.research_areas && t.research_areas.length > 0 && (
                        <Space size={4} wrap>
                          {t.research_areas.slice(0, 3).map((a) => (
                            <Tag key={a} color="geekblue" style={{ fontSize: 11 }}>
                              {a}
                            </Tag>
                          ))}
                        </Space>
                      )}
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
            <div style={{ textAlign: 'center', marginTop: 24 }}>
              <Pagination
                current={page}
                total={total}
                pageSize={pageSize}
                onChange={(p) => setPage(p)}
                showTotal={(t) => `共 ${t} 人`}
              />
            </div>
          </>
        )}
      </Spin>
    </div>
  )
}

export default LabSearchPage
