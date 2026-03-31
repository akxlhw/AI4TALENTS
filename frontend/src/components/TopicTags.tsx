/**
 * 研究方向标签缩略显示组件
 * 支持两种显示模式：
 * 1. compact: 显示前N个标签，超出部分用 +N 表示
 * 2. tooltip: 鼠标悬停显示完整列表
 */
import React from 'react'
import { Tag, Tooltip, Space } from 'antd'

interface TopicTagsProps {
  tags: string[]
  maxVisible?: number  // 最多显示几个标签，默认2
  mode?: 'compact' | 'tooltip'  // 显示模式，默认tooltip
  size?: 'small' | 'default'  // 标签大小
}

const TopicTags: React.FC<TopicTagsProps> = ({
  tags,
  maxVisible = 2,
  mode = 'tooltip',
  size = 'small',
}) => {
  if (!tags || tags.length === 0) {
    return <span style={{ color: '#999' }}>-</span>
  }

  const visibleTags = tags.slice(0, maxVisible)
  const hiddenCount = tags.length - maxVisible

  const tagStyle = {
    margin: 0,
    fontSize: size === 'small' ? 11 : 12,
    maxWidth: 150,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
  }

  // tooltip 模式：显示部分 + 悬停显示全部
  if (mode === 'tooltip' && hiddenCount > 0) {
    const tooltipContent = (
      <div style={{ maxWidth: 300 }}>
        {tags.map((tag, index) => (
          <Tag key={index} style={{ margin: '2px 4px', fontSize: 12 }}>
            {tag}
          </Tag>
        ))}
      </div>
    )

    return (
      <Tooltip title={tooltipContent} placement="topLeft">
        <Space size={4} wrap={false} style={{ cursor: 'pointer' }}>
          {visibleTags.map((tag, index) => (
            <Tag key={index} style={tagStyle}>{tag}</Tag>
          ))}
          <Tag style={{ ...tagStyle, background: '#f5f5f5', border: '1px dashed #d9d9d9' }}>
            +{hiddenCount}
          </Tag>
        </Space>
      </Tooltip>
    )
  }

  // compact 模式：仅显示部分 + 数量提示
  return (
    <Space size={4} wrap>
      {visibleTags.map((tag, index) => (
        <Tag key={index} style={tagStyle}>{tag}</Tag>
      ))}
      {hiddenCount > 0 && (
        <span style={{ fontSize: 11, color: '#999' }}>+{hiddenCount}</span>
      )}
    </Space>
  )
}

export default TopicTags
