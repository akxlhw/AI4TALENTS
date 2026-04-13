/**
 * AI Loading Overlay - AI主题加载遮罩层
 *
 * 特效元素：
 * - 神经网络粒子动画
 * - 脉冲光环效果
 * - 动态进度提示文字（线性推进）
 */
import { useEffect, useState, useRef } from 'react'
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

const STEP_INTERVAL = 2500 // 每个步骤间隔时间(ms)

const AILoadingOverlay: React.FC<AILoadingOverlayProps> = ({
  visible,
  title = 'AI 智能分析中',
  steps = DEFAULT_STEPS,
}) => {
  const [currentStep, setCurrentStep] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!visible) {
      // 重置状态
      setCurrentStep(0)
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
      return
    }

    // 重置到第一步
    setCurrentStep(0)

    // 线性推进步骤，到达最后一步后停止
    timerRef.current = setInterval(() => {
      setCurrentStep((prev) => {
        // 到达最后一步就停止，不再推进
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
