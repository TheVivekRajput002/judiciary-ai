import { useRef, type KeyboardEvent } from 'react'

interface Props {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  isLoading: boolean
}

export function QueryInputBar({ value, onChange, onSubmit, isLoading }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!isLoading && value.trim()) onSubmit()
    }
  }

  return (
    <div
      className="flex items-end gap-3 rounded-xl p-3"
      style={{
        background: 'var(--color-bg-elevated)',
        border: '1px solid var(--color-bg-border)',
      }}
    >
      <textarea
        ref={textareaRef}
        id="query-input"
        rows={1}
        value={value}
        onChange={(e) => {
          onChange(e.target.value)
          // Auto-resize
          e.target.style.height = 'auto'
          e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
        }}
        onKeyDown={handleKeyDown}
        disabled={isLoading}
        placeholder="Ask a legal research question regarding Indian law or uploaded documents…"
        className="flex-1 resize-none bg-transparent outline-none text-sm leading-relaxed"
        style={{
          color: 'var(--color-text-primary)',
          caretColor: 'var(--color-accent)',
          minHeight: '24px',
          maxHeight: '160px',
        }}
      />

      <button
        id="submit-query"
        onClick={onSubmit}
        disabled={isLoading || !value.trim()}
        className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all"
        style={{
          background: isLoading || !value.trim() ? 'var(--color-bg-border)' : 'var(--color-accent)',
          color: isLoading || !value.trim() ? 'var(--color-text-muted)' : '#0a0a0b',
          cursor: isLoading || !value.trim() ? 'not-allowed' : 'pointer',
        }}
        title="Send (Enter)"
      >
        {isLoading ? (
          <span className="animate-gold-pulse text-xs">●</span>
        ) : (
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        )}
      </button>
    </div>
  )
}
