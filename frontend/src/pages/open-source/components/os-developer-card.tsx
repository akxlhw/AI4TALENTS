import { Button, Card, Checkbox, Col, Row, Space, Tag, Tooltip, Typography } from 'antd'
import { HeartFilled, HeartOutlined, StarOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { domainThemes, semanticColors } from '../../../theme'
import type { OSDeveloper } from '../../../types'

const { Text, Paragraph } = Typography

interface OsDeveloperCardProps {
  developer: OSDeveloper
  selected: boolean
  isFavorite: boolean
  onToggleFavorite: (developerId: number) => void
  onToggleSelect: (developerId: number) => void
}

const OsDeveloperCard: React.FC<OsDeveloperCardProps> = ({
  developer: dev,
  selected,
  isFavorite,
  onToggleFavorite,
  onToggleSelect,
}) => {
  const navigate = useNavigate()
  const primary = domainThemes.opensource.primary

  return (
    <Card
      hoverable
      className="domain-card"
      style={{
        borderLeft: `3px solid ${domainThemes.opensource.secondary}`,
        transition: 'all 0.2s ease',
        border: selected ? `2px solid ${primary}` : undefined,
      }}
      styles={{ body: { padding: '14px 16px' } }}
      onClick={() => navigate(`/opensource/developers/${dev.developer_id}`)}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: 8,
        }}
      >
        <Space align="start">
          {dev.avatar_url ? (
            <img
              src={`${dev.avatar_url}${dev.avatar_url.includes('?') ? '&' : '?'}s=64`}
              alt={dev.name || dev.github_login}
              loading="lazy"
              style={{ width: 40, height: 40, borderRadius: 20, objectFit: 'cover' }}
            />
          ) : (
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 20,
                background: primary,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontSize: 16,
                fontWeight: 600,
              }}
            >
              {(dev.name || dev.github_login)?.[0]?.toUpperCase()}
            </div>
          )}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
              <Text strong style={{ fontSize: 14 }}>
                {dev.name || dev.github_login}
              </Text>
              {dev.roles?.includes('Owner') && (
                <Tag
                  style={{
                    fontSize: 10,
                    lineHeight: '16px',
                    padding: '0 6px',
                    borderRadius: 4,
                    margin: 0,
                    background: semanticColors.osYellow,
                    color: '#fff',
                    border: 'none',
                    fontWeight: 600,
                  }}
                >
                  Owner
                </Tag>
              )}
              {dev.roles?.includes('Committer') && (
                <Tag
                  style={{
                    fontSize: 10,
                    lineHeight: '16px',
                    padding: '0 6px',
                    borderRadius: 4,
                    margin: 0,
                    background: semanticColors.osBlue,
                    color: '#fff',
                    border: 'none',
                    fontWeight: 600,
                  }}
                >
                  Committer
                </Tag>
              )}
              {dev.is_student && (
                <Tag
                  color="green"
                  style={{
                    fontSize: 10,
                    lineHeight: '16px',
                    padding: '0 6px',
                    borderRadius: 4,
                    margin: 0,
                    fontWeight: 600,
                  }}
                >
                  在校生
                </Tag>
              )}
            </div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              @{dev.github_login}
            </Text>
          </div>
        </Space>
        <Button
          type="text"
          size="small"
          style={{ padding: '0 4px', margin: 0, flexShrink: 0 }}
          icon={
            isFavorite ? <HeartFilled style={{ color: semanticColors.red }} /> : <HeartOutlined />
          }
          onClick={e => {
            e.stopPropagation()
            onToggleFavorite(dev.developer_id)
          }}
        />
      </div>

      <Paragraph
        ellipsis={{ rows: 1 }}
        style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}
      >
        {dev.bio || '暂无简介'}
      </Paragraph>

      <Row gutter={16}>
        <Col span={6}>
          <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>Stars</Text>
          <div style={{ fontWeight: 700, color: primary, fontSize: 13 }}>
            <StarOutlined style={{ fontSize: 11, marginRight: 2 }} />
            {(dev.total_stars_received / 1000).toFixed(1)}k
          </div>
        </Col>
        <Col span={6}>
          <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>开发语言</Text>
          <Tooltip
            title={
              <Space size={4} wrap>
                {(dev.primary_languages || []).map(lang => (
                  <Tag key={lang} style={{ fontSize: 11, borderRadius: 4, margin: 0 }}>
                    {lang}
                  </Tag>
                ))}
                {(dev.primary_languages || []).length === 0 && '无'}
              </Space>
            }
          >
            <div
              style={{
                fontWeight: 700,
                color: primary,
                fontSize: 13,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {(dev.primary_languages || []).slice(0, 2).join(', ') || '-'}
            </div>
          </Tooltip>
        </Col>
        <Col span={6}>
          <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>公司</Text>
          <div
            style={{
              fontWeight: 700,
              color: primary,
              fontSize: 13,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {dev.company || '-'}
          </div>
        </Col>
        <Col span={6}>
          <Text style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>地区</Text>
          <div
            style={{
              fontWeight: 700,
              color: primary,
              fontSize: 13,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {dev.location || '-'}
          </div>
        </Col>
      </Row>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: 10,
          paddingTop: 10,
          borderTop: `1px solid ${semanticColors.borderGrayLight}`,
        }}
        onClick={e => e.stopPropagation()}
      >
        <Checkbox checked={selected} onChange={() => onToggleSelect(dev.developer_id)}>
          选择
        </Checkbox>
      </div>
    </Card>
  )
}

export default OsDeveloperCard
