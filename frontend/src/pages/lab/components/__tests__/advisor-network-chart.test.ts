import { describe, it, expect } from 'vitest'
import { buildTree } from '../advisor-tree-builder'

interface N {
  name: string
  talent_id: number | null
  role_type: string
  is_student: boolean
  photo_url: string | null
  is_founder: boolean
}

const person = (name: string, opts: Partial<N> = {}): N => ({
  name,
  talent_id: 1,
  role_type: 'professor',
  is_student: false,
  photo_url: null,
  is_founder: false,
  ...opts,
})

describe('buildTree', () => {
  it('pins the founder as root and aggregates remaining advisors under 其他导师', () => {
    const nodes = [
      person('周志华', { is_founder: true, talent_id: 99 }),
      person('学生甲', { is_student: true, role_type: 'student' }),
      person('教授B'),
      person('学生乙', { is_student: true, role_type: 'student' }),
    ]
    const edges = [
      { source: '周志华', target: '学生甲', type: 'advisor' },
      { source: '教授B', target: '学生乙', type: 'advisor' },
    ]
    const { root } = buildTree(nodes, edges, '南京大学LAMDA实验室')

    expect(root.name).toBe('周志华')
    const childNames = (root.children ?? []).map(c => c.name)
    expect(childNames).toContain('学生（1）')
    expect(childNames).toContain('其他导师')
    const students = (root.children ?? []).find(c => c.name === '学生（1）')
    expect(students?.children?.map(c => c.name)).toEqual(['学生甲'])
    expect(students?.collapsed).toBe(true)
    const agg = (root.children ?? []).find(c => c.name === '其他导师')
    expect(agg?.children?.map(c => c.name)).toEqual(['教授B'])
    expect(agg?.children?.[0].children?.map(c => c.name)).toEqual(['学生乙'])
  })

  it('keeps professor-students as expanded real edges and folds plain students', () => {
    const nodes = [
      person('周志华', { is_founder: true, talent_id: 99 }),
      person('黎铭'),
      person('徒孙甲', { is_student: true, role_type: 'student' }),
      person('学生甲', { is_student: true, role_type: 'student' }),
      person('学生乙', { is_student: true, role_type: 'student' }),
    ]
    const edges = [
      { source: '周志华', target: '黎铭', type: 'advisor' },
      { source: '周志华', target: '学生甲', type: 'advisor' },
      { source: '周志华', target: '学生乙', type: 'advisor' },
      { source: '黎铭', target: '徒孙甲', type: 'advisor' },
    ]
    const { root } = buildTree(nodes, edges, '南京大学LAMDA实验室')

    const childNames = (root.children ?? []).map(c => c.name)
    // professor-student stays a direct child, expanded one level
    expect(childNames[0]).toBe('黎铭')
    const liming = (root.children ?? [])[0]
    expect(liming.collapsed).toBe(false)
    expect(liming.children?.map(c => c.name)).toEqual(['徒孙甲'])
    // plain students fold into a collapsed aggregate
    const students = (root.children ?? []).find(c => c.name === '学生（2）')
    expect(students?.collapsed).toBe(true)
    expect(students?.children?.map(c => c.name)).toEqual(['学生甲', '学生乙'])
  })

  it('renders a parallel forest under the lab root when no founder exists', () => {
    const nodes = [
      person('教授A'),
      person('教授B'),
      person('学生甲', { is_student: true, role_type: 'student' }),
      person('学生乙', { is_student: true, role_type: 'student' }),
    ]
    const edges = [
      { source: '教授A', target: '学生甲', type: 'advisor' },
      { source: '教授B', target: '学生乙', type: 'advisor' },
    ]
    const { root } = buildTree(nodes, edges, 'MIT CSAIL')

    expect(root.name).toBe('MIT CSAIL')
    const childNames = (root.children ?? []).map(c => c.name)
    expect(new Set(childNames)).toEqual(new Set(['教授A', '教授B']))
    // no founder aggregate node in forest mode
    expect(childNames).not.toContain('其他导师')
  })

  it('supports multi-generation trees and guards cycles', () => {
    const nodes = [
      person('A'),
      person('B'),
      person('C', { is_student: true, role_type: 'student' }),
    ]
    const edges = [
      { source: 'A', target: 'B', type: 'advisor' },
      { source: 'B', target: 'C', type: 'advisor' },
      { source: 'C', target: 'A', type: 'advisor' }, // cycle A→B→C→A
    ]
    const { root } = buildTree(nodes, edges, 'X Lab')
    // must terminate; A is top advisor with B under it, C under B, no infinite loop
    expect(root.name).toBe('X Lab')
    const a = (root.children ?? []).find(c => c.name === 'A')
    expect(a?.children?.[0].name).toBe('B')
    expect(a?.children?.[0].children?.[0].name).toBe('C')
    expect(a?.children?.[0].children?.[0].children ?? []).toEqual([])
  })
})
