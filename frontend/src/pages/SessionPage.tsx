import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

import { useChatStore } from '../store/useChatStore'
import { useDocumentStore } from '../store/useDocumentStore'
import { useResearchStore } from '../store/useResearchStore'
import { useSessionStore } from '../store/useSessionStore'

import { DocumentManager } from '../components/DocumentManager'
import { FindingsPanel } from '../components/FindingsPanel'
import { MessageBubble } from '../components/MessageBubble'
import { PipelineProgressIndicator } from '../components/PipelineProgressIndicator'
import { QueryInputBar } from '../components/QueryInputBar'

import type { Citation, ConflictBlock, StageEvent, ChatMessage } from '../types'

export function SessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const bottomRef = useRef<HTMLDivElement>(null)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isClearing, setIsClearing] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  const { pushStage, clearStages, clearAll, setExtras, setError, error } = useChatStore()
  const documents = useDocumentStore((s) => s.documents)
  const setDocuments = useDocumentStore((s) => s.setDocuments)
  const clearEntities = useResearchStore((s) => s.clearEntities)
  const setActiveSession = useSessionStore((s) => s.setActiveSession)

  // Load session & history on mount
  useEffect(() => {
    if (!sessionId) return
    fetch(`/api/sessions/${sessionId}`)
      .then((r) => {
        if (!r.ok) throw new Error('Session not found')
        return r.json()
      })
      .then((session) => {
        setActiveSession(session)
        if (session.messages && session.messages.length > 0) {
          const loaded: ChatMessage[] = session.messages.map((m: { id: string; role: 'user' | 'assistant'; content: string }) => ({
            id: m.id,
            role: m.role,
            content: m.content,
          }))
          setMessages(loaded)
        }
      })
      .catch(() => navigate('/'))

    fetch(`/api/documents?session_id=${sessionId}`)
      .then((r) => r.json())
      .then(setDocuments)
      .catch(() => {})
  }, [sessionId, navigate, setActiveSession, setDocuments])

  // Auto-scroll to bottom on message or stream changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isLoading])

  const handleSubmit = async () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading || !sessionId) return

    const userMsgId = `user-${Date.now()}`
    const assistantMsgId = `asst-${Date.now()}`

    const userMsg: ChatMessage = { id: userMsgId, role: 'user', content: trimmed }
    const initialAssistantMsg: ChatMessage = { id: assistantMsgId, role: 'assistant', content: '' }

    setMessages((prev) => [...prev, userMsg, initialAssistantMsg])
    setInput('')
    setIsLoading(true)
    setError(null)
    clearStages()
    pushStage({ stage: 'Understand', status: 'running' })

    const citations: Citation[] = []
    const conflicts: ConflictBlock[] = []
    let routingMode = ''

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: trimmed }),
      })

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}))
        throw new Error(errJson.detail || `Server returned ${res.status}`)
      }

      if (!res.body) {
        throw new Error('No response stream received from server')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let i = 0
        while (i < lines.length) {
          const line = lines[i]

          if (line.startsWith('event: stage')) {
            const nextLine = lines[i + 1] || ''
            if (nextLine.startsWith('data: ')) {
              try {
                const evt: StageEvent = JSON.parse(nextLine.slice(6))
                pushStage(evt)
              } catch {}
              i += 2
              continue
            }
          } else if (line.startsWith('event: citations')) {
            const nextLine = lines[i + 1] || ''
            if (nextLine.startsWith('data: ')) {
              try {
                const cits: Citation[] = JSON.parse(nextLine.slice(6))
                citations.push(...cits)
              } catch {}
              i += 2
              continue
            }
          } else if (line.startsWith('event: conflicts')) {
            const nextLine = lines[i + 1] || ''
            if (nextLine.startsWith('data: ')) {
              try {
                const confs: ConflictBlock[] = JSON.parse(nextLine.slice(6))
                conflicts.push(...confs)
              } catch {}
              i += 2
              continue
            }
          } else if (line.startsWith('event: done')) {
            const nextLine = lines[i + 1] || ''
            if (nextLine.startsWith('data: ')) {
              try {
                const d = JSON.parse(nextLine.slice(6))
                routingMode = d.routing_mode || ''
              } catch {}
              i += 2
              continue
            }
          } else if (line.startsWith('event: error')) {
            const nextLine = lines[i + 1] || ''
            if (nextLine.startsWith('data: ')) {
              try {
                const d = JSON.parse(nextLine.slice(6))
                setError(d.message)
              } catch {}
              i += 2
              continue
            }
          } else if (line.startsWith('0:')) {
            // Text chunk
            try {
              const textChunk = JSON.parse(line.slice(2))
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantMsgId ? { ...m, content: m.content + textChunk } : m
                )
              )
            } catch {}
          }
          i++
        }
      }

      // Store structured metadata for this assistant message
      setExtras(assistantMsgId, { citations, conflicts, routingMode })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err)
      setError(msg)
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId && !m.content
            ? { ...m, content: `Error generating response: ${msg}` }
            : m
        )
      )
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearChat = async () => {
    if (!sessionId || messages.length === 0 || isLoading) return
    setIsClearing(true)
    try {
      await fetch(`/api/sessions/${sessionId}/messages`, { method: 'DELETE' })
      setMessages([])
      clearAll()
      clearEntities()
    } catch (e) {
      console.error('Failed to clear chat:', e)
    } finally {
      setIsClearing(false)
    }
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside
        className={`shrink-0 flex flex-col overflow-y-auto transition-all duration-300 ease-in-out ${
          isSidebarOpen
            ? 'w-72 md:w-80 p-4 opacity-100'
            : 'w-0 p-0 opacity-0 overflow-hidden border-r-0 pointer-events-none'
        }`}
        style={{
          borderRight: isSidebarOpen ? '1px solid var(--color-bg-border)' : 'none',
          background: 'var(--color-bg-surface)',
        }}
      >
        {/* Sidebar Header: Logo & Collapse Button */}
        <div className="flex items-center justify-between pt-1 pb-2 min-w-[250px]">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold tracking-tight" style={{ color: 'var(--color-text-primary)' }}>
              Lexi<span style={{ color: 'var(--color-accent)' }}>AI</span>
            </span>
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--color-accent)' }} />
          </div>
          <button
            onClick={() => setIsSidebarOpen(false)}
            className="p-1.5 rounded-lg transition-colors text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-elevated)]"
            title="Collapse document sidebar"
            aria-label="Collapse document sidebar"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="9" y1="3" x2="9" y2="21" />
              <path d="M15 9l-3 3 3 3" />
            </svg>
          </button>
        </div>

        {/* Sidebar Body */}
        <div className="min-w-[250px] flex flex-col gap-6">
          <DocumentManager sessionId={sessionId!} />
          <FindingsPanel />
        </div>
      </aside>

      {/* ── Main Panel ──────────────────────────────────── */}
      <main className="flex flex-col flex-1 overflow-hidden">
        {/* Header */}
        <header
          className="flex items-center justify-between px-6 py-3 shrink-0"
          style={{ borderBottom: '1px solid var(--color-bg-border)' }}
        >
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsSidebarOpen((prev) => !prev)}
              className="flex items-center gap-2 text-xs px-2.5 py-1.5 rounded-lg transition-all"
              style={{
                border: '1px solid var(--color-bg-border)',
                color: isSidebarOpen ? 'var(--color-text-secondary)' : 'var(--color-accent)',
                background: isSidebarOpen ? 'transparent' : 'var(--color-accent-soft)',
                borderColor: isSidebarOpen ? 'var(--color-bg-border)' : 'var(--color-accent)',
              }}
              title={isSidebarOpen ? 'Collapse document sidebar' : 'Open document sidebar'}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="9" y1="3" x2="9" y2="21" />
                <path d={isSidebarOpen ? "M15 9l-3 3 3 3" : "M13 15l3-3-3-3"} />
              </svg>
              <span>{isSidebarOpen ? 'Hide Documents' : 'Documents'}</span>
              {documents.length > 0 && (
                <span
                  className="px-1.5 py-0.2 rounded-full text-[10px] font-semibold"
                  style={{
                    background: isSidebarOpen ? 'var(--color-bg-elevated)' : 'var(--color-accent)',
                    color: isSidebarOpen ? 'var(--color-accent)' : '#000',
                  }}
                >
                  {documents.length}
                </span>
              )}
            </button>
            <span className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
              Research Session
            </span>
          </div>

          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={handleClearChat}
                disabled={isLoading || isClearing}
                className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg transition-all disabled:opacity-50"
                style={{
                  border: '1px solid var(--color-bg-border)',
                  color: 'var(--color-text-secondary)',
                  background: 'transparent',
                }}
                onMouseEnter={(e) => {
                  ;(e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-error)'
                  ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--color-error)'
                  ;(e.currentTarget as HTMLButtonElement).style.background = 'rgba(240,62,62,0.08)'
                }}
                onMouseLeave={(e) => {
                  ;(e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-bg-border)'
                  ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text-secondary)'
                  ;(e.currentTarget as HTMLButtonElement).style.background = 'transparent'
                }}
                title="Clear all messages in this chat"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                  <path d="M10 11v6" />
                  <path d="M14 11v6" />
                  <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                </svg>
                <span>{isClearing ? 'Clearing…' : 'Clear Chat'}</span>
              </button>
            )}

            <button
              onClick={async () => {
                const res = await fetch('/api/sessions', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({}),
                })
                const session = await res.json()
                navigate(`/session/${session.id}`)
              }}
              className="text-xs px-3 py-1.5 rounded-lg transition-all"
              style={{
                border: '1px solid var(--color-bg-border)',
                color: 'var(--color-text-secondary)',
                background: 'transparent',
              }}
              onMouseEnter={(e) => {
                ;(e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-accent)'
                ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--color-accent)'
              }}
              onMouseLeave={(e) => {
                ;(e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--color-bg-border)'
                ;(e.currentTarget as HTMLButtonElement).style.color = 'var(--color-text-secondary)'
              }}
            >
              New Session
            </button>
          </div>
        </header>

        {/* Pipeline Progress */}
        <PipelineProgressIndicator />

        {/* Error Banner */}
        {error && (
          <div
            className="mx-6 mt-3 rounded-lg px-4 py-2 text-sm flex items-center justify-between"
            style={{ background: 'rgba(240,62,62,0.1)', border: '1px solid var(--color-error)', color: 'var(--color-error)' }}
          >
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-xs underline ml-4">Dismiss</button>
          </div>
        )}

        {/* Conversation Transcript */}
        <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-6">
          {messages.length === 0 && (
            <div className="flex-1 flex flex-col items-center justify-center gap-3">
              <div className="text-4xl" style={{ color: 'var(--color-bg-border)' }}>⚖</div>
              <p className="text-sm text-center max-w-xs" style={{ color: 'var(--color-text-muted)' }}>
                Upload a legal document or ask a research question to get started.
              </p>
            </div>
          )}
          {messages.map((m) => (
            <MessageBubble key={m.id} message={m} />
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Query Input */}
        <div className="px-6 pb-6 pt-2 shrink-0">
          <QueryInputBar
            value={input}
            onChange={setInput}
            onSubmit={handleSubmit}
            isLoading={isLoading}
          />
          <p className="text-center text-xs mt-2" style={{ color: 'var(--color-text-muted)' }}>
            LexiAI researches Indian law. Not legal advice.
          </p>
        </div>
      </main>
    </div>
  )
}
