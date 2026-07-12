import React from 'react'

interface LabIconProps {
  className?: string
  style?: React.CSSProperties
}

/**
 * AI Lab domain icon.
 *
 * A microchip/processor glyph drawn in the same outlined stroke style as
 * Ant Design icons (BookOutlined, CodeOutlined, TrophyOutlined, BuildOutlined)
 * so the domain switcher feels visually consistent.
 */
const LabIcon: React.FC<LabIconProps> = ({ className, style }) => {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={{ display: 'inline-block', width: '1em', height: '1em', ...style }}
      aria-hidden="true"
      focusable="false"
    >
      {/* Chip body */}
      <rect x="7.5" y="7.5" width="9" height="9" rx="1.6" />
      {/* Chip pins */}
      <path d="M7.5 10.5h-2M7.5 13.5h-2M16.5 10.5h2M16.5 13.5h2M10.5 7.5v-2M13.5 7.5v-2M10.5 16.5v2M13.5 16.5v2" />
      {/* Core dot */}
      <circle cx="12" cy="12" r="1.4" fill="currentColor" stroke="none" />
    </svg>
  )
}

export default LabIcon
