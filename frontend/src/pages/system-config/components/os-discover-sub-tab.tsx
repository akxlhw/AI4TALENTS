import { useEffect, useRef, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Col,
  Collapse,
  InputNumber,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd'
import { RadarChartOutlined, ImportOutlined, ReloadOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { api } from '../../../services/api'
import '../../../i18n/namespaces/system-config'
import { useTechDirectionOptions } from '../../../hooks/useIndustryQueries'
import { mergeGroupSelection } from './os-discover-selection'
import { getErrorMessage } from './utils'

const { Text, Title } = Typography

interface DiscoveredRepo {
  repo_full_name: string
  display_name: string
  description: string
  language: string | null
  stars: number
  contributors?: number
  html_url: string
  direction_codes: string[]
  element_codes?: string[]
  exists_in_config: boolean
}

interface DiscoverStatus {
  status: 'idle' | 'running' | 'completed' | 'cancelled' | 'error'
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
  const { t } = useTranslation(['systemConfig', 'common'])
  const { data: directions } = useTechDirectionOptions()
  const [selectedDirections, setSelectedDirections] = useState<string[]>([])
  const [minStars, setMinStars] = useState<number>(30000)
  const [minContributors, setMinContributors] = useState<number>(0)
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
  const directionNameMap = Object.fromEntries((directions || []).map(d => [d.code, d.name]))

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
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
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
        min_contributors: minContributors || 0,
      })
      message.success(t('osDiscover.started'))
      fetchStatus()
    } catch (e) {
      message.error(getErrorMessage(e, t('osDiscover.startFailed')))
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
        t('osDiscover.importResult', {
          created: created.length,
          skipped: skipped.length,
          failed: failed.length,
        })
      )
      if (created.length > 0) {
        message.success(t('osDiscover.imported', { n: created.length }))
        onImported?.()
      }
      // Refresh status to update exists_in_config flags
      fetchStatus()
      setSelectedRepos([])
    } catch (e) {
      message.error(getErrorMessage(e, t('osDiscover.importFailed')))
    } finally {
      setImporting(false)
    }
  }

  // Results render as one Table per direction group; each Table's
  // rowSelection.onChange reports only that group's keys, so selections must
  // MERGE into the global state — otherwise picking in one group wipes the
  // selections made in another.
  const handleGroupSelectionChange = (groupRepos: DiscoveredRepo[], keys: React.Key[]) => {
    setSelectedRepos(prev =>
      mergeGroupSelection(
        prev,
        groupRepos.map(r => r.repo_full_name),
        keys
      )
    )
  }

  const importableRepos = (status?.results || []).filter(r => !r.exists_in_config)
  const allImportableSelected =
    importableRepos.length > 0 &&
    importableRepos.every(r => selectedRepos.includes(r.repo_full_name))
  const handleSelectAll = () => {
    setSelectedRepos(allImportableSelected ? [] : importableRepos.map(r => r.repo_full_name))
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
    return Object.entries(groups).sort((a, b) => b[1].length - a[1].length)
  })()

  const isRunning = status?.status === 'running'
  const progressPercent =
    status && status.total > 0 ? Math.round((status.processed / status.total) * 100) : 0

  return (
    <div>
      {/* ── Control card ── */}
      <Card className="domain-card" size="small" style={{ borderRadius: 12, marginBottom: 16 }}>
        <Title level={5} style={{ marginTop: 0 }}>
          <RadarChartOutlined
            style={{ marginRight: 8, color: 'var(--domain-badge-bg, #6B46C1)' }}
          />
          {t('osDiscover.title')}
        </Title>
        <Text type="secondary" style={{ display: 'block', marginBottom: 16, fontSize: 13 }}>
          {t('osDiscover.description')}
        </Text>
        <Row gutter={[12, 12]} align="middle">
          <Col xs={24} md={12}>
            <Select
              mode="multiple"
              placeholder={t('osDiscover.directionsPlaceholder')}
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
          <Col xs={8} md={4}>
            <InputNumber
              style={{ width: '100%' }}
              min={1000}
              max={500000}
              step={5000}
              value={minStars}
              onChange={v => setMinStars(v ?? 30000)}
              formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={t => Number((t || '').replace(/,/g, ''))}
              addonBefore={t('osDiscover.starsAddon')}
              disabled={isRunning}
            />
          </Col>
          <Col xs={8} md={4}>
            <Tooltip title={t('osDiscover.contributorsTooltip')}>
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                max={100000}
                step={50}
                value={minContributors}
                onChange={v => setMinContributors(v ?? 0)}
                addonBefore={t('osDiscover.contributorsAddon')}
                disabled={isRunning}
              />
            </Tooltip>
          </Col>
          <Col xs={8} md={4}>
            <Button
              type="primary"
              block
              icon={<RadarChartOutlined />}
              loading={starting || isRunning}
              onClick={handleStart}
              disabled={isRunning}
            >
              {isRunning ? t('osDiscover.probing') : t('osDiscover.start')}
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
            format={() =>
              t('osDiscover.progressFormat', { processed: status.processed, total: status.total })
            }
          />
          <Text type="secondary" style={{ fontSize: 13 }}>
            {t('osDiscover.current', { name: directionNameMap[status.current] || status.current })}
            {status.found > 0 && t('osDiscover.foundSuffix', { n: status.found })}
            {status.errors > 0 && t('osDiscover.errorsSuffix', { n: status.errors })}
          </Text>
        </Card>
      )}

      {/* ── Error / Cancelled ── */}
      {status?.status === 'error' && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message={t('osDiscover.errorTitle')}
          description={t('osDiscover.errorDescription')}
        />
      )}
      {status?.status === 'cancelled' && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          message={t('osDiscover.cancelledTitle')}
          description={t('osDiscover.cancelledDescription')}
        />
      )}

      {/* ── Import bar + Results ── */}
      {status?.results && status.results.length > 0 && (
        <>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: 12,
            }}
          >
            <Text>
              {t('osDiscover.foundTotalPrefix')}
              <strong>{status.results.length}</strong>
              {t('osDiscover.foundTotalSuffix')}
              {importableRepos.length < status.results.length &&
                t('osDiscover.importableSuffix', { n: importableRepos.length })}
              {status.status === 'completed' && t('osDiscover.completedSuffix')}
            </Text>
            <Space>
              <Button size="small" icon={<ReloadOutlined />} onClick={fetchStatus}>
                {t('actions.refreshStatus')}
              </Button>
              <Button
                size="small"
                onClick={handleSelectAll}
                disabled={importableRepos.length === 0 || importing}
              >
                {allImportableSelected
                  ? t('osDiscover.deselectAll')
                  : t('osDiscover.selectAllImportable')}
              </Button>
              <Button
                size="small"
                onClick={() => setSelectedRepos([])}
                disabled={selectedRepos.length === 0 || importing}
              >
                {t('osDiscover.clearSelection')}
              </Button>
              <Button
                type="primary"
                size="small"
                icon={<ImportOutlined />}
                loading={importing}
                disabled={selectedRepos.length === 0}
                onClick={handleImport}
              >
                {t('osDiscover.importSelected', { n: selectedRepos.length })}
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
                    <Tag style={{ margin: 0 }}>
                      {t('osDiscover.projectCount', { n: repos.length })}
                    </Tag>
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
                      onChange: keys => handleGroupSelectionChange(repos, keys),
                      getCheckboxProps: r => ({ disabled: r.exists_in_config }),
                    }}
                    columns={[
                      {
                        title: t('osDiscover.columns.repo'),
                        dataIndex: 'repo_full_name',
                        width: 240,
                        render: (name: string, r: DiscoveredRepo) => (
                          <Space direction="vertical" size={0}>
                            <a
                              href={r.html_url}
                              target="_blank"
                              rel="noreferrer"
                              style={{ fontFamily: 'monospace' }}
                            >
                              {name}
                            </a>
                            {r.exists_in_config && (
                              <Tag color="default" style={{ fontSize: 10, margin: 0 }}>
                                {t('osDiscover.inLibrary')}
                              </Tag>
                            )}
                          </Space>
                        ),
                      },
                      {
                        title: t('osDiscover.columns.description'),
                        dataIndex: 'description',
                        ellipsis: true,
                        render: (d: string) => (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {d || '—'}
                          </Text>
                        ),
                      },
                      {
                        title: t('osDiscover.columns.stars'),
                        dataIndex: 'stars',
                        width: 90,
                        sorter: (a: DiscoveredRepo, b: DiscoveredRepo) => a.stars - b.stars,
                        render: (s: number) => (
                          <Text strong>{s >= 1000 ? `${(s / 1000).toFixed(1)}k` : s}</Text>
                        ),
                      },
                      {
                        title: t('osDiscover.columns.contributors'),
                        dataIndex: 'contributors',
                        width: 90,
                        sorter: (a: DiscoveredRepo, b: DiscoveredRepo) =>
                          (a.contributors ?? -1) - (b.contributors ?? -1),
                        render: (c: number | undefined) =>
                          c === undefined ? '—' : c >= 1000 ? `${(c / 1000).toFixed(1)}k` : c,
                      },
                      {
                        title: t('osDiscover.columns.language'),
                        dataIndex: 'language',
                        width: 100,
                        render: (l: string | null) =>
                          l ? <Tag style={{ margin: 0 }}>{l}</Tag> : '—',
                      },
                      {
                        title: t('osDiscover.columns.directions'),
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
          <Text type="secondary">{t('osDiscover.emptyHint')}</Text>
        </Card>
      )}
    </div>
  )
}

export default OsDiscoverSubTab
