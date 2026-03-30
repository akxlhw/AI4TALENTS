/**
 * SelectionActions Component
 *
 * A unified action bar for table row selection.
 * Shows selection count and provides batch action buttons.
 */

import React from 'react'
import { Space, Typography, Button, Dropdown, Menu } from 'antd'
import { DownloadOutlined, DownOutlined } from '@ant-design/icons'

const { Text } = Typography

export interface SelectionAction {
  key: string
  label: string
  icon?: React.ReactNode
  onClick: () => void
  loading?: boolean
  disabled?: boolean
  danger?: boolean
}

export interface SelectionActionsProps {
  /** Number of selected items */
  selectedCount: number
  /** Clear selection callback */
  onClear: () => void
  /** Available actions */
  actions?: SelectionAction[]
  /** Dropdown menu items for export */
  exportMenuItems?: Array<{ key: string; label: string }>
  /** Export menu click handler */
  onExport?: (key: string) => void
  /** Export button loading state */
  exporting?: boolean
  /** Maximum selection limit */
  maxSelection?: number
  /** Custom text for selection count */
  selectionText?: string
}

const SelectionActions: React.FC<SelectionActionsProps> = ({
  selectedCount,
  onClear,
  actions = [],
  exportMenuItems,
  onExport,
  exporting = false,
  maxSelection,
  selectionText = '项',
}) => {
  if (selectedCount === 0) {
    return null
  }

  const exportMenu = exportMenuItems ? (
    <Menu
      items={exportMenuItems.map(item => ({ key: item.key, label: item.label }))}
      onClick={(e) => onExport?.(e.key)}
    />
  ) : null

  return (
    <div style={{
      padding: '12px 16px',
      background: '#fafafa',
      borderBottom: '1px solid #f0f0f0',
    }}>
      <Space>
        <Text>
          已选择 <strong>{selectedCount}</strong> {selectionText}
          {maxSelection && ` (最多 ${maxSelection})`}
        </Text>
        <Button size="small" onClick={onClear}>
          取消选择
        </Button>
        {actions.map((action) => (
          <Button
            key={action.key}
            size="small"
            type="primary"
            icon={action.icon}
            onClick={action.onClick}
            loading={action.loading}
            disabled={action.disabled}
            danger={action.danger}
          >
            {action.label}
          </Button>
        ))}
        {exportMenu && (
          <Dropdown overlay={exportMenu} trigger={['click']}>
            <Button
              type="primary"
              size="small"
              icon={<DownloadOutlined />}
              loading={exporting}
            >
              导出 <DownOutlined />
            </Button>
          </Dropdown>
        )}
      </Space>
    </div>
  )
}

export default SelectionActions
