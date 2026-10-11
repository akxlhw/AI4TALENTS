import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { useTranslation } from 'react-i18next'
import { buildTree } from './advisor-tree-builder'
import type { NetworkNode, NetworkEdge, TreeNode, TreeLabels } from './advisor-tree-builder'
import '../../../i18n/namespaces/lab'

interface AdvisorNetworkChartProps {
  data: { nodes: NetworkNode[]; edges: NetworkEdge[] }
  labName?: string
  onNodeClick?: (name: string, talentId: number | null) => void
}

const AdvisorNetworkChart: React.FC<AdvisorNetworkChartProps> = ({
  data,
  labName,
  onNodeClick,
}) => {
  const { t } = useTranslation('lab')
  const resolvedLabName = labName ?? t('tree.defaultLab')

  const labels = useMemo<TreeLabels>(
    () => ({
      founderTitle: name => `👑 ${t('tree.founder')} · ${name}`,
      coAdvisedBy: names => t('tree.coAdvised', { names: names.join(t('tree.nameJoiner')) }),
      studentsAggregate: n => t('tree.studentsAggregate', { n }),
      founderStudentsGroup: t('tree.founderStudentsGroup'),
      otherAdvisors: t('tree.otherAdvisors'),
      orgGroup: t('tree.orgGroup'),
    }),
    [t]
  )

  const { root } = useMemo(
    () => buildTree(data.nodes, data.edges, resolvedLabName, labels),
    [data, resolvedLabName, labels]
  )

  // Canvas size follows the INITIALLY VISIBLE tree shape (a collapsed node
  // counts as one leaf and one level), so sibling spacing stays compact and
  // constant in px no matter how big the full tree is — roam handles overflow.
  const { visibleLeafCount, visibleLevels } = useMemo(() => {
    const leaves = (n: TreeNode): number =>
      n.collapsed || !n.children?.length ? 1 : n.children.reduce((sum, c) => sum + leaves(c), 0)
    const levels = (n: TreeNode): number =>
      n.collapsed || !n.children?.length ? 1 : 1 + Math.max(...n.children.map(levels))
    return { visibleLeafCount: leaves(root), visibleLevels: levels(root) }
  }, [root])

  const canvasWidth = Math.max(640, visibleLeafCount * 48)
  const canvasHeight = Math.max(240, visibleLevels * 160)

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
        // -1 = no depth-based default; per-node `collapsed` flags decide
        initialTreeDepth: -1,
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
      <div style={{ fontSize: 12, color: '#64748B', marginBottom: 4 }}>{t('tree.legend')}</div>
      <ReactECharts
        option={option}
        notMerge
        style={{ height: 560 }}
        onEvents={{
          click: (params: { data?: TreeNode; event?: { event?: { shiftKey?: boolean } } }) => {
            const d = params.data
            if (!d || !onNodeClick) return
            // Shift+click opens the detail page for ANY node with a talent
            // record — plain click stays reserved for expand/collapse, so the
            // two gestures never fight over the same node.
            if (d.talent_id && (params.event?.event?.shiftKey || !d.has_children)) {
              onNodeClick(d.name, d.talent_id)
            }
          },
        }}
      />
    </div>
  )
}

export default AdvisorNetworkChart
