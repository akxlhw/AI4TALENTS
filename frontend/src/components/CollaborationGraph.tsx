import { useMemo } from 'react'
import ReactECharts from 'echarts-for-react'
import { Empty, Spin, Typography, Space } from 'antd'

const { Text } = Typography

interface CollaborationNode {
  id: string
  name: string
  affiliation?: string
  collaborationCount: number
}

interface CollaborationLink {
  source: string
  target: string
  value: number
}

interface CollaborationGraphProps {
  nodes: CollaborationNode[]
  links: CollaborationLink[]
  loading?: boolean
  onNodeClick?: (nodeId: string) => void
}

const CollaborationGraph: React.FC<CollaborationGraphProps> = ({
  nodes,
  links,
  loading = false,
  onNodeClick,
}) => {
  const option = useMemo(() => {
    if (nodes.length === 0) return null

    // Build echarts graph data
    const chartNodes = nodes.map((node, index) => ({
      id: node.id,
      name: node.name,
      symbolSize: Math.min(50, 20 + node.collaborationCount * 5),
      category: index === 0 ? 0 : 1,
      itemStyle: {
        color: index === 0 ? '#1890ff' : '#91d5ff',
      },
      label: {
        show: true,
        fontSize: 12,
      },
    }))

    const chartLinks = links.map(link => ({
      source: link.source,
      target: link.target,
      value: link.value,
      lineStyle: {
        width: Math.min(10, link.value),
        color: '#aaa',
        curveness: 0.1,
      },
    }))

    return {
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            return `${params.data.name}<br/>合作次数: ${nodes.find(n => n.id === params.data.id)?.collaborationCount || 0}`
          }
          return `${params.data.source} - ${params.data.target}<br/>合作论文: ${params.data.value}`
        },
      },
      legend: {
        data: ['当前学者', '合作者'],
        bottom: 10,
      },
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: chartNodes,
          links: chartLinks,
          categories: [
            { name: '当前学者' },
            { name: '合作者' },
          ],
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
          force: {
            repulsion: 100,
            edgeLength: [50, 150],
            gravity: 0.1,
          },
        },
      ],
    }
  }, [nodes, links])

  if (loading) {
    return (
      <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (nodes.length === 0) {
    return (
      <div style={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty
          description={
            <Space direction="vertical">
              <Text>暂无合作网络数据</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                需要同步论文合作数据后才能展示
              </Text>
            </Space>
          }
        />
      </div>
    )
  }

  return (
    <ReactECharts
      option={option}
      style={{ height: 400, width: '100%' }}
      onEvents={{
        click: (params: any) => {
          if (params.dataType === 'node' && onNodeClick) {
            onNodeClick(params.data.id)
          }
        },
      }}
    />
  )
}

export default CollaborationGraph

// Re-export types
export type { CollaborationNode, CollaborationLink }
