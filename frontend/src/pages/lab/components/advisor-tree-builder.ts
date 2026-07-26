import { ROLE_COLORS } from '../constants/lab-role'

export interface NetworkNode {
  name: string
  talent_id: number | null
  role_type: string
  is_student: boolean
  photo_url: string | null
  is_founder: boolean
}

export interface NetworkEdge {
  source: string
  target: string
  type: string // advisor / co_advisor
}

export interface TreeNode {
  name: string
  children?: TreeNode[]
  talent_id?: number | null
  has_children?: boolean
  // echarts visuals
  symbol?: string
  symbolSize?: number | number[]
  symbolKeepAspect?: boolean
  itemStyle?: Record<string, unknown>
  label?: Record<string, unknown>
  tooltip?: { formatter: string }
  collapsed?: boolean
}

export interface BuiltTree {
  root: TreeNode
  totalNodes: number
  /** Leaf count drives canvas width, depth drives canvas height — keeps
   * per-node spacing constant in px regardless of tree size. */
  leafCount: number
  depth: number
}

function measure(t: TreeNode): { leaves: number; depth: number } {
  const kids = t.children ?? []
  if (!kids.length) return { leaves: 1, depth: 1 }
  let leaves = 0
  let depth = 0
  for (const k of kids) {
    const m = measure(k)
    leaves += m.leaves
    depth = Math.max(depth, m.depth)
  }
  return { leaves, depth: depth + 1 }
}

const FOUNDER_GOLD = '#D4AF37'
const ADVISOR_COLOR = '#0D2B4E'
const STUDENT_COLOR = '#0EA5E9'
const AGGREGATE_COLOR = '#94A3B8'

function initialsOf(name: string): string {
  return name.trim().charAt(0).toUpperCase()
}

function makeVisual(
  node: NetworkNode | null,
  opts: { founder?: boolean; aggregate?: boolean },
  displayName: string,
  tooltipExtra: string,
): Pick<TreeNode, 'symbol' | 'symbolSize' | 'symbolKeepAspect' | 'itemStyle' | 'label' | 'tooltip'> {
  const size = opts.founder ? 52 : opts.aggregate ? 30 : node?.is_student ? 28 : 40
  const borderColor = opts.founder
    ? FOUNDER_GOLD
    : opts.aggregate
      ? AGGREGATE_COLOR
      : node
        ? ROLE_COLORS[node.role_type] || (node.is_student ? STUDENT_COLOR : ADVISOR_COLOR)
        : AGGREGATE_COLOR
  const borderWidth = opts.founder ? 3 : 2
  const title = opts.founder ? `👑 创始人 · ${displayName}` : displayName
  const tooltip = tooltipExtra ? `${title}<br/>${tooltipExtra}` : title

  if (!opts.aggregate && node?.photo_url) {
    return {
      symbol: `image://${node.photo_url}`,
      symbolSize: size,
      symbolKeepAspect: true,
      itemStyle: { borderColor, borderWidth },
      label: { show: true, position: 'bottom', fontSize: opts.founder ? 13 : 11, color: '#333' },
      tooltip: { formatter: tooltip },
    }
  }
  return {
    symbol: 'circle',
    symbolSize: size,
    itemStyle: {
      color: opts.aggregate ? '#F1F5F9' : borderColor,
      borderColor,
      borderWidth,
    },
    label: {
      show: true,
      position: 'bottom',
      fontSize: opts.founder ? 13 : 11,
      color: '#333',
      formatter: (p: { name?: string }) => (p.name ? `${initialsOf(p.name)} ${p.name}` : ''),
    },
    tooltip: { formatter: tooltip },
  }
}

/** Build an ECharts tree from flat nodes/edges. Founder-pinned when present,
 * otherwise a neutral forest under a virtual lab root. Cycles are cut at the
 * first repeated node on a branch. */
export function buildTree(
  nodes: NetworkNode[],
  edges: NetworkEdge[],
  labName: string,
): BuiltTree {
  const byName = new Map(nodes.map(n => [n.name, n]))
  const childrenOf = new Map<string, string[]>()
  const coOf = new Map<string, string[]>()
  for (const e of edges) {
    if (e.type === 'co_advisor') {
      coOf.set(e.target, [...(coOf.get(e.target) ?? []), e.source])
    } else {
      childrenOf.set(e.source, [...(childrenOf.get(e.source) ?? []), e.target])
    }
  }

  const toTreeNode = (name: string, visited: Set<string>): TreeNode => {
    const person = byName.get(name) ?? null
    const coList = coOf.get(name) ?? []
    const tooltipExtra = coList.length ? `共同指导：${coList.join('、')}` : ''
    const kids = visited.has(name)
      ? []
      : (childrenOf.get(name) ?? []).filter(k => byName.has(k) && !visited.has(k))
    visited.add(name)
    const childNodes = kids.map(k => toTreeNode(k, visited))
    const founder = person?.is_founder === true
    return {
      name,
      talent_id: person?.talent_id ?? null,
      has_children: childNodes.length > 0,
      ...(childNodes.length ? { children: childNodes } : {}),
      ...makeVisual(person, { founder }, name, tooltipExtra),
    }
  }

  const collectNames = (t: TreeNode, acc: Set<string>): void => {
    acc.add(t.name)
    ;(t.children ?? []).forEach(c => collectNames(c, acc))
  }

  const founderNode = nodes.find(n => n.is_founder)
  if (founderNode) {
    // Founder-pinned: founder is the root; his student subtree + an
    // organizational "其他导师" aggregate for the remaining advisors.
    const founderTree = toTreeNode(founderNode.name, new Set())
    const subtree = new Set<string>()
    collectNames(founderTree, subtree)

    const otherAdvisorTrees = [...childrenOf.keys()]
      .filter(name => !subtree.has(name) && byName.has(name))
      .sort((a, b) => (childrenOf.get(b)?.length ?? 0) - (childrenOf.get(a)?.length ?? 0))
      .map(name => toTreeNode(name, new Set(subtree)))

    const children = [...(founderTree.children ?? [])]
    if (otherAdvisorTrees.length) {
      children.push({
        name: '其他导师',
        talent_id: null,
        has_children: true,
        children: otherAdvisorTrees,
        ...makeVisual(null, { aggregate: true }, '其他导师', '组织分组（非师承关系）'),
      })
    }
    return withMeasure({ ...founderTree, children })
  }

  // Neutral forest: virtual lab root → all advisors in parallel (sorted by
  // student count), each with their own student subtree.
  const topAdvisors = [...childrenOf.keys()]
    .filter(name => byName.has(name))
    .sort((a, b) => (childrenOf.get(b)?.length ?? 0) - (childrenOf.get(a)?.length ?? 0))
  return withMeasure({
    name: labName,
    talent_id: null,
    has_children: true,
    children: topAdvisors.map(name => toTreeNode(name, new Set())),
    ...makeVisual(null, { aggregate: true }, labName, ''),
  })

  function withMeasure(root: TreeNode): BuiltTree {
    const m = measure(root)
    return { root, totalNodes: nodes.length, leafCount: m.leaves, depth: m.depth }
  }
}
