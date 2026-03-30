/**
 * FilterSection Component
 *
 * A reusable filter section with consistent layout for filter controls.
 * Used in search, favorites, and other list pages.
 */

import React from 'react'
import { Card, Row, Col, Space, Typography, Button } from 'antd'
import { ClearOutlined } from '@ant-design/icons'

const { Text } = Typography

export interface FilterSectionProps {
  /** Filter controls */
  children: React.ReactNode
  /** Show reset button */
  showReset?: boolean
  /** Reset button callback */
  onReset?: () => void
  /** Reset button text */
  resetText?: string
  /** Additional actions on the right side */
  actions?: React.ReactNode
  /** Whether the filter section has active filters */
  hasActiveFilters?: boolean
  /** Custom padding style */
  padding?: string | number
}

const FilterSection: React.FC<FilterSectionProps> = ({
  children,
  showReset = true,
  onReset,
  resetText = '重置筛选',
  actions,
  hasActiveFilters = false,
  padding = '12px 24px',
}) => {
  return (
    <Card style={{ marginBottom: 16 }} bodyStyle={{ padding }}>
      <Row gutter={16} align="middle">
        <Col flex="auto">
          <Space size={8} wrap>
            <Text type="secondary">筛选:</Text>
            {children}
            {showReset && hasActiveFilters && (
              <Button
                type="link"
                icon={<ClearOutlined />}
                onClick={onReset}
              >
                {resetText}
              </Button>
            )}
          </Space>
        </Col>
        {actions && (
          <Col>
            {actions}
          </Col>
        )}
      </Row>
    </Card>
  )
}

export default FilterSection
