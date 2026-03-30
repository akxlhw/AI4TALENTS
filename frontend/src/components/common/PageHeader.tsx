/**
 * PageHeader Component
 *
 * A reusable page header with icon, title, and optional action buttons.
 * Used across all main pages for consistent styling.
 */

import React from 'react'
import { Typography, Space, Button } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'

const { Title } = Typography

export interface PageHeaderAction {
  key: string
  label: string
  icon?: React.ReactNode
  onClick?: () => void
  loading?: boolean
  type?: 'primary' | 'default' | 'dashed' | 'text' | 'link'
  danger?: boolean
}

export interface PageHeaderProps {
  /** Page title */
  title: string
  /** Optional icon before the title */
  icon?: React.ReactNode
  /** Optional subtitle or description */
  subtitle?: string
  /** Action buttons to display on the right side */
  actions?: PageHeaderAction[]
  /** Show refresh button */
  showRefresh?: boolean
  /** Refresh button callback */
  onRefresh?: () => void
  /** Refresh button loading state */
  refreshing?: boolean
  /** Level of the title (1-5) */
  level?: 1 | 2 | 3 | 4 | 5
  /** Extra content on the right */
  extra?: React.ReactNode
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  icon,
  subtitle,
  actions = [],
  showRefresh = false,
  onRefresh,
  refreshing = false,
  level = 3,
  extra,
}) => {
  return (
    <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <div>
        <Title level={level} style={{ margin: 0 }}>
          {icon && <span style={{ marginRight: 8 }}>{icon}</span>}
          {title}
        </Title>
        {subtitle && (
          <div style={{ color: '#666', marginTop: 4 }}>{subtitle}</div>
        )}
      </div>
      <Space>
        {actions.map((action) => (
          <Button
            key={action.key}
            type={action.type || 'default'}
            icon={action.icon}
            onClick={action.onClick}
            loading={action.loading}
            danger={action.danger}
          >
            {action.label}
          </Button>
        ))}
        {showRefresh && (
          <Button
            icon={<ReloadOutlined />}
            onClick={onRefresh}
            loading={refreshing}
          >
            刷新
          </Button>
        )}
        {extra}
      </Space>
    </div>
  )
}

export default PageHeader
