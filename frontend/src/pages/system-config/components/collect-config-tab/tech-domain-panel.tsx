import { Card, Table, Typography, Tag, Space, Button, Tooltip, Empty, Spin, Badge } from 'antd'
import { SettingOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { getVenueTypeConfig } from '../../../../constants'
import type { TechDomainCollect } from '../../../../types'

const { Text } = Typography

interface TechDomainPanelProps {
  loading: boolean
  techDomains: TechDomainCollect[]
  onConfigVenues: (domain: TechDomainCollect) => void
  onOpenCollect: (domain: TechDomainCollect) => void
}

const TechDomainPanel: React.FC<TechDomainPanelProps> = ({
  loading,
  techDomains,
  onConfigVenues,
  onOpenCollect,
}) => {
  const elementColumns = [
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
        if (sources.length === 0) return <Text type="secondary">未配置</Text>
        const displayVenues = sources.slice(0, 10)
        return (
          <Space size={[4, 4]} wrap>
            {displayVenues.map((v) => (
              <Tooltip key={v.id} title={v.name || v.id}>
                <Tag color={getVenueTypeConfig(v.type).color}>{v.id.toUpperCase()}</Tag>
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
              onClick={() => onOpenCollect(record)}
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
    <Card>
      <Spin spinning={loading}>
        <Table
          dataSource={techDomains}
          columns={elementColumns}
          rowKey="tech_domain_id"
          pagination={false}
          locale={{ emptyText: <Empty description="暂无技术领域数据" /> }}
        />
      </Spin>
    </Card>
  )
}

export default TechDomainPanel
