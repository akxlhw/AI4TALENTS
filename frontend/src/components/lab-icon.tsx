import React from 'react'

interface LabIconProps {
  className?: string
  style?: React.CSSProperties
}

/**
 * AI Lab domain icon — "future star" motif.
 *
 * Two outlined four-point sparkles of different sizes, evoking emerging AI
 * talent and generative sparkle. Drawn with the same stroke style as Ant
 * Design icons so the domain switcher stays visually consistent.
 */
const LabIcon: React.FC<LabIconProps> = ({ className, style }) => {
  const sparkle = (cx: number, cy: number, s: number) => {
    // Four-point star: top, right, bottom, left with curved inset corners.
    const t = `${cx},${cy - s}`
    const r = `${cx + s},${cy}`
    const b = `${cx},${cy + s}`
    const l = `${cx - s},${cy}`
    const it = `${cx},${cy - s * 0.35}`
    const ir = `${cx + s * 0.35},${cy}`
    const ib = `${cx},${cy + s * 0.35}`
    const il = `${cx - s * 0.35},${cy}`
    return `M${t} Q${ir} ${r} Q${ib} ${b} Q${il} ${l} Q${it} ${t} Z`
  }

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
      {/* Larger star, lower-left */}
      <path d={sparkle(10, 15, 6)} />
      {/* Smaller star, upper-right */}
      <path d={sparkle(17, 7, 3.5)} />
    </svg>
  )
}

export default LabIcon
