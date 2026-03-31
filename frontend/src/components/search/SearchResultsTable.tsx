/**
 * SearchResultsTable - 搜索结果表格组件
 *
 * 职责：
 * - 渲染人才列表表格
 * - 处理行选择
 * - 支持列配置
 */
import { Table, Space, Tag, Typography, Empty, Dropdown, Menu, Button, Spin } from 'antd'
import { DownloadOutlined, DownOutlined } from '@ant-design/icons'
import type { SearchTalent } from '../../types'
import FavoriteButton from '../FavoriteButton'
import { getRoleTypeConfig } from '../../constants/roleType'

const { Text } = Typography

export interface ColumnConfig {
  key: string
  visible: boolean
  label: string
}

export interface SearchResultsTableProps {
  results: SearchTalent[]
  loading: boolean
  total: number
  page: number
  pageSize: number
  selectedKeys: React.Key[]
  visibleColumns: string[]
  onSelectChange: (keys: React.Key[]) => void
  onRowClick: (talentId: number) => void
  onSchoolClick: (schoolId: number) => void
  onPageChange: (page: number) => void
  onExport: (format: 'csv' | 'xlsx') => void
  onCompare: () => void
  exporting: boolean
  searchQuery: string
}

const SearchResultsTable: React.FC<SearchResultsTableProps> = ({
  results,
  loading,
  total,
  page,
  pageSize,
  selectedKeys,
  visibleColumns,
  onSelectChange,
  onRowClick,
  onSchoolClick,
  onPageChange,
  onExport,
  onCompare,
  exporting,
  searchQuery,
}) => {
  const allColumns = [
    {
      title: '收藏',
      key: 'favorite',
      width: 60,
      align: 'center' as const,
      render: (_: unknown, record: SearchTalent) => (
        <FavoriteButton talentId={record.talent_id} size="small" />
      ),
    },
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (name: string, record: SearchTalent) => (
        <a onClick={() => onRowClick(record.talent_id)} style={{ fontWeight: 500 }}>
          <Space direction="vertical" size={0}>
            <span>{name}</span>
            {record.name_en && (
              <span style={{ fontSize: 12, color: '#999' }}>{record.name_en}</span>
            )}
          </Space>
        </a>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role_type',
      key: 'role_type',
      width: 100,
      render: (role: string) => {
        const config = getRoleTypeConfig(role)
        return <Tag color={config.color}>{config.text}</Tag>
      },
    },
    {
      title: '学校',
      dataIndex: 'school_name',
      key: 'school_name',
      width: 150,
      ellipsis: true,
      render: (name: string, record: SearchTalent) =>
        name ? (
          <a onClick={() => record.school_id && onSchoolClick(record.school_id)}>{name}</a>
        ) : (
          <Text type="secondary">-</Text>
        ),
    },
    {
      title: '论文',
      dataIndex: 'works_count',
      key: 'works_count',
      width: 80,
      align: 'center' as const,
      sorter: true,
    },
    {
      title: '引用',
      dataIndex: 'cited_by_count',
      key: 'cited_by_count',
      width: 100,
      align: 'right' as const,
      render: (count: number) => count.toLocaleString(),
      sorter: true,
    },
    {
      title: 'H指数',
      dataIndex: 'h_index',
      key: 'h_index',
      width: 80,
      align: 'center' as const,
      sorter: true,
    },
    {
      title: '研究方向',
      dataIndex: 'topic_tags',
      key: 'topic_tags',
      width: 200,
      render: (tags: string[]) => (
        <Space size={4} wrap>
          {(tags || []).slice(0, 3).map(tag => (
            <Tag key={tag} style={{ margin: 0, fontSize: 11 }}>
              {tag}
            </Tag>
          ))}
          {tags && tags.length > 3 && (
            <span style={{ fontSize: 11, color: '#999' }}>+{tags.length - 3}</span>
          )}
        </Space>
      ),
    },
  ]

  // Filter columns based on user settings
  const columns = allColumns.filter(col => visibleColumns.includes(col.key as string))

  const exportMenu = (
    <Menu
      items={[
        { key: 'csv', label: '导出 CSV' },
        { key: 'xlsx', label: '导出 Excel' },
      ]}
      onClick={(e) => onExport(e.key as 'csv' | 'xlsx')}
    />
  )

  return (
    <div style={{ padding: 0 }}>
      {selectedKeys.length > 0 && (
        <div style={{ padding: '12px 16px', background: '#fafafa', borderBottom: '1px solid #f0f0f0' }}>
          <Space>
            <Text>已选择 <strong>{selectedKeys.length}</strong> 项</Text>
            <Button size="small" onClick={() => onSelectChange([])}>取消选择</Button>
            <Button
              size="small"
              onClick={onCompare}
              disabled={selectedKeys.length < 2 || selectedKeys.length > 4}
            >
              对比 ({selectedKeys.length}/4)
            </Button>
            <Dropdown overlay={exportMenu} trigger={['click']}>
              <Button type="primary" size="small" icon={<DownloadOutlined />} loading={exporting}>
                导出 <DownOutlined />
              </Button>
            </Dropdown>
          </Space>
        </div>
      )}
      <Spin spinning={loading}>
        <Table
          dataSource={results}
          columns={columns}
          rowKey="talent_id"
          rowSelection={{
            selectedRowKeys: selectedKeys,
            onChange: onSelectChange,
          }}
          pagination={{
            current: page,
            pageSize,
            total: total,
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 条结果`,
            pageSizeOptions: ['20', '50', '100'],
          }}
          onChange={(pagination) => onPageChange(pagination.current || 1)}
          locale={{
            emptyText: (
              <Empty
                description={
                  searchQuery
                    ? `未找到与"${searchQuery}"相关的人才`
                    : '暂无人才数据'
                }
              />
            ),
          }}
        />
      </Spin>
    </div>
  )
}

export default SearchResultsTable
