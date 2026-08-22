import { describe, expect, it } from 'vitest'

import { mergeGroupSelection } from './os-discover-selection'

describe('mergeGroupSelection', () => {
  it('keeps selections from other direction groups', () => {
    // Group A selected "a/one"; then group B's table reports its own keys —
    // pre-fix this overwrote the state and lost "a/one".
    const merged = mergeGroupSelection(['a/one'], ['b/one', 'b/two'], ['b/one'])
    expect(merged.sort()).toEqual(['a/one', 'b/one'])
  })

  it('replaces the group selection on change (uncheck works)', () => {
    const merged = mergeGroupSelection(
      ['a/one', 'a/two'],
      ['a/one', 'a/two'],
      ['a/two']
    )
    expect(merged).toEqual(['a/two'])
  })

  it('clearing a group keeps other groups intact', () => {
    const merged = mergeGroupSelection(
      ['a/one', 'b/one'],
      ['a/one', 'a/two'],
      []
    )
    expect(merged).toEqual(['b/one'])
  })
})
