import { create } from 'zustand'
import type { MessageExtras, StageEvent } from '../types'

interface ChatState {
  // Per-message extras keyed by message ID
  extrasMap: Record<string, MessageExtras>
  setExtras: (messageId: string, extras: MessageExtras) => void

  // Pipeline progress for the current in-flight query
  currentStages: StageEvent[]
  pushStage: (event: StageEvent) => void
  clearStages: () => void

  // Error banner
  error: string | null
  setError: (msg: string | null) => void

  // Clear everything
  clearAll: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  extrasMap: {},
  setExtras: (id, extras) =>
    set((s) => ({ extrasMap: { ...s.extrasMap, [id]: extras } })),

  currentStages: [],
  pushStage: (event) =>
    set((s) => {
      const stages = s.currentStages.filter((e) => e.stage !== event.stage)
      return { currentStages: [...stages, event] }
    }),
  clearStages: () => set({ currentStages: [] }),

  error: null,
  setError: (msg) => set({ error: msg }),

  clearAll: () => set({ extrasMap: {}, currentStages: [], error: null }),
}))
