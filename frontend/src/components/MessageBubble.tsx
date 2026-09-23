import ReactMarkdown from 'react-markdown'
import type { ChatMessage } from '../types'
import { useChatStore } from '../store/useChatStore'
import { CitationsList } from './CitationsList'
import { ConflictNotice } from './ConflictNotice'

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end animate-fade-up">
      <div
        className="max-w-xl rounded-2xl px-4 py-3 text-sm"
        style={{
          background: 'var(--color-bg-elevated)',
          color: 'var(--color-text-primary)',
          border: '1px solid var(--color-bg-border)',
        }}
      >
        {content}
      </div>
    </div>
  )
}

function AssistantBubble({ message }: { message: ChatMessage }) {
  const extras = useChatStore((s) => s.extrasMap[message.id])
  const isStreaming = message.content.endsWith('▋')
  const content = isStreaming ? message.content.slice(0, -1) : message.content

  return (
    <div className="animate-fade-up">
      {/* LexiAI label */}
      <div className="flex items-center gap-2 mb-2">
        <div
          className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold"
          style={{ background: 'var(--color-accent-soft)', color: 'var(--color-accent)', border: '1px solid var(--color-accent)' }}
        >
          L
        </div>
        <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
          LexiAI
        </span>
        {extras?.routingMode && (
          <span
            className="text-xs px-2 py-0.5 rounded-full capitalize"
            style={{ background: 'var(--color-accent-soft)', color: 'var(--color-accent)' }}
          >
            {extras.routingMode}
          </span>
        )}
      </div>

      <div
        className="rounded-xl p-4"
        style={{
          background: 'var(--color-bg-surface)',
          border: '1px solid var(--color-bg-border)',
        }}
      >
        {/* Answer content with markdown rendering */}
        <div
          className="prose prose-sm max-w-none text-sm leading-relaxed"
          style={{ color: 'var(--color-text-primary)' }}
        >
          <ReactMarkdown
            components={{
              h2: ({ children }) => (
                <h2 className="text-sm font-semibold mt-4 mb-1" style={{ color: 'var(--color-text-primary)' }}>
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-sm font-medium mt-3 mb-1" style={{ color: 'var(--color-text-secondary)' }}>
                  {children}
                </h3>
              ),
              ul: ({ children }) => <ul className="list-disc pl-4 space-y-1 my-2">{children}</ul>,
              li: ({ children }) => <li className="text-sm" style={{ color: 'var(--color-text-primary)' }}>{children}</li>,
              strong: ({ children }) => <strong style={{ color: 'var(--color-text-primary)', fontWeight: 600 }}>{children}</strong>,
              blockquote: ({ children }) => (
                <blockquote
                  className="pl-3 my-2 italic text-xs"
                  style={{ borderLeft: '2px solid var(--color-accent)', color: 'var(--color-text-secondary)' }}
                >
                  {children}
                </blockquote>
              ),
              p: ({ children }) => <p className="mb-2 leading-relaxed">{children}</p>,
              a: ({ href, children }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-semibold underline underline-offset-2 transition-opacity hover:opacity-80"
                  style={{ color: 'var(--color-accent)' }}
                >
                  <span>{children}</span>
                  <svg
                    width="11"
                    height="11"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="opacity-75 inline"
                  >
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                    <polyline points="15 3 21 3 21 9" />
                    <line x1="10" y1="14" x2="21" y2="3" />
                  </svg>
                </a>
              ),
            }}
          >
            {content}
          </ReactMarkdown>
          {isStreaming && (
            <span className="animate-blink ml-0.5" style={{ color: 'var(--color-accent)' }}>▋</span>
          )}
        </div>

        {/* Citations */}
        {extras?.citations && extras.citations.length > 0 && (
          <CitationsList citations={extras.citations} />
        )}

        {/* Conflicts */}
        {extras?.conflicts && extras.conflicts.length > 0 && (
          <ConflictNotice conflicts={extras.conflicts} />
        )}

        {/* Follow-up chips */}
        {extras?.followUpSuggestions && extras.followUpSuggestions.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {extras.followUpSuggestions.map((s, i) => (
              <button
                key={i}
                className="text-xs px-3 py-1 rounded-full transition-all hover:border-[var(--color-accent)]"
                style={{
                  background: 'var(--color-bg-elevated)',
                  color: 'var(--color-text-secondary)',
                  border: '1px solid var(--color-bg-border)',
                }}
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'user') return <UserBubble content={message.content} />
  return <AssistantBubble message={message} />
}
