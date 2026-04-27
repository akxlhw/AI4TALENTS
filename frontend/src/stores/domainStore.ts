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
const availableDomains: Domain[] = ['academic']

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

// Apply CSS vars on app init
applyDomainCssVars('academic')
