import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Session } from '../types'

interface SessionState {
  activeSessionId: string | null
  activeSession: Session | null
  setActiveSession: (session: Session) => void
  clearSession: () => void
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      activeSessionId: null,
      activeSession: null,
      setActiveSession: (session) => set({ activeSessionId: session.id, activeSession: session }),
      clearSession: () => set({ activeSessionId: null, activeSession: null }),
    }),
    { name: 'lexi-session', partialize: (s) => ({ activeSessionId: s.activeSessionId }) }
  )
)
