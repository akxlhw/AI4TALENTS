/**
 * Dev-only console logging — silent in production builds.
 *
 * Use instead of bare console.* so diagnostics stay available during
 * development without shipping to production users.
 */
export const logger = {
  error: (...args: unknown[]) => {
    if (import.meta.env.DEV) console.error(...args)
  },
  warn: (...args: unknown[]) => {
    if (import.meta.env.DEV) console.warn(...args)
  },
}
