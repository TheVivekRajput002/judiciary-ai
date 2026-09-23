// Shared TypeScript types matching the backend models

export interface Document {
  id: string
  session_id: string
  original_filename: string
  file_type: string
  status: 'uploaded' | 'processing' | 'processed' | 'failed'
  error_message?: string
  page_count?: number
  case_name?: string
  uploaded_at: string
  processed_at?: string
}

export interface Citation {
  source_type: 'document' | 'web'
  document_filename?: string
  page_number?: string
  section?: string
  case_name?: string
  url?: string
  title?: string
  court_or_authority?: string
  excerpt?: string
}

export interface ConflictBlock {
  position_a: string
  sources_a: string[]
  position_b: string
  sources_b: string[]
  description: string
}

export interface Session {
  id: string
  title?: string
  created_at: string
  last_active_at: string
}

export interface ResearchEntity {
  id: string
  entity_type: 'case' | 'statute' | 'issue' | 'authority'
  name: string
  summary?: string
}

export type PipelineStage =
  | 'Understand'
  | 'Plan'
  | 'Retrieve'
  | 'Research'
  | 'Reason'
  | 'Synthesize'
  | 'Cite'
  | 'Remember'
  | 'Clarify'
  | 'InsufficientEvidence'

export interface StageEvent {
  stage: PipelineStage
  status: 'running' | 'done' | 'error'
  summary?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
}

// Per-message structured extras (stored in useChatStore)
export interface MessageExtras {
  citations?: Citation[]
  conflicts?: ConflictBlock[]
  routingMode?: string
  followUpSuggestions?: string[]
}
