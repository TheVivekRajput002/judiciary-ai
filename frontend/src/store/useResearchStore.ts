import { create } from 'zustand'
import type { ResearchEntity } from '../types'

interface ResearchState {
  entities: ResearchEntity[]
  setEntities: (entities: ResearchEntity[]) => void
  addEntity: (entity: ResearchEntity) => void
  clearEntities: () => void
}

export const useResearchStore = create<ResearchState>((set) => ({
  entities: [],
  setEntities: (entities) => set({ entities }),
  addEntity: (entity) =>
    set((s) => ({
      entities: s.entities.some((e) => e.id === entity.id)
        ? s.entities
        : [...s.entities, entity],
    })),
  clearEntities: () => set({ entities: [] }),
}))
