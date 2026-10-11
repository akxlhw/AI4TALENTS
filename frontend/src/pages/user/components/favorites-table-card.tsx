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
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation('user')

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
              {t('table.selectedBefore')}
              <strong>{selectedRowKeys.length}</strong>
              {t('table.selectedAfter')}
            </Text>
            <Button size="small" onClick={() => onSelectionChange([])}>
              {t('table.clearSelection')}
            </Button>
            <Button
              size="small"
              onClick={onCompare}
              disabled={selectedRowKeys.length < 2 || selectedRowKeys.length > 4}
            >
              {t('table.compare', { count: selectedRowKeys.length })}
            </Button>
            {isAdmin && (
              <Dropdown menu={exportMenu} trigger={['click']}>
                <Button type="primary" size="small" icon={<DownloadOutlined />} loading={exporting}>
                  {t('table.export')} <DownOutlined />
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
            showTotal: count => t('table.total', { count }),
          }}
          onChange={onTableChange}
          locale={{
            emptyText: (
              <Empty description={t('table.empty')} image={Empty.PRESENTED_IMAGE_SIMPLE}>
                <Button type="primary" onClick={() => navigate('/search')}>
                  {t('table.goSearch')}
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
