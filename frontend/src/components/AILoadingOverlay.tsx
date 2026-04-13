/**
 * AI Loading Overlay - AI4RECRUIT 智能人才库
 *
 * 设计理念：
 * - 简洁优雅，符合 Ant Design v5 设计语言
 * - 品牌标识清晰展示
 * - 微妙的 AI 视觉元素
 * - 进度可视化反馈
 */
import { useEffect, useState, useRef } from 'react'
import './AILoadingOverlay.css'

interface AILoadingOverlayProps {
  visible: boolean
  title?: string
  steps?: string[]
}

const DEFAULT_STEPS = [
  '连接 AI 服务',
  '解析职位描述',
  '提取技能要求',
  '匹配候选人',
  '生成推荐结果',
]

const STEP_INTERVAL = 2500

const AILoadingOverlay: React.FC<AILoadingOverlayProps> = ({
  visible,
  title = '智能分析中',
  steps = DEFAULT_STEPS,
}) => {
  const [currentStep, setCurrentStep] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!visible) {
      setCurrentStep(0)
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      return
    }

    setCurrentStep(0)

    timerRef.current = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= steps.length - 1) {
          return prev
        }
        return prev + 1
      })
    }, STEP_INTERVAL)

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }, [visible, steps.length])

  if (!visible) return null

  return (
    <div className="ai-loading-overlay">
      <div className="loading-container">
        {/* 品牌区域 */}
        <div className="brand-section">
          <div className="brand-name">
            <span className="brand-ai">AI</span>
            <span className="brand-connector">4</span>
            <span className="brand-recruit">RECRUIT</span>
          </div>
          <div className="brand-tagline">智能人才发现平台</div>
        </div>

        {/* 主视觉区域 */}
        <div className="visual-section">
          {/* 外圈动画 */}
          <div className="orbit-ring">
            <div className="orbit-dot dot-1" />
            <div className="orbit-dot dot-2" />
            <div className="orbit-dot dot-3" />
          </div>

          {/* 中心图标 */}
          <div className="center-icon">
            <svg viewBox="0 0 48 48" className="ai-svg">
              {/* 大脑轮廓 */}
              <path
                className="brain-path"
                d="M24 4C14 4 8 12 8 20C8 28 12 34 18 38L18 42L30 42L30 38C36 34 40 28 40 20C40 12 34 4 24 4Z"
                fill="none"
                strokeWidth="2"
              />
              {/* 神经连接线 */}
              <path className="neural-line line-1" d="M16 18 L24 24 L32 18" fill="none" strokeWidth="1.5" />
              <path className="neural-line line-2" d="M16 28 L24 22 L32 28" fill="none" strokeWidth="1.5" />
              {/* 连接节点 */}
              <circle className="node node-1" cx="16" cy="18" r="2" />
              <circle className="node node-2" cx="32" cy="18" r="2" />
              <circle className="node node-3" cx="24" cy="24" r="2.5" />
              <circle className="node node-4" cx="16" cy="28" r="2" />
              <circle className="node node-5" cx="32" cy="28" r="2" />
            </svg>
          </div>
        </div>

        {/* 状态区域 */}
        <div className="status-section">
          <h3 className="status-title">{title}</h3>

          {/* 步骤进度条 */}
          <div className="step-progress">
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
              />
            </div>
            <div className="step-label">
              <span className="step-number">{currentStep + 1}/{steps.length}</span>
              <span className="step-text">{steps[currentStep]}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AILoadingOverlay
