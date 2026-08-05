import {
  Button,
  Card,
  Dropdown,
  Empty,
  Space,
  Spin,
  Table,
  Typography,
  type MenuProps,
  type TablePaginationConfig,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { DownOutlined, DownloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { semanticColors } from '../../../theme'
import type { FavoriteTalent } from '../../../types'

const { Text } = Typography

interface FavoritesTableCardProps {
  loading: boolean
  favorites: FavoriteTalent[]
  columns: ColumnsType<FavoriteTalent>
  page: number
  pageSize: number
  total: number
  selectedRowKeys: React.Key[]
  isAdmin: boolean
  exporting: boolean
  exportMenu: MenuProps
  onSelectionChange: (keys: React.Key[]) => void
  onTableChange: (pagination: TablePaginationConfig) => void
  onCompare: () => void
}

const FavoritesTableCard: React.FC<FavoritesTableCardProps> = ({
  loading,
  favorites,
  columns,
  page,
  pageSize,
  total,
  selectedRowKeys,
  isAdmin,
  exporting,
  exportMenu,
  onSelectionChange,
  onTableChange,
  onCompare,
}) => {
  const navigate = useNavigate()

  return (
    <Card styles={{ body: { padding: 0 } }}>
      {selectedRowKeys.length > 0 && (
        <div
          style={{
            padding: '12px 16px',
            background: semanticColors.bgGrayLight,
            borderBottom: `1px solid ${semanticColors.borderGrayLight}`,
          }}
        >
          <Space>
            <Text>
              已选择 <strong>{selectedRowKeys.length}</strong> 项
            </Text>
            <Button size="small" onClick={() => onSelectionChange([])}>
              取消选择
            </Button>
            <Button
              size="small"
              onClick={onCompare}
              disabled={selectedRowKeys.length < 2 || selectedRowKeys.length > 4}
            >
              对比 ({selectedRowKeys.length}/4)
            </Button>
            {isAdmin && (
              <Dropdown menu={exportMenu} trigger={['click']}>
                <Button type="primary" size="small" icon={<DownloadOutlined />} loading={exporting}>
                  导出 <DownOutlined />
                </Button>
              </Dropdown>
            )}
          </Space>
        </div>
      )}
      <Spin spinning={loading}>
        <Table
          dataSource={favorites}
          columns={columns}
          rowKey="favorite_id"
          rowSelection={{
            selectedRowKeys,
            onChange: onSelectionChange,
          }}
          scroll={{ x: 1000 }}
          pagination={{
            current: page,
            pageSize,
            total: total,
            showSizeChanger: false,
            showTotal: total => `共 ${total} 位收藏`,
          }}
          onChange={onTableChange}
          locale={{
            emptyText: (
              <Empty description="暂无收藏" image={Empty.PRESENTED_IMAGE_SIMPLE}>
                <Button type="primary" onClick={() => navigate('/search')}>
                  去搜索人才
                </Button>
              </Empty>
            ),
          }}
        />
      </Spin>
    </Card>
  )
}

export default FavoritesTableCard
