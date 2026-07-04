import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

interface RoleDistributionChartProps {
  data: { name: string; value: number }[]
  onSliceClick?: (name: string) => void
}

const ROLE_COLORS = ['#0D2B4E', '#0EA5E9', '#60A5FA', '#93C5FD']

const RoleDistributionChart: React.FC<RoleDistributionChartProps> = ({ data, onSliceClick }) => {
  const total = data.reduce((sum, item) => sum + item.value, 0)

  const option: EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, left: 'center' },
    color: ROLE_COLORS,
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: false, position: 'center' },
        emphasis: {
          label: { show: true, fontSize: 18, fontWeight: 'bold', formatter: `{b}\n{c}` },
        },
        labelLine: { show: false },
        data,
      },
    ],
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '42%',
        style: {
          text: `${total}`,
          align: 'center',
          fill: '#1a202c',
          fontSize: 24,
          fontWeight: 'bold',
        },
      },
      {
        type: 'text',
        left: 'center',
        top: '50%',
        style: { text: '总计', align: 'center', fill: '#718096', fontSize: 12 },
      },
    ],
  }

  const onEvents = {
    click: (params: any) => {
      if (onSliceClick) onSliceClick(params.name)
    },
  }

  return <ReactECharts option={option} style={{ height: 300 }} onEvents={onEvents} />
}

export default RoleDistributionChart
