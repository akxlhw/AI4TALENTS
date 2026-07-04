import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

interface LabDistributionChartProps {
  data: { name: string; value: number }[]
  onBarClick?: (name: string) => void
}

const LabDistributionChart: React.FC<LabDistributionChartProps> = ({ data, onBarClick }) => {
  const option: EChartsOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: data.map((d) => d.name), inverse: true },
    series: [
      {
        type: 'bar',
        data: data.map((d) => d.value),
        itemStyle: {
          color: 'var(--domain-secondary)',
          borderRadius: [0, 4, 4, 0],
        },
        barWidth: '60%',
      },
    ],
  }

  const onEvents = {
    click: (params: any) => {
      if (onBarClick) onBarClick(params.name)
    },
  }

  return <ReactECharts option={option} style={{ height: Math.max(200, data.length * 40 + 80) }} onEvents={onEvents} />
}

export default LabDistributionChart
