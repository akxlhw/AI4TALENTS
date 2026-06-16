import { useMemo, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { Empty, Spin, Typography, Space, Select, Slider, Card, Row, Col, Badge, Alert } from 'antd'

const { Text } = Typography

interface GenealogyNode {
  talent_id: number
  name: string
  institution?: string | null
  composite_score: number
  tier: string
  h_index: number
  cited_by_count: number
  is_root: boolean
}

interface GenealogyLink {
  source: number
  target: number
  type: string
  confidence: number
  shared_institution: boolean
  evidence_count: number
  first_year?: number | null
  last_year?: number | null
}

interface GenealogyGraphProps {
  rootTalent: GenealogyNode
  nodes: GenealogyNode[]
  links: GenealogyLink[]
  loading?: boolean
  onNodeClick?: (nodeId: number) => void
}

const TIER_COLORS: Record<string, string> = {
  tier1: '#e94560',
  tier2: '#ffa726',
  tier3: '#42a5f5',
  tier4: '#66bb6a',
}

const TIER_NAMES: Record<string, string> = {
  tier1: '学术领军',
  tier2: '中坚学者',
  tier3: '青年才俊',
  tier4: '新锐研究者',
}

const TIER_ORDER = ['tier1', 'tier2', 'tier3', 'tier4']

const RELATIONSHIP_NAMES: Record<string, string> = {
  advisor_student: '导师-学生',
  mentor_mentee: ' mentor-mentee',
  senior_junior: ' senior-junior',
}

const GenealogyGraph: React.FC<GenealogyGraphProps> = ({
  rootTalent,
  nodes,
  links,
  loading = false,
  onNodeClick,
}) => {
  const [relFilter, setRelFilter] = useState<string | null>(null)
  // Default matches backend default min_confidence=0.3
  const [minConf, setMinConf] = useState<number>(0.3)
  const [tierFilter, setTierFilter] = useState<string | null>(null)

  const allNodes = useMemo(() => [rootTalent, ...nodes], [rootTalent, nodes])

  const filteredLinks = useMemo(() => {
    return links.filter((link) => {
      if (link.confidence < minConf) return false
      if (relFilter && link.type !== relFilter) return false
      return true
    })
  }, [links, minConf, relFilter])

  // Use string IDs to avoid any type mismatch between number/string
  const visibleNodeIds = useMemo(() => {
    const ids = new Set<string>([String(rootTalent.talent_id)])
    filteredLinks.forEach((l) => {
      ids.add(String(l.source))
      ids.add(String(l.target))
    })
    return ids
  }, [filteredLinks, rootTalent.talent_id])

  const filteredNodes = useMemo(() => {
    return allNodes.filter((n) => {
      if (!visibleNodeIds.has(String(n.talent_id))) return false
      if (tierFilter && n.tier !== tierFilter) return false
      return true
    })
  }, [allNodes, visibleNodeIds, tierFilter])

  const option = useMemo(() => {
    if (filteredNodes.length === 0) return null

    // Group nodes by tier for top-down layered layout
    const tierGroups: Record<number, GenealogyNode[]> = {}
    filteredNodes.forEach((node) => {
      const idx = TIER_ORDER.indexOf(node.tier)
      const key = idx >= 0 ? idx : TIER_ORDER.length - 1
      if (!tierGroups[key]) tierGroups[key] = []
      tierGroups[key].push(node)
    })

    const CONTAINER_WIDTH = 900
    const MARGIN_X = 130
    const tierYPositions = [60, 180, 300, 420]

    const chartNodes = filteredNodes.map((node) => {
      const isRoot = node.is_root
      const size = isRoot ? 32 : Math.max(10, Math.min(28, 10 + node.composite_score * 0.2))
      const tierIdx = TIER_ORDER.indexOf(node.tier)
      const groupIdx = tierIdx >= 0 ? tierIdx : TIER_ORDER.length - 1
      const group = tierGroups[groupIdx] || []
      const indexInGroup = group.findIndex((n) => n.talent_id === node.talent_id)
      const groupSize = group.length
      const spacingX = groupSize > 1 ? (CONTAINER_WIDTH - 2 * MARGIN_X) / (groupSize - 1) : 0
      return {
        id: String(node.talent_id),
        name: isRoot ? `★ ${node.name}` : node.name,
        x: MARGIN_X + indexInGroup * spacingX,
        y: tierYPositions[groupIdx],
        symbolSize: size,
        category: groupIdx,
        itemStyle: {
          color: TIER_COLORS[node.tier] || '#91d5ff',
          ...(isRoot
            ? {
                borderColor: '#fff',
                borderWidth: 3,
                shadowBlur: 10,
                shadowColor: 'rgba(0,0,0,0.3)',
              }
            : {}),
        },
        label: {
          show: true,
          fontSize: isRoot ? 14 : 12,
          fontWeight: isRoot ? 'bold' : 'normal',
        },
        value: node.composite_score,
      }
    })

    const chartLinks = filteredLinks.map((link) => ({
      // Backend stores from=student, to=advisor. Swap for visual direction: advisor -> student
      source: String(link.target),
      target: String(link.source),
      value: link.confidence,
      lineStyle: {
        width: Math.max(1, link.confidence * 4),
        color: link.confidence >= 0.75 ? '#e94560' : link.confidence >= 0.5 ? '#ffa726' : '#999',
        type: link.confidence < 0.5 ? 'dashed' : 'solid',
        curveness: 0.2,
      },
      symbol: ['none', 'arrow'],
      symbolSize: [0, 10],
    }))

    const categories = TIER_ORDER.map((tier) => ({
      name: TIER_NAMES[tier],
      itemStyle: { color: TIER_COLORS[tier] },
    }))

    return {
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            const node = filteredNodes.find((n) => String(n.talent_id) === params.data.id)
            if (!node) return params.data.name
            return `${node.name}<br/>机构: ${node.institution || '-'}<br/>综合评分: ${node.composite_score.toFixed(1)}<br/>层级: ${TIER_NAMES[node.tier]}<br/>h-index: ${node.h_index}<br/>引用: ${node.cited_by_count}`
          }
          const link = filteredLinks[params.dataIndex]
          if (!link) return ''
          const advisorNode = filteredNodes.find((n) => n.talent_id === link.target)
          const studentNode = filteredNodes.find((n) => n.talent_id === link.source)
          return `${advisorNode?.name || link.target} → ${studentNode?.name || link.source}<br/>${RELATIONSHIP_NAMES[link.type] || link.type}<br/>置信度: ${(link.confidence * 100).toFixed(0)}%<br/>证据: ${link.evidence_count} 篇`
        },
      },
      legend: {
        orient: 'vertical',
        left: 10,
        top: 'middle',
        itemWidth: 12,
        itemHeight: 12,
        textStyle: { fontSize: 11 },
        data: categories.map((c) => c.name),
      },
      series: [
        {
          type: 'graph',
          layout: 'none',
          data: chartNodes,
          links: chartLinks,
          categories,
          roam: true,
          label: {
            show: true,
            position: 'right',
            formatter: '{b}',
          },
          labelLayout: {
            hideOverlap: true,
          },
          scaleLimit: {
            min: 0.4,
            max: 2,
          },
          lineStyle: {
            color: 'source',
            curveness: 0.3,
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: {
              width: 10,
            },
          },
        },
      ],
    }
  }, [filteredNodes, filteredLinks])

  if (loading) {
    return (
      <div style={{ height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (nodes.length === 0 && links.length === 0) {
    return (
      <div style={{ height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty
          description={
            <Space direction="vertical">
              <Text>暂无学术族谱数据</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                该学者未推断出族谱关系，或需要管理员重新触发族谱计算
              </Text>
            </Space>
          }
        />
      </div>
    )
  }

  const hasNoLinksAfterFilter = filteredLinks.length === 0

  return (
    <div>
      <Card size="small" style={{ marginBottom: 12 }}>
        <Row gutter={16} align="middle">
          <Col xs={24} sm={6}>
            <Text type="secondary">关系类型</Text>
            <Select
              allowClear
              placeholder="全部关系"
              style={{ width: '100%', marginTop: 4 }}
              value={relFilter}
              onChange={setRelFilter}
              options={[
                { label: '导师-学生', value: 'advisor_student' },
                { label: 'Mentor-Mentee', value: 'mentor_mentee' },
                { label: 'Senior-Junior', value: 'senior_junior' },
              ]}
            />
          </Col>
          <Col xs={24} sm={6}>
            <Text type="secondary">最低置信度: {(minConf * 100).toFixed(0)}%</Text>
            <Slider
              min={0.3}
              max={1.0}
              step={0.05}
              value={minConf}
              onChange={setMinConf}
              style={{ marginTop: 4 }}
            />
          </Col>
          <Col xs={24} sm={6}>
            <Text type="secondary">层级过滤</Text>
            <Select
              allowClear
              placeholder="全部层级"
              style={{ width: '100%', marginTop: 4 }}
              value={tierFilter}
              onChange={setTierFilter}
              options={[
                { label: <Badge color="#e94560" text="T1 学术领军" />, value: 'tier1' },
                { label: <Badge color="#ffa726" text="T2 中坚学者" />, value: 'tier2' },
                { label: <Badge color="#42a5f5" text="T3 青年才俊" />, value: 'tier3' },
                { label: <Badge color="#66bb6a" text="T4 新锐研究者" />, value: 'tier4' },
              ]}
            />
          </Col>
          <Col xs={24} sm={6}>
            <div style={{ textAlign: 'right', paddingTop: 20 }}>
              <Text type="secondary">
                显示 {filteredNodes.length} 个节点 / {filteredLinks.length} 条关系
              </Text>
              {links.length > 0 && filteredLinks.length < links.length && (
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    (原始共 {links.length} 条，当前过滤后 {filteredLinks.length} 条)
                  </Text>
                </div>
              )}
            </div>
          </Col>
        </Row>
        {hasNoLinksAfterFilter && (
          <Alert
            message={`当前学者「${rootTalent.name}」暂无通过置信度 ≥ ${(minConf * 100).toFixed(0)}% 的族谱关系。尝试降低最低置信度，或等待管理员重新触发族谱计算。`}
            type="info"
            showIcon
            style={{ marginTop: 12 }}
          />
        )}
      </Card>
      {option && (
        <div style={{ position: 'relative', height: 500 }}>
          {/* Tier background strips */}
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '25%', backgroundColor: 'rgba(233,69,96,0.04)', pointerEvents: 'none' }} />
          <div style={{ position: 'absolute', top: '25%', left: 0, right: 0, height: '25%', backgroundColor: 'rgba(255,167,38,0.04)', pointerEvents: 'none' }} />
          <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '25%', backgroundColor: 'rgba(66,165,245,0.04)', pointerEvents: 'none' }} />
          <div style={{ position: 'absolute', top: '75%', left: 0, right: 0, height: '25%', backgroundColor: 'rgba(102,187,106,0.04)', pointerEvents: 'none' }} />
          {/* Separator lines */}
          <div style={{ position: 'absolute', top: '25%', left: 0, right: 0, borderTop: '1px dashed #e8e8e8', pointerEvents: 'none' }} />
          <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, borderTop: '1px dashed #e8e8e8', pointerEvents: 'none' }} />
          <div style={{ position: 'absolute', top: '75%', left: 0, right: 0, borderTop: '1px dashed #e8e8e8', pointerEvents: 'none' }} />
          <ReactECharts
            option={option}
            notMerge={true}
            lazyUpdate={false}
            style={{ height: 500, width: '100%', position: 'relative', zIndex: 1 }}
            opts={{ renderer: 'canvas' }}
            onEvents={{
              click: (params: any) => {
                if (params?.dataType === 'node' && onNodeClick) {
                  onNodeClick(parseInt(params.data.id))
                }
              },
            }}
          />
        </div>
      )}
      {!option && (
        <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Empty description="过滤后没有可显示的节点" />
        </div>
      )}
    </div>
  )
}

export default GenealogyGraph
export type { GenealogyNode, GenealogyLink }
