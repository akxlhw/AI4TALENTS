/**
 * Tech element taxonomy (v2) — frontend mirror of
 * backend/app/domains/shared/constants/tech_taxonomy.py.
 * 10 domains → 34 elements (tech_element valid values) → 75 directions.
 * Update both files together.
 * Shared module — import from '@/constants/tech-elements'.
 */

export interface TechElementOption {
  value: string
  label: string
  color: string
  domain: string
}

// Domain display colors (one per domain, elements inherit)
const DOMAIN_COLORS: Record<string, string> = {
  basic_software: '#1A365D',
  ai_models: '#722ed1',
  ai_apps: '#9254de',
  communications: '#1677ff',
  computing: '#08979c',
  modeling_simulation: '#d4660a',
  trusted_security: '#cf1322',
  multimedia: '#eb2f96',
  robotics: '#389e0d',
  autonomous_driving: '#237804',
}

export const DOMAIN_LABELS: Record<string, string> = {
  basic_software: '基础软件',
  ai_models: 'AI大模型',
  ai_apps: 'AI软件',
  communications: '通信技术',
  computing: '计算技术',
  modeling_simulation: '建模仿真与数学应用',
  trusted_security: '可信安全',
  multimedia: '多媒体',
  robotics: '机器人',
  autonomous_driving: '自动驾驶',
}

// Flat list of 34 element codes with domain grouping + colors
export const TECH_ELEMENTS: TechElementOption[] = [
  // 基础软件
  { value: 'os', label: '操作系统', color: DOMAIN_COLORS.basic_software, domain: 'basic_software' },
  { value: 'db_storage', label: '数据库与存储', color: DOMAIN_COLORS.basic_software, domain: 'basic_software' },
  { value: 'languages', label: '编程语言', color: DOMAIN_COLORS.basic_software, domain: 'basic_software' },
  { value: 'toolchain', label: '编译与构建', color: DOMAIN_COLORS.basic_software, domain: 'basic_software' },
  { value: 'middleware', label: '中间件', color: DOMAIN_COLORS.basic_software, domain: 'basic_software' },
  { value: 'browser', label: '浏览器与引擎', color: DOMAIN_COLORS.basic_software, domain: 'basic_software' },
  // AI大模型
  { value: 'models', label: '模型', color: DOMAIN_COLORS.ai_models, domain: 'ai_models' },
  { value: 'training', label: '训练', color: DOMAIN_COLORS.ai_models, domain: 'ai_models' },
  { value: 'inference', label: '推理', color: DOMAIN_COLORS.ai_models, domain: 'ai_models' },
  // AI软件
  { value: 'agents', label: '智能体与工具', color: DOMAIN_COLORS.ai_apps, domain: 'ai_apps' },
  { value: 'ai_engineering', label: 'AI工程', color: DOMAIN_COLORS.ai_apps, domain: 'ai_apps' },
  { value: 'apps', label: '应用', color: DOMAIN_COLORS.ai_apps, domain: 'ai_apps' },
  // 通信技术
  { value: 'protocols', label: '网络协议与栈', color: DOMAIN_COLORS.communications, domain: 'communications' },
  { value: 'wireless', label: '无线通信', color: DOMAIN_COLORS.communications, domain: 'communications' },
  { value: 'network_simulation', label: '网络仿真', color: DOMAIN_COLORS.communications, domain: 'communications' },
  // 计算技术
  { value: 'hpc', label: '高性能计算', color: DOMAIN_COLORS.computing, domain: 'computing' },
  { value: 'cloud_native', label: '云原生', color: DOMAIN_COLORS.computing, domain: 'computing' },
  { value: 'virtualization', label: '虚拟化', color: DOMAIN_COLORS.computing, domain: 'computing' },
  { value: 'silicon', label: '开源芯片', color: DOMAIN_COLORS.computing, domain: 'computing' },
  // 建模仿真与数学应用
  { value: 'sci_compute', label: '科学计算', color: DOMAIN_COLORS.modeling_simulation, domain: 'modeling_simulation' },
  { value: 'simulation', label: '仿真', color: DOMAIN_COLORS.modeling_simulation, domain: 'modeling_simulation' },
  { value: 'math_libs', label: '数学库', color: DOMAIN_COLORS.modeling_simulation, domain: 'modeling_simulation' },
  // 可信安全
  { value: 'sys_sec', label: '系统与网络安全', color: DOMAIN_COLORS.trusted_security, domain: 'trusted_security' },
  { value: 'sec_ops', label: '攻防与检测', color: DOMAIN_COLORS.trusted_security, domain: 'trusted_security' },
  { value: 'crypto_trust', label: '密码与信任', color: DOMAIN_COLORS.trusted_security, domain: 'trusted_security' },
  // 多媒体
  { value: 'av', label: '音视频', color: DOMAIN_COLORS.multimedia, domain: 'multimedia' },
  { value: 'graphics', label: '图形图像', color: DOMAIN_COLORS.multimedia, domain: 'multimedia' },
  // 机器人
  { value: 'robot_control', label: '本体与控制', color: DOMAIN_COLORS.robotics, domain: 'robotics' },
  { value: 'robot_perception', label: '感知', color: DOMAIN_COLORS.robotics, domain: 'robotics' },
  { value: 'embodied', label: '具身智能', color: DOMAIN_COLORS.robotics, domain: 'robotics' },
  // 自动驾驶
  { value: 'ad_platforms', label: '全栈平台', color: DOMAIN_COLORS.autonomous_driving, domain: 'autonomous_driving' },
  { value: 'ad_perception', label: '感知与定位', color: DOMAIN_COLORS.autonomous_driving, domain: 'autonomous_driving' },
  { value: 'ad_planning', label: '规划控制', color: DOMAIN_COLORS.autonomous_driving, domain: 'autonomous_driving' },
  { value: 'ad_simulation', label: '仿真', color: DOMAIN_COLORS.autonomous_driving, domain: 'autonomous_driving' },
]

/** Options grouped by domain for OptGroup-style selects */
export const TECH_ELEMENT_GROUPS = Object.entries(
  TECH_ELEMENTS.reduce<Record<string, TechElementOption[]>>((acc, el) => {
    ;(acc[el.domain] = acc[el.domain] || []).push(el)
    return acc
  }, {})
).map(([domain, elements]) => ({
  label: DOMAIN_LABELS[domain] || domain,
  options: elements.map(e => ({ value: e.value, label: e.label })),
}))

export const getTechElementLabel = (code: string): string =>
  TECH_ELEMENTS.find(t => t.value === code)?.label || code

export const getTechElementColor = (code: string): string =>
  TECH_ELEMENTS.find(t => t.value === code)?.color || '#999'

/** "领域 · 要素" full label, e.g. "AI大模型 · 训练" — for surfaces where the
 * parent domain should be visible alongside the element. */
export const getTechElementFullLabel = (code: string): string => {
  const el = TECH_ELEMENTS.find(t => t.value === code)
  if (!el) return code
  return `${DOMAIN_LABELS[el.domain] || el.domain} · ${el.label}`
}

export const getTechElementDomain = (code: string): string | undefined =>
  TECH_ELEMENTS.find(t => t.value === code)?.domain
