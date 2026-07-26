import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { ROLE_COLORS } from '../constants/lab-role'

interface AdvisorNetworkChartProps {
  data: {
    nodes: { name: string; talent_id: number | null; role_type: string; is_student: boolean }[]
    edges: { source: string; target: string; type: string }[]
  }
  onNodeClick?: (name: string, talentId: number | null) => void
}

const AdvisorNetworkChart: React.FC<AdvisorNetworkChartProps> = ({ data, onNodeClick }) => {
  const chartNodes = data.nodes.map(n => ({
    id: n.name,
    name: n.name,
    symbolSize: n.is_student ? 20 : 35,
    category: n.is_student ? 0 : 1,
    itemStyle: {
      color: ROLE_COLORS[n.role_type] || ROLE_COLORS.unknown,
      borderColor: '#fff',
      borderWidth: 2,
    },
    label: { show: !n.is_student || data.nodes.length <= 30 },
  }))

  const chartLinks = data.edges.map(e => ({
    source: e.source,
    target: e.target,
    lineStyle: {
      width: e.type === 'co_advisor' ? 1 : 2,
      color: e.type === 'co_advisor' ? '#94A3B8' : '#0EA5E9',
      curveness: 0.2,
      type: (e.type === 'co_advisor' ? 'dashed' : 'solid') as 'dashed' | 'solid',
    },
  }))

  const option: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: object) => {
        const p = params as { dataType?: string; data?: { name?: string } }
        if (p.dataType === 'node' && p.data?.name) {
          return p.data.name
        }
        return ''
      },
    },
    legend: {
      data: ['学生', '导师'],
      bottom: 0,
      left: 'center',
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        label: {
          show: true,
          position: 'right',
          fontSize: 11,
          color: '#333',
        },
        force: {
          repulsion: 120,
          edgeLength: [60, 120],
          gravity: 0.08,
        },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 4 },
        },
        categories: [
          { name: '学生', itemStyle: { color: '#0EA5E9' } },
          { name: '导师', itemStyle: { color: '#0D2B4E' } },
        ],
        data: chartNodes,
        links: chartLinks,
      },
    ],
  }

  return (
    <ReactECharts
      option={option}
      style={{ height: 500 }}
      onEvents={{
        click: (params: object) => {
          const p = params as { dataType?: string; data?: { name?: string; talent_id?: number | null } }
          if (p.dataType === 'node' && onNodeClick && p.data?.name) {
            onNodeClick(p.data.name, p.data.talent_id ?? null)
          }
        },
      }}
    />
  )
}

export default AdvisorNetworkChart
