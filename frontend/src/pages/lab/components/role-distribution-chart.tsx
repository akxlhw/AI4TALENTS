import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { useTranslation } from 'react-i18next'
import { ROLE_COLORS, useLabRoles } from '../constants/lab-role'
import '../../../i18n/namespaces/lab'

interface RoleDistributionChartProps {
  data: { name: string; value: number }[]
  onSliceClick?: (name: string) => void
}

const RoleDistributionChart: React.FC<RoleDistributionChartProps> = ({ data, onSliceClick }) => {
  const { t } = useTranslation('lab')
  const { roleLabel } = useLabRoles()
  const total = data.reduce((sum, item) => sum + item.value, 0)

  // Map raw role_type keys to localized labels + correct colors
  const chartData = data.map(item => ({
    name: roleLabel(item.name),
    value: item.value,
    itemStyle: { color: ROLE_COLORS[item.name] || '#CBD5E1' },
    // keep raw key for click callback
    _rawKey: item.name,
  }))

  const option: EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, left: 'center' },
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
        data: chartData,
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
        style: { text: t('overview.total'), align: 'center', fill: '#718096', fontSize: 12 },
      },
    ],
  }

  const onEvents = {
    click: (params: { name: string }) => {
      if (onSliceClick) {
        // Find the raw role_type key from chartData
        const matched = chartData.find(d => d.name === params.name)
        onSliceClick(matched?._rawKey || params.name)
      }
    },
  }

  return <ReactECharts option={option} style={{ height: 300 }} onEvents={onEvents} />
}

export default RoleDistributionChart
