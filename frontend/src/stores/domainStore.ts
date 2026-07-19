/**
 * Domain state management using Zustand.
 *
 * Currently only 'academic' is fully functional.
 * Other domains are placeholders with demo pages.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Domain } from '../theme'
import { applyDomainCssVars } from '../theme'

interface DomainState {
  currentDomain: Domain
  setDomain: (domain: Domain) => void
  isDomainAvailable: (domain: Domain) => boolean
}

/** Domains that have full functionality (not just demo) */
const availableDomains: Domain[] = ['academic', 'opensource', 'lab', 'competition']

export const useDomainStore = create<DomainState>()(
  persist(
    (set) => ({
      currentDomain: 'academic',

      setDomain: (domain) => {
        set({ currentDomain: domain })
        applyDomainCssVars(domain)
      },

      isDomainAvailable: (domain) => availableDomains.includes(domain),
    }),
    {
      name: 'talent-platform-domain',
      partialize: (state) => ({ currentDomain: state.currentDomain }),
    }
  )
)

// Apply CSS vars on app init — respect persisted domain if available
const stored = localStorage.getItem('talent-platform-domain')
let initDomain: Domain = 'academic'
if (stored) {
  try {
    const parsed = JSON.parse(stored)
    if (parsed.state?.currentDomain) {
      initDomain = parsed.state.currentDomain
    }
  } catch {
    /* fallback to default */
  }
}
applyDomainCssVars(initDomain)
