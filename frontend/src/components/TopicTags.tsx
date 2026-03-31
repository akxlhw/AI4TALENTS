/**
 * 研究方向标签缩略显示组件
 *
 * 特性：
 * 1. 限制标签宽度，防止超出单元格
 * 2. Tooltip 悬浮显示完整列表（白色背景）
 * 3. 标签过长时自动省略
 */
import React from 'react'
import { Tag, Tooltip } from 'antd'

interface TopicTagsProps {
  tags: string[]
  maxVisible?: number  // 最多显示几个标签，默认2
  maxTagWidth?: number // 单个标签最大宽度，默认80px
}

const TopicTags: React.FC<TopicTagsProps> = ({
  tags,
  maxVisible = 2,
  maxTagWidth = 80,
}) => {
  if (!tags || tags.length === 0) {
    return <span style={{ color: '#999' }}>-</span>
  }

  const visibleTags = tags.slice(0, maxVisible)
  const hiddenCount = tags.length - maxVisible

  // 标签样式：限制宽度 + 省略
  const tagStyle: React.CSSProperties = {
    margin: 0,
    fontSize: 11,
    maxWidth: maxTagWidth,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    display: 'inline-block',
    verticalAlign: 'middle',
  }

  // 容器样式：flex 布局防止溢出
  const containerStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    maxWidth: '100%',
    overflow: 'hidden',
  }

  // 有隐藏标签时，显示 Tooltip
  if (hiddenCount > 0) {
    const tooltipContent = (
      <div style={{
        maxWidth: 320,
        display: 'flex',
        flexWrap: 'wrap',
        gap: 4,
      }}>
        {tags.map((tag, index) => (
          <Tag
            key={index}
            style={{
              margin: 0,
              fontSize: 12,
              maxWidth: 150,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {tag}
          </Tag>
        ))}
      </div>
    )

    return (
      <Tooltip
        title={tooltipContent}
        placement="topLeft"
        overlayStyle={{ maxWidth: 360 }}
        overlayInnerStyle={{
          background: '#fff',
          color: '#333',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          padding: 8,
        }}
      >
        <div style={{ ...containerStyle, cursor: 'pointer' }}>
          {visibleTags.map((tag, index) => (
            <Tag key={index} style={tagStyle} title={tag}>{tag}</Tag>
          ))}
          <Tag
            style={{
              ...tagStyle,
              background: '#f5f5f5',
              border: '1px dashed #d9d9d9',
              color: '#666',
              flexShrink: 0,
            }}
          >
            +{hiddenCount}
          </Tag>
        </div>
      </Tooltip>
    )
  }

  // 没有隐藏标签
  return (
    <div style={containerStyle}>
      {visibleTags.map((tag, index) => (
        <Tooltip key={index} title={tag} placement="topLeft">
          <Tag style={tagStyle}>{tag}</Tag>
        </Tooltip>
      ))}
    </div>
  )
}

export default TopicTags
