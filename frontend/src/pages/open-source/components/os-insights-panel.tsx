import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Alert, Button, Card, Col, Collapse, Empty, Row, Spin, Statistic, Typography } from 'antd'
import { BarChartOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { api } from '../../../services/api'
import type { OSInsightsResponse } from '../../../services/api/openSource'
import type { OSSearchQuery } from '../../../types'
import { useTechElements } from '@/constants/tech-elements'

const { Text } = Typography

interface Props {
  query: OSSearchQuery
}

function barOption(entries: [string, number][], color: string): EChartsOption {
  return {
    grid: { left: 8, right: 32, top: 8, bottom: 8, containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: entries.map(([k]) => k).reverse() },
    series: [
      {
        type: 'bar',
        data: entries.map(([, v]) => v).reverse(),
        itemStyle: { color },
        label: { show: true, position: 'right', fontWeight: 'bold', color: '#000' },
      },
    ],
    tooltip: { trigger: 'axis' },
  }
}

const OsInsightsPanel: React.FC<Props> = ({ query }) => {
  const { fullLabel } = useTechElements()
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<OSInsightsResponse | null>(null)
  const [error, setError] = useState(false)

  // 最新 query 的 ref：fetchInsights 保持引用稳定（不随 query 身份变化重建），
  // 但发起请求时读取的是最新筛选值
  const queryRef = useRef(query)
  queryRef.current = query
  // 请求序号：旧请求晚返回时丢弃其响应，避免覆盖新筛选的结果
  const requestIdRef = useRef(0)

  // 仅聚合端点实际消费的 11 个筛选字段参与签名；page/sort_by/mode 等
  // 不改变签名，翻页/排序/模式切换不会触发重取
  const filtersKey = useMemo(
    () =>
      JSON.stringify({
        q: query.q,
        tech_elements: query.tech_elements,
        languages: query.languages,
        location: query.location,
        company: query.company,
        repo_full_names: query.repo_full_names,
        is_committer: query.is_committer,
        is_student: query.is_student,
        has_contact: !!query.has_contact,
        china_related: !!query.china_related,
        top_org: !!query.top_org,
      }),
    [query]
  )

  const fetchInsights = useCallback(async () => {
    const requestId = ++requestIdRef.current
    const q = queryRef.current
    setLoading(true)
    try {
      const res = await api.openSource.getDeveloperInsights({
        q: q.q,
        tech_elements: q.tech_elements,
        languages: q.languages,
        location: q.location,
        company: q.company,
        repo_full_names: q.repo_full_names,
        is_committer: q.is_committer,
        is_student: q.is_student,
        has_contact: q.has_contact || undefined,
        china_related: q.china_related || undefined,
        top_org: q.top_org || undefined,
      })
      if (requestId !== requestIdRef.current) return
      setData(res.data)
      setError(false)
    } catch {
      if (requestId !== requestIdRef.current) return
      setData(null)
      setError(true)
    } finally {
      if (requestId === requestIdRef.current) setLoading(false)
    }
  }, [])

  // 展开时请求；筛选变化（filtersKey 变化）且面板处于展开态时自动刷新
  useEffect(() => {
    if (open) fetchInsights()
  }, [open, filtersKey, fetchInsights])

  const techEntries = useMemo(
    () =>
      Object.entries(data?.tech_element_distribution ?? {}).map(([code, n]) => [
        fullLabel(code),
        n,
      ]) as [string, number][],
    [data, fullLabel]
  )
  const repoEntries = useMemo(
    () =>
      (data?.repo_distribution ?? []).map(
        r => [r.repo_full_name, r.developer_count] as [string, number]
      ),
    [data]
  )
  const companyEntries = useMemo(() => Object.entries(data?.company_distribution ?? {}), [data])

  const contactRate =
    data && data.total > 0 ? ((data.contactable / data.total) * 100).toFixed(1) : '0.0'

  return (
    <Collapse
      style={{ marginTop: 16 }}
      onChange={keys => setOpen(keys.length > 0)}
      items={[
        {
          key: 'insights',
          label: (
            <span>
              <BarChartOutlined style={{ marginRight: 6 }} />
              命中人才洞察（管理员）
            </span>
          ),
          children: (
            <Spin spinning={loading} style={{ minHeight: 120 }}>
              {error && !loading && (
                <Alert
                  type="error"
                  message="洞察加载失败"
                  showIcon
                  action={
                    <Button size="small" onClick={fetchInsights}>
                      重试
                    </Button>
                  }
                />
              )}
              {!error && !data && !loading && <Empty description="展开后加载洞察数据" />}
              {data && data.total === 0 && <Empty description="当前筛选无命中人才" />}
              {data && data.total > 0 && (
                <>
                  <Row gutter={16} style={{ marginBottom: 8 }}>
                    <Col span={6}>
                      <Card size="small">
                        <Statistic title="命中人数" value={data.total} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card size="small">
                        <Statistic
                          title="可触达（有联系方式）"
                          value={`${data.contactable} / ${data.total}`}
                          suffix={
                            <Text type="secondary" style={{ fontSize: 14 }}>
                              {contactRate}%
                            </Text>
                          }
                        />
                      </Card>
                    </Col>
                  </Row>
                  <Row gutter={16}>
                    <Col xs={24} lg={8}>
                      <Card size="small" title="技术要素分布">
                        <ReactECharts
                          option={barOption(techEntries, '#6B46C1')}
                          style={{ height: 260 }}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} lg={8}>
                      <Card size="small" title="来源仓库 Top 10">
                        <ReactECharts
                          option={barOption(repoEntries, '#0891B2')}
                          style={{ height: 260 }}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} lg={8}>
                      <Card size="small" title="当前公司 Top 10">
                        <ReactECharts
                          option={barOption(companyEntries, '#16A34A')}
                          style={{ height: 260 }}
                        />
                      </Card>
                    </Col>
                  </Row>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    统计范围为当前筛选条件的全部命中人才；语义/混合搜索模式下按关键词等价条件统计。
                  </Text>
                </>
              )}
            </Spin>
          ),
        },
      ]}
    />
  )
}

export default OsInsightsPanel
