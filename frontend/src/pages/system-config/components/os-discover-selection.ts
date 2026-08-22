/** Selection helpers for the OS auto-discover results panel.
 *
 * Results render as one Table per direction group, and each Table's
 * rowSelection.onChange reports only that group's keys — so a group's
 * change must MERGE into the global selection instead of overwriting it
 * (overwriting wiped every other group's checked rows). */

export type SelectionKey = string | number | bigint

export function mergeGroupSelection(
  prev: SelectionKey[],
  groupRepoFullNames: string[],
  keys: SelectionKey[]
): SelectionKey[] {
  const groupKeys = new Set(groupRepoFullNames)
  return [...prev.filter(k => !groupKeys.has(k as string)), ...keys]
}
