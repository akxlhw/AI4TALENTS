import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { buildTree } from './advisor-tree-builder'
import type { NetworkNode, NetworkEdge, TreeNode } from './advisor-tree-builder'

interface AdvisorNetworkChartProps {
  data: { nodes: NetworkNode[]; edges: NetworkEdge[] }
  labName?: string
  onNodeClick?: (name: string, talentId: number | null) => void
}

const AdvisorNetworkChart: React.FC<AdvisorNetworkChartProps> = ({
  data,
  labName = '实验室',
  onNodeClick,
}) => {
  const { root, totalNodes, leafCount, depth } = useMemo(
    () => buildTree(data.nodes, data.edges, labName),
    [data, labName],
  )

  // Large labs: collapse student level by default, click to expand
  const initialDepth = totalNodes > 60 ? 1 : 3

  // Fixed-px canvas sized by tree shape, so sibling/level spacing stays
  // compact and constant (~88px per leaf column, ~150px per level) no
  // matter how big the tree gets — roam lets the user pan/zoom the overflow.
  const canvasWidth = Math.max(640, leafCount * 88)
  const canvasHeight = Math.max(320, depth * 150)

  const option: EChartsOption = {
    tooltip: { trigger: 'item', triggerOn: 'mousemove' },
    series: [
      {
        type: 'tree',
        data: [root],
        left: 'center',
        top: 24,
        width: canvasWidth,
        height: canvasHeight,
        orient: 'TB',
        symbol: 'circle',
        symbolSize: 28,
        roam: true,
        initialTreeDepth: initialDepth,
        expandAndCollapse: true,
        label: { show: true, position: 'bottom', fontSize: 11, color: '#333' },
        leaves: { label: { show: true, position: 'bottom', fontSize: 11 } },
        lineStyle: { color: '#CBD5E1', width: 1.2, curveness: 0.5 },
        emphasis: { focus: 'descendant' },
        animationDuration: 300,
        animationDurationUpdate: 300,
      },
    ],
  }

  return (
    <div>
      <div style={{ fontSize: 12, color: '#64748B', marginBottom: 4 }}>
        金边 👑 = 创始人 · 深色 = 导师 · 浅色 = 学生 · 灰色分组 = 组织归类（非师承） ·
        点击节点展开/收起，点击学生查看详情 · 滚轮缩放，拖拽平移
      </div>
      <ReactECharts
        option={option}
        notMerge
        style={{ height: 560 }}
        onEvents={{
          click: (params: { data?: TreeNode }) => {
            const d = params.data
            // Leaf node with a talent record → navigate; parents expand natively
            if (d && !d.has_children && d.talent_id && onNodeClick) {
              onNodeClick(d.name, d.talent_id)
            }
          },
        }}
      />
    </div>
  )
}

export default AdvisorNetworkChart
