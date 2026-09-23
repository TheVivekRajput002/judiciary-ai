import { useCallback, useRef } from 'react'
import { useDocumentStore } from '../store/useDocumentStore'

export function FileUploadZone({ sessionId }: { sessionId: string }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const addDocument = useDocumentStore((s) => s.addDocument)
  const updateDocument = useDocumentStore((s) => s.updateDocument)

  const upload = useCallback(async (file: File) => {
    const formData = new FormData()
    formData.append('file', file)

    const res = await fetch(`/api/documents?session_id=${sessionId}`, {
      method: 'POST',
      body: formData,
    })
    if (!res.ok) return
    const doc = await res.json()
    addDocument(doc)

    // Poll until processed or failed
    const poll = async () => {
      const r = await fetch(`/api/documents?session_id=${sessionId}`)
      if (!r.ok) return
      const docs = await r.json()
      const updated = docs.find((d: any) => d.id === doc.id)
      if (updated) updateDocument(doc.id, updated)
      if (updated?.status === 'uploaded' || updated?.status === 'processing') {
        setTimeout(poll, 2000)
      }
    }
    setTimeout(poll, 1500)
  }, [sessionId, addDocument, updateDocument])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) upload(file)
  }, [upload])

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) upload(file)
    e.target.value = ''
  }, [upload])

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      className="rounded-lg p-4 flex flex-col items-center gap-2 cursor-pointer transition-color"
      style={{
        border: '1.5px dashed var(--color-bg-border)',
        background: 'transparent',
      }}
      onMouseEnter={(e) => {
        ;(e.currentTarget as HTMLDivElement).style.borderColor = 'var(--color-accent)'
      }}
      onMouseLeave={(e) => {
        ;(e.currentTarget as HTMLDivElement).style.borderColor = 'var(--color-bg-border)'
      }}
    >
      <svg
        width="20" height="20" viewBox="0 0 24 24" fill="none"
        stroke="var(--color-accent)" strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round"
      >
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </svg>
      <span className="text-xs text-center" style={{ color: 'var(--color-text-muted)' }}>
        Drop a judgment or PDF
      </span>
      <input ref={inputRef} type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={handleChange} />
    </div>
  )
}
