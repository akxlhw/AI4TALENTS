/**
 * TechElementTable - 技术要素配置表格组件
 *
 * 职责：
 * - 显示技术要素列表
 * - 显示关联的顶会顶刊
 * - 提供配置和采集操作按钮
 */
import { Table, Typography, Tag, Space, Button, Tooltip, Badge, Empty } from 'antd'
import { SettingOutlined, PlayCircleOutlined } from '@ant-design/icons'
import type { TechElementCollect, VenueTypeConfig } from '../../types'

const { Text } = Typography

export interface TechElementTableProps {
  data: TechElementCollect[]
  loading: boolean
  venueTypeMap: Record<string, VenueTypeConfig>
  onConfigVenues: (element: TechElementCollect) => void
  onStartCollect: (element: TechElementCollect) => void
}

const TechElementTable: React.FC<TechElementTableProps> = ({
  data,
  loading,
  venueTypeMap,
  onConfigVenues,
  onStartCollect,
}) => {
  const columns = [
    {
      title: '技术要素',
      dataIndex: 'element_name',
      key: 'element_name',
      render: (name: string, record: TechElementCollect) => (
        <Space>
          <Text strong>{name}</Text>
          {record.element_name_en && <Text type="secondary">({record.element_name_en})</Text>}
        </Space>
      ),
    },
    {
      title: '关联顶会顶刊',
      key: 'venues',
      render: (_: unknown, record: TechElementCollect) => {
        const sources = record.collect_sources || []
        if (sources.length === 0) {
          return <Text type="secondary">未配置</Text>
        }
        const displayVenues = sources.slice(0, 3)
        return (
          <Space size={[4, 4]} wrap>
            {displayVenues.map((v) => (
              <Tooltip key={v.id} title={v.id}>
                <Tag color={venueTypeMap[v.type]?.color || 'default'}>
                  {v.name || v.id}
                </Tag>
              </Tooltip>
            ))}
            {sources.length > 3 && <Tag>+{sources.length - 3}</Tag>}
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
      render: (_: unknown, record: TechElementCollect) => (
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
      rowKey="tech_element_id"
      pagination={false}
      loading={loading}
      locale={{
        emptyText: <Empty description="暂无技术要素数据" />,
      }}
    />
  )
}

export default TechElementTable
