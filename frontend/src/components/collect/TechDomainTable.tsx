/**
 * TechDomainTable - 技术领域配置表格组件
 *
 * 职责：
 * - 显示技术领域列表
 * - 显示关联的顶会顶刊
 * - 提供配置和采集操作按钮
 */
import { Table, Typography, Tag, Space, Button, Tooltip, Badge, Empty } from 'antd'
import { SettingOutlined, PlayCircleOutlined } from '@ant-design/icons'
import type { TechDomainCollect, VenueTypeConfig } from '../../types'

const { Text } = Typography

export interface TechDomainTableProps {
  data: TechDomainCollect[]
  loading: boolean
  venueTypeMap: Record<string, VenueTypeConfig>
  onConfigVenues: (domain: TechDomainCollect) => void
  onStartCollect: (domain: TechDomainCollect) => void
}

const TechDomainTable: React.FC<TechDomainTableProps> = ({
  data,
  loading,
  venueTypeMap,
  onConfigVenues,
  onStartCollect,
}) => {
  const columns = [
    {
      title: '技术领域',
      dataIndex: 'domain_name',
      key: 'domain_name',
      width: 120,
      render: (name: string) => <Text strong>{name}</Text>,
    },
    {
      title: '关联顶会顶刊',
      key: 'venues',
      render: (_: unknown, record: TechDomainCollect) => {
        const sources = record.collect_sources || []
        if (sources.length === 0) {
          return <Text type="secondary">未配置</Text>
        }
        const displayVenues = sources.slice(0, 10)
        return (
          <Space size={[4, 4]} wrap>
            {displayVenues.map((v) => (
              <Tooltip key={v.id} title={v.name || v.id}>
                <Tag color={venueTypeMap[v.type]?.color || 'default'}>
                  {v.id.toUpperCase()}
                </Tag>
              </Tooltip>
            ))}
            {sources.length > 10 && <Tag>+{sources.length - 10}</Tag>}
          </Space>
        )
      },
    },
    {
      title: '顶会顶刊数',
      dataIndex: 'venue_count',
      key: 'venue_count',
      width: 100,
      render: (count: number) => (
        <Badge count={count} showZero color="blue" style={{ marginRight: 8 }} />
      ),
    },
    {
      title: '最后采集',
      dataIndex: 'last_collect_at',
      key: 'last_collect_at',
      width: 120,
      render: (date: string | null) => date ? new Date(date).toLocaleDateString() : <Text type="secondary">-</Text>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      render: (_: unknown, record: TechDomainCollect) => (
        <Space>
          <Tooltip title="配置顶会顶刊">
            <Button
              type="link"
              size="small"
              icon={<SettingOutlined />}
              onClick={() => onConfigVenues(record)}
            >
              配置
            </Button>
          </Tooltip>
          <Tooltip title="启动采集">
            <Button
              type="primary"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => onStartCollect(record)}
              disabled={!record.collect_sources || record.collect_sources.length === 0}
            >
              采集
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <Table
      dataSource={data}
      columns={columns}
      rowKey="tech_domain_id"
      pagination={false}
      loading={loading}
      locale={{
        emptyText: <Empty description="暂无技术领域数据" />,
      }}
    />
  )
}

export default TechDomainTable
