import type { Citation } from '../types'

function DocumentCitationCard({ c }: { c: Citation }) {
  return (
    <div
      className="rounded p-3 text-xs font-mono transition-all"
      style={{
        background: 'var(--color-bg-elevated)',
        borderLeft: '2px solid var(--color-accent)',
        color: 'var(--color-text-secondary)',
      }}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <div style={{ color: 'var(--color-text-primary)', fontWeight: 600 }} className="truncate">
          📄 {c.case_name || c.document_filename}
        </div>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-bg-border)] text-[var(--color-text-muted)] shrink-0 font-sans">
          Document
        </span>
      </div>
      {c.document_filename && <div>Doc: {c.document_filename}</div>}
      {c.page_number && <div>Page: {c.page_number}</div>}
      {c.section && <div>§ {c.section}</div>}
      {c.excerpt && (
        <div
          className="mt-2 italic"
          style={{ color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-bg-border)', paddingTop: 6 }}
        >
          "{c.excerpt}"
        </div>
      )}
    </div>
  )
}

function WebCitationCard({ c }: { c: Citation }) {
  return (
    <div
      className="rounded p-3 text-xs font-mono transition-all"
      style={{
        background: 'var(--color-bg-elevated)',
        borderLeft: '2px solid var(--color-info)',
        color: 'var(--color-text-secondary)',
      }}
    >
      <div className="flex items-center justify-between gap-2 mb-1">
        <a
          href={c.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: 'var(--color-accent)', fontWeight: 600, textDecoration: 'none' }}
          className="hover:underline flex items-center gap-1.5 truncate"
        >
          <span>🌐</span>
          <span className="truncate">{c.title || c.url}</span>
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="shrink-0"
          >
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
        </a>
        {c.court_or_authority && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-bg-border)] text-[var(--color-info)] shrink-0 font-sans font-medium">
            {c.court_or_authority}
          </span>
        )}
      </div>
      {c.url && (
        <div className="text-[11px] truncate opacity-70 mb-1" style={{ color: 'var(--color-text-muted)' }}>
          {c.url}
        </div>
      )}
      {c.excerpt && (
        <div
          className="mt-1.5 italic"
          style={{ color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-bg-border)', paddingTop: 6 }}
        >
          "{c.excerpt}"
        </div>
      )}
    </div>
  )
}

export function CitationsList({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null

  return (
    <div className="mt-4 pt-3" style={{ borderTop: '1px solid var(--color-bg-border)' }}>
      <div
        className="text-xs uppercase tracking-widest mb-2 font-semibold flex items-center gap-2"
        style={{ color: 'var(--color-text-muted)' }}
      >
        <span>Sources &amp; Citations</span>
        <span
          className="text-[10px] px-1.5 py-0.2 rounded-full"
          style={{ background: 'var(--color-bg-border)', color: 'var(--color-text-secondary)' }}
        >
          {citations.length}
        </span>
      </div>
      <div className="flex flex-col gap-2">
        {citations.map((c, i) =>
          c.source_type === 'document' ? (
            <DocumentCitationCard key={i} c={c} />
          ) : (
            <WebCitationCard key={i} c={c} />
          )
        )}
      </div>
    </div>
  )
}
