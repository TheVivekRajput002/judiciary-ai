import { useDocumentStore } from '../store/useDocumentStore'
import { FileUploadZone } from './FileUploadZone'

const STATUS_COLORS: Record<string, string> = {
  uploaded: 'var(--color-text-muted)',
  processing: 'var(--color-info)',
  processed: 'var(--color-success)',
  failed: 'var(--color-error)',
}

const STATUS_LABELS: Record<string, string> = {
  uploaded: 'Queued',
  processing: 'Processing…',
  processed: 'Ready',
  failed: 'Failed',
}

export function DocumentManager({ sessionId }: { sessionId: string }) {
  const documents = useDocumentStore((s) => s.documents)
  const removeDocument = useDocumentStore((s) => s.removeDocument)

  const handleDelete = async (id: string) => {
    removeDocument(id) // optimistic
    await fetch(`/api/documents/${id}`, { method: 'DELETE' })
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        className="text-xs uppercase tracking-widest"
        style={{ color: 'var(--color-text-muted)' }}
      >
        Documents
      </div>

      <FileUploadZone sessionId={sessionId} />

      {documents.length > 0 && (
        <div className="flex flex-col gap-1 mt-1">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center gap-2 rounded px-2 py-2 group transition-color"
              style={{ background: 'transparent' }}
              onMouseEnter={(e) => {
                ;(e.currentTarget as HTMLDivElement).style.background = 'var(--color-bg-elevated)'
              }}
              onMouseLeave={(e) => {
                ;(e.currentTarget as HTMLDivElement).style.background = 'transparent'
              }}
            >
              {/* File icon */}
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
                stroke="var(--color-text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>

              <div className="flex-1 min-w-0">
                <div
                  className="text-xs truncate"
                  style={{ color: 'var(--color-text-primary)' }}
                  title={doc.original_filename}
                >
                  {doc.original_filename}
                </div>
                <div className="text-xs" style={{ color: STATUS_COLORS[doc.status] }}>
                  {STATUS_LABELS[doc.status]}
                  {doc.status === 'processing' && (
                    <span className="ml-1 animate-gold-pulse" style={{ color: 'var(--color-info)' }}>●</span>
                  )}
                </div>
              </div>

              {/* Delete button */}
              <button
                onClick={() => handleDelete(doc.id)}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded"
                style={{ color: 'var(--color-text-muted)' }}
                title="Remove"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6l-1 14H6L5 6" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
