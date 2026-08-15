import { useEffect, useRef, useState } from 'react'
import {
  Alert, Button, Card, Col, Collapse, InputNumber, Progress, Row, Select,
  Space, Spin, Table, Tag, Typography, message,
} from 'antd'
import { RadarChartOutlined, ImportOutlined, ReloadOutlined } from '@ant-design/icons'
import { api } from '../../../services/api'
import { useTechDirectionOptions } from '../../../hooks/useIndustryQueries'
import { getErrorMessage } from './utils'

const { Text, Title } = Typography

interface DiscoveredRepo {
  repo_full_name: string
  display_name: string
  description: string
  language: string | null
  stars: number
  html_url: string
  direction_codes: string[]
  element_codes?: string[]
  exists_in_config: boolean
}

interface DiscoverStatus {
  status: 'idle' | 'running' | 'completed' | 'error'
  processed: number
  total: number
  current: string
  found: number
  errors: number
  results: DiscoveredRepo[]
  params?: { direction_codes?: string[]; min_stars?: number }
}

/** Auto-discover well-known repos (stars >= threshold) by tech direction.
 * Embedded inside the repo-config page: onImported refreshes the repo table
 * after a successful import so new repos show up immediately. */
const OsDiscoverSubTab: React.FC<{ onImported?: () => void }> = ({ onImported }) => {
  const { data: directions } = useTechDirectionOptions()
  const [selectedDirections, setSelectedDirections] = useState<string[]>([])
  const [minStars, setMinStars] = useState<number>(30000)
  const [starting, setStarting] = useState(false)
  const [status, setStatus] = useState<DiscoverStatus | null>(null)
  const [selectedRepos, setSelectedRepos] = useState<React.Key[]>([])
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Direction options grouped by domain
  const directionOptions = (directions || []).map(d => ({
    value: d.code,
    label: `${d.name}（${d.domainName}）`,
  }))
  const directionNameMap = Object.fromEntries(
    (directions || []).map(d => [d.code, d.name])
  )

  const fetchStatus = async () => {
    try {
      const res = await api.openSource.getDiscoveryStatus()
      setStatus(res.data)
      return res.data as DiscoverStatus
    } catch {
      return null
    }
  }

  // Poll while running
  useEffect(() => {
    fetchStatus()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  useEffect(() => {
    if (status?.status === 'running') {
      if (!pollRef.current) {
        pollRef.current = setInterval(fetchStatus, 3000)
      }
    } else if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [status?.status])

  const handleStart = async () => {
    setStarting(true)
    setImportResult(null)
    setSelectedRepos([])
    try {
      await api.openSource.startDiscovery({
        direction_codes: selectedDirections,
        min_stars: minStars || 30000,
      })
      message.success('探测任务已启动，结果将实时更新')
      fetchStatus()
    } catch (e) {
      message.error(getErrorMessage(e, '启动探测失败'))
    } finally {
      setStarting(false)
    }
  }

  const handleImport = async () => {
    if (selectedRepos.length === 0 || !status) return
    setImporting(true)
    try {
      const selected = status.results.filter(
        r => selectedRepos.includes(r.repo_full_name) && !r.exists_in_config
      )
      // Backend results carry element_codes (union across hit directions,
      // taxonomy v2 element layer) — use them directly for import tagging.
      const repos = selected.map(r => ({
        repo_full_name: r.repo_full_name,
        tech_element: r.element_codes?.length ? r.element_codes : ['models'],
      }))
      const res = await api.openSource.importDiscovered(repos)
      const { created, skipped, failed } = res.data
      setImportResult(
        `导入完成：成功 ${created.length}，已存在 ${skipped.length}，失败 ${failed.length}`
      )
      if (created.length > 0) {
        message.success(`已导入 ${created.length} 个仓库，见下方仓库配置列表`)
        onImported?.()
      }
      // Refresh status to update exists_in_config flags
      fetchStatus()
      setSelectedRepos([])
    } catch (e) {
      message.error(getErrorMessage(e, '导入失败'))
    } finally {
      setImporting(false)
    }
  }

  // Group results by primary direction for display
  const grouped = (() => {
    if (!status?.results) return []
    const groups: Record<string, DiscoveredRepo[]> = {}
    for (const r of status.results) {
      const key = r.direction_codes[0] || 'other'
      if (!groups[key]) groups[key] = []
      groups[key].push(r)
    }
    return Object.entries(groups).sort(
      (a, b) => b[1].length - a[1].length
    )
  })()

  const isRunning = status?.status === 'running'
  const progressPercent = status && status.total > 0
    ? Math.round((status.processed / status.total) * 100) : 0

  return (
    <div>
      {/* ── Control card ── */}
      <Card className="domain-card" size="small" style={{ borderRadius: 12, marginBottom: 16 }}>
        <Title level={5} style={{ marginTop: 0 }}>
          <RadarChartOutlined style={{ marginRight: 8, color: 'var(--domain-badge-bg, #6B46C1)' }} />
          自动探测知名开源项目
        </Title>
        <Text type="secondary" style={{ display: 'block', marginBottom: 16, fontSize: 13 }}>
          按技术方向搜索 GitHub 上 star 达标的知名开源项目（只预览不入库，勾选后可导入仓库配置）。
          探测 22 个方向约需 2-5 分钟（受 GitHub Search API 限速约束）。
        </Text>
        <Row gutter={[12, 12]} align="middle">
          <Col xs={24} md={14}>
            <Select
              mode="multiple"
              placeholder="选择技术方向（留空 = 全部 75 个方向）"
              style={{ width: '100%' }}
              value={selectedDirections}
              onChange={setSelectedDirections}
              options={directionOptions}
              allowClear
              showSearch
              optionFilterProp="label"
              disabled={isRunning}
            />
          </Col>
          <Col xs={12} md={5}>
            <InputNumber
              style={{ width: '100%' }}
              min={1000}
              max={500000}
              step={5000}
              value={minStars}
              onChange={v => setMinStars(v ?? 30000)}
              formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={t => Number((t || '').replace(/,/g, ''))}
              addonBefore="Star ≥"
              disabled={isRunning}
            />
          </Col>
          <Col xs={12} md={5}>
            <Button
              type="primary"
              block
              icon={<RadarChartOutlined />}
              loading={starting || isRunning}
              onClick={handleStart}
              disabled={isRunning}
            >
              {isRunning ? '探测中…' : '开始探测'}
            </Button>
          </Col>
        </Row>
      </Card>

      {/* ── Progress ── */}
      {isRunning && status && (
        <Card className="domain-card" size="small" style={{ borderRadius: 12, marginBottom: 16 }}>
          <Progress
            percent={progressPercent}
            status="active"
            format={() => `${status.processed}/${status.total} 方向`}
          />
          <Text type="secondary" style={{ fontSize: 13 }}>
            当前：{directionNameMap[status.current] || status.current}
            {status.found > 0 && ` · 已发现 ${status.found} 个项目`}
            {status.errors > 0 && ` · ${status.errors} 次搜索失败`}
          </Text>
        </Card>
      )}

      {/* ── Error ── */}
      {status?.status === 'error' && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message="探测任务异常终止"
          description="可能是网络或 GitHub API 限速导致，稍后可重新探测（已发现的部分结果保留在下表）。"
        />
      )}

      {/* ── Import bar + Results ── */}
      {status?.results && status.results.length > 0 && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <Text>
              共发现 <strong>{status.results.length}</strong> 个项目
              {status.status === 'completed' && '（探测完成）'}
            </Text>
            <Space>
              <Button size="small" icon={<ReloadOutlined />} onClick={fetchStatus}>
                刷新状态
              </Button>
              <Button
                type="primary"
                size="small"
                icon={<ImportOutlined />}
                loading={importing}
                disabled={selectedRepos.length === 0}
                onClick={handleImport}
              >
                导入选中的 {selectedRepos.length} 个仓库
              </Button>
            </Space>
          </div>
          {importResult && (
            <Alert type="success" showIcon message={importResult} style={{ marginBottom: 12 }} />
          )}

          <Spin spinning={importing}>
            <Collapse
              defaultActiveKey={grouped.slice(0, 3).map(([k]) => k)}
              items={grouped.map(([direction, repos]) => ({
                key: direction,
                label: (
                  <Space>
                    <Text strong>{directionNameMap[direction] || direction}</Text>
                    <Tag style={{ margin: 0 }}>{repos.length} 个项目</Tag>
                  </Space>
                ),
                children: (
                  <Table
                    size="small"
                    rowKey="repo_full_name"
                    dataSource={repos}
                    pagination={false}
                    rowSelection={{
                      selectedRowKeys: selectedRepos,
                      onChange: setSelectedRepos,
                      getCheckboxProps: r => ({ disabled: r.exists_in_config }),
                    }}
                    columns={[
                      {
                        title: '仓库',
                        dataIndex: 'repo_full_name',
                        width: 240,
                        render: (name: string, r: DiscoveredRepo) => (
                          <Space direction="vertical" size={0}>
                            <a href={r.html_url} target="_blank" rel="noreferrer" style={{ fontFamily: 'monospace' }}>
                              {name}
                            </a>
                            {r.exists_in_config && (
                              <Tag color="default" style={{ fontSize: 10, margin: 0 }}>已在库</Tag>
                            )}
                          </Space>
                        ),
                      },
                      {
                        title: '描述',
                        dataIndex: 'description',
                        ellipsis: true,
                        render: (d: string) => (
                          <Text type="secondary" style={{ fontSize: 12 }}>{d || '—'}</Text>
                        ),
                      },
                      {
                        title: 'Star',
                        dataIndex: 'stars',
                        width: 90,
                        sorter: (a: DiscoveredRepo, b: DiscoveredRepo) => a.stars - b.stars,
                        render: (s: number) => (
                          <Text strong>{s >= 1000 ? `${(s / 1000).toFixed(1)}k` : s}</Text>
                        ),
                      },
                      {
                        title: '语言',
                        dataIndex: 'language',
                        width: 100,
                        render: (l: string | null) => l ? <Tag style={{ margin: 0 }}>{l}</Tag> : '—',
                      },
                      {
                        title: '命中方向',
                        dataIndex: 'direction_codes',
                        width: 160,
                        render: (codes: string[]) => (
                          <Space size={2} wrap>
                            {codes.map(c => (
                              <Tag key={c} style={{ fontSize: 10, margin: 0 }}>
                                {directionNameMap[c] || c}
                              </Tag>
                            ))}
                          </Space>
                        ),
                      },
                    ]}
                  />
                ),
              }))}
            />
          </Spin>
        </>
      )}

      {/* ── Empty hint ── */}
      {(!status || (status.status === 'idle' && status.results.length === 0)) && (
        <Card className="domain-card" size="small" style={{ borderRadius: 12 }}>
          <Text type="secondary">
            尚无探测结果。选择方向（或留空探测全部）并设置 star 阈值后，点击「开始探测」。
          </Text>
        </Card>
      )}
    </div>
  )
}

export default OsDiscoverSubTab
