/**
 * AI Loading Overlay - AI主题加载遮罩层
 *
 * 特效元素：
 * - 神经网络粒子动画
 * - 脉冲光环效果
 * - 动态进度提示文字
 */
import { useEffect, useState } from 'react'
import { RobotOutlined } from '@ant-design/icons'
import './AILoadingOverlay.css'

interface AILoadingOverlayProps {
  visible: boolean
  title?: string
  steps?: string[]
}

const DEFAULT_STEPS = [
  '正在连接 AI 服务...',
  '解析职位描述...',
  '提取关键技能要求...',
  '分析研究方向匹配...',
  '计算候选人匹配度...',
  '生成推荐结果...',
]

const AILoadingOverlay: React.FC<AILoadingOverlayProps> = ({
  visible,
  title = 'AI 智能分析中',
  steps = DEFAULT_STEPS,
}) => {
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    if (!visible) {
      setCurrentStep(0)
      return
    }

    // 循环显示步骤提示
    const interval = setInterval(() => {
      setCurrentStep((prev) => (prev + 1) % steps.length)
    }, 2000)

    return () => clearInterval(interval)
  }, [visible, steps.length])

  if (!visible) return null

  return (
    <div className="ai-loading-overlay">
      <div className="ai-loading-content">
        {/* 神经网络背景 */}
        <div className="neural-network">
          <div className="node node-1" />
          <div className="node node-2" />
          <div className="node node-3" />
          <div className="node node-4" />
          <div className="node node-5" />
          <div className="node node-6" />
          <svg className="connections" viewBox="0 0 200 200">
            <line className="connection" x1="50" y1="50" x2="100" y2="100" />
            <line className="connection" x1="150" y1="50" x2="100" y2="100" />
            <line className="connection" x1="50" y1="150" x2="100" y2="100" />
            <line className="connection" x1="150" y1="150" x2="100" y2="100" />
            <line className="connection" x1="100" y1="30" x2="100" y2="100" />
            <line className="connection" x1="100" y1="170" x2="100" y2="100" />
          </svg>
        </div>

        {/* 中心 AI 图标 */}
        <div className="ai-icon-container">
          <div className="pulse-ring ring-1" />
          <div className="pulse-ring ring-2" />
          <div className="pulse-ring ring-3" />
          <div className="ai-icon">
            <RobotOutlined />
          </div>
        </div>

        {/* 标题和进度提示 */}
        <div className="ai-loading-text">
          <h3>{title}</h3>
          <div className="step-indicator">
            <div className="step-dots">
              {steps.map((_, idx) => (
                <span
                  key={idx}
                  className={`step-dot ${idx === currentStep ? 'active' : ''} ${idx < currentStep ? 'completed' : ''}`}
                />
              ))}
            </div>
            <p className="current-step">{steps[currentStep]}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AILoadingOverlay
