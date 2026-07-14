import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Avatar, Typography } from 'antd'
import LabIcon from '../../../components/lab-icon'
import type { LabWithTalents } from '../../../types'
import { ROLE_CONFIG, ROLE_COLORS } from '../constants/lab-role'

const { Title, Text } = Typography

interface LabCardProps {
  lab: LabWithTalents
}

const LabCard: React.FC<React.PropsWithChildren<LabCardProps>> = ({ lab }) => {
  const navigate = useNavigate()
  const previewTalents = lab.talents.slice(0, 5)
  const overflow = Math.max(0, lab.count - previewTalents.length)

  // Build mini composition bar segments
  const dist = lab.role_distribution || {}
  const total = Object.values(dist).reduce((a, b) => a + b, 0) || 1
  const segments = ROLE_CONFIG.filter(r => dist[r.key] > 0).map(r => ({
    ...r,
    count: dist[r.key],
    pct: (dist[r.key] / total) * 100,
  }))

  return (
    <div
      onClick={() => navigate(`/lab/search?parent_lab=${encodeURIComponent(lab.name)}`)}
      style={{
        borderRadius: 14,
        overflow: 'hidden',
        background: '#fff',
        cursor: 'pointer',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        border: '1px solid var(--color-border, #e8e8e8)',
        transition: 'transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.transform = 'translateY(-4px)'
        e.currentTarget.style.boxShadow = '0 12px 32px rgba(13,43,78,0.12)'
        e.currentTarget.style.borderColor = 'var(--domain-secondary, #0EA5E9)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = ''
        e.currentTarget.style.boxShadow = ''
        e.currentTarget.style.borderColor = 'var(--color-border, #e8e8e8)'
      }}
    >
      {/* === Brand Banner === */}
      <div
        style={{
          background: 'var(--domain-gradient, linear-gradient(135deg,#0D2B4E,#0EA5E9))',
          padding: '14px 18px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 10,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, flex: 1 }}>
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              background: 'rgba(255,255,255,0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              overflow: 'hidden',
            }}
          >
            {lab.logo_url ? (
              <img src={lab.logo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              <LabIcon style={{ fontSize: 20, color: '#fff' }} />
            )}
          </div>
          <Title
            level={5}
            ellipsis
            style={{
              margin: 0,
              color: '#fff',
              fontWeight: 600,
              fontSize: 15,
              lineHeight: 1.3,
            }}
          >
            {lab.name}
          </Title>
        </div>
        <div style={{ textAlign: 'right', flexShrink: 0, whiteSpace: 'nowrap' }}>
          <span style={{ color: '#fff', fontSize: 22, fontWeight: 700, lineHeight: 1 }}>{lab.count}</span>
          <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 13, marginLeft: 2 }}>人</span>
        </div>
      </div>

      {/* === Body === */}
      <div style={{ padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: 12, flex: 1 }}>
        {/* Lab description */}
        {lab.description && (
          <Text
            style={{
              fontSize: 12,
              color: '#64748b',
              lineHeight: 1.6,
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {lab.description}
          </Text>
        )}

        {/* Avatar stack */}
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{ display: 'flex' }}>
            {previewTalents.map((talent, i) => (
              <Avatar
                key={talent.talent_id}
                src={talent.photo_url || undefined}
                size={32}
                style={{
                  marginLeft: i === 0 ? 0 : -10,
                  border: '2px solid #fff',
                  backgroundColor: ROLE_COLORS[talent.role_type] || ROLE_COLORS.unknown,
                  fontSize: 12,
                  zIndex: previewTalents.length - i,
                }}
              >
                {talent.name.charAt(0)}
              </Avatar>
            ))}
          </div>
          {overflow > 0 && (
            <div
              style={{
                marginLeft: -10,
                width: 32,
                height: 32,
                borderRadius: '50%',
                border: '2px solid #fff',
                background: 'var(--domain-light-bg, #F0F9FF)',
                color: 'var(--domain-primary, #0D2B4E)',
                fontSize: 11,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 0,
              }}
            >
              +{overflow > 99 ? '99' : overflow}
            </div>
          )}
        </div>

        {/* Mini composition bar */}
        {segments.length > 0 && (
          <div>
            <div
              style={{
                display: 'flex',
                height: 6,
                borderRadius: 3,
                overflow: 'hidden',
                background: '#f0f0f0',
              }}
            >
              {segments.map(seg => (
                <div
                  key={seg.key}
                  style={{
                    width: `${seg.pct}%`,
                    background: seg.color,
                    transition: 'width 0.3s ease',
                  }}
                  title={`${seg.label}: ${seg.count} (${seg.pct.toFixed(0)}%)`}
                />
              ))}
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 6 }}>
              {segments.map(seg => (
                <div key={seg.key} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: seg.color }} />
                  <Text style={{ fontSize: 11, color: '#666' }}>
                    {seg.label} {seg.pct.toFixed(0)}%
                  </Text>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default LabCard
