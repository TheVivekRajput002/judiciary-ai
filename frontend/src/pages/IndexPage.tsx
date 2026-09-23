import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSessionStore } from '../store/useSessionStore'

export function IndexPage() {
  const navigate = useNavigate()
  const activeSessionId = useSessionStore((s) => s.activeSessionId)

  useEffect(() => {
    const go = async () => {
      // Resume last session if exists
      if (activeSessionId) {
        const res = await fetch(`/api/sessions/${activeSessionId}`)
        if (res.ok) {
          navigate(`/session/${activeSessionId}`, { replace: true })
          return
        }
      }
      // Otherwise create a new session
      const res = await fetch('/api/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const session = await res.json()
      navigate(`/session/${session.id}`, { replace: true })
    }
    go()
  }, [])

  return (
    <div className="h-screen flex items-center justify-center" style={{ color: 'var(--color-text-muted)' }}>
      <span className="text-sm animate-gold-pulse" style={{ color: 'var(--color-accent)' }}>
        Starting session…
      </span>
    </div>
  )
}
