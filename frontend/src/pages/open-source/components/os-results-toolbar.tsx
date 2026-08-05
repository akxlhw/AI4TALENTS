import { Button, Checkbox, Dropdown, Space, Typography, type MenuProps } from 'antd'
import { DownOutlined, DownloadOutlined } from '@ant-design/icons'

const { Text } = Typography

interface OsResultsToolbarProps {
  total: number
  showControls: boolean
  isPageAllSelected: boolean
  selectedCount: number
  isAdmin: boolean
  exporting: boolean
  exportMenu: MenuProps
  onSelectPage: () => void
  onSelectAll: () => void
  onClearSelection: () => void
}

const OsResultsToolbar: React.FC<OsResultsToolbarProps> = ({
  total,
  showControls,
  isPageAllSelected,
  selectedCount,
  isAdmin,
  exporting,
  exportMenu,
  onSelectPage,
  onSelectAll,
  onClearSelection,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
        marginBottom: 16,
      }}
    >
      <Text style={{ color: 'var(--text-secondary)' }}>共 {total} 条结果</Text>
      {showControls && (
        <Space wrap>
          <Checkbox checked={isPageAllSelected} onChange={onSelectPage}>
            全选当前页
          </Checkbox>
          <Button size="small" onClick={onSelectAll}>
            全选所有结果
          </Button>
          <Text>
            已选择 <strong>{selectedCount}</strong> 位开发者
          </Text>
          {selectedCount > 0 && (
            <Button size="small" onClick={onClearSelection}>
              取消选择
            </Button>
          )}
          {isAdmin && (
            <Dropdown menu={exportMenu} trigger={['click']}>
              <Button type="primary" size="small" icon={<DownloadOutlined />} loading={exporting}>
                导出 <DownOutlined />
              </Button>
            </Dropdown>
          )}
        </Space>
      )}
    </div>
  )
}

export default OsResultsToolbar
