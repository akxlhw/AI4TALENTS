import { useEffect, useCallback } from 'react'

interface KeyboardShortcut {
  key: string
  ctrlKey?: boolean
  metaKey?: boolean
  shiftKey?: boolean
  action: () => void
  description?: string
}

/**
 * Hook to handle keyboard shortcuts
 *
 * @param shortcuts - Array of shortcut definitions
 * @param enabled - Whether shortcuts are enabled
 *
 * Example usage:
 * useKeyboardShortcuts([
 *   { key: '/', action: () => inputRef.current?.focus() },
 *   { key: 'f', ctrlKey: true, action: () => inputRef.current?.focus() },
 *   { key: 'Escape', action: () => setModalVisible(false) },
 * ])
 */
export function useKeyboardShortcuts(
  shortcuts: KeyboardShortcut[],
  enabled: boolean = true
) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return

      // Don't trigger shortcuts when typing in input fields
      const target = event.target as HTMLElement
      const isInputField =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable

      for (const shortcut of shortcuts) {
        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase()
        const ctrlMatch = shortcut.ctrlKey ? (event.ctrlKey || event.metaKey) : !event.ctrlKey && !event.metaKey
        const shiftMatch = shortcut.shiftKey ? event.shiftKey : !event.shiftKey

        // For 'Escape' key, allow it even in input fields
        // For other keys, skip if in input field (unless ctrl/cmd is pressed)
        if (shortcut.key.toLowerCase() === 'escape') {
          if (keyMatch) {
            event.preventDefault()
            shortcut.action()
            return
          }
        } else if (isInputField && !shortcut.ctrlKey && !shortcut.metaKey) {
          continue
        }

        if (keyMatch && ctrlMatch && shiftMatch) {
          event.preventDefault()
          shortcut.action()
          return
        }
      }
    },
    [shortcuts, enabled]
  )

  useEffect(() => {
    if (enabled) {
      window.addEventListener('keydown', handleKeyDown)
      return () => window.removeEventListener('keydown', handleKeyDown)
    }
  }, [handleKeyDown, enabled])
}

export default useKeyboardShortcuts
