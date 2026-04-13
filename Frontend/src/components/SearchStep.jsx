import { useState, useRef, useEffect } from 'react'
import { search } from '../api/client'

const STEPS = [
  {
    id:     1,
    label:  'Company Discovery',
    desc:   'Scanning the web for matching companies',
    detail: 'Searching LinkedIn, Wellfound, startup directories...',
  },
  {
    id:     2,
    label:  'People Finder',
    desc:   'Finding founders and decision makers',
    detail: 'Identifying CTOs, founders and key contacts...',
  },
  {
    id:     3,
    label:  'Profile Enrichment',
    desc:   'Deep-diving each profile and company',
    detail: 'Gathering hooks, emails, recent activity...',
  },
]

const EXAMPLES = [
  'ML internships Kolkata remote',
  'Backend engineer Bangalore hybrid',
  'DevOps startups India full-time',
  'AI product roles remote',
]

function TypingText({ text, active }) {
  const [shown, setShown] = useState('')
  useEffect(() => {
    if (!active) { setShown(text); return }
    setShown('')
    let i = 0
    const iv = setInterval(() => {
      if (i < text.length) { setShown(text.slice(0, ++i)) }
      else clearInterval(iv)
    }, 20)
    return () => clearInterval(iv)
  }, [text, active])
  return <>{shown}{active && <span className="opacity-60 animate-pulse">|</span>}</>
}

function StepCard({ step, event }) {
  const status = event?.status || 'idle'
  const isRun  = status === 'running'
  const isDone = status === 'done'
  const isErr  = status === 'error'

  return (
    <div className={`rounded-xl border transition-all duration-500 overflow-hidden ${
      isRun  ? 'step-active'                               :
      isDone ? 'bg-emerald-900/10 border-emerald-500/20'  :
      isErr  ? 'bg-red-900/10 border-red-500/20'          :
      'glass border-white/5'
    }`}>
      <div className="flex items-center gap-3 px-4 py-3">

        {/* Icon */}
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
          isRun  ? 'bg-blue-500/15'    :
          isDone ? 'bg-emerald-500/15' :
          isErr  ? 'bg-red-500/15'     :
          'bg-white/5'
        }`}>
          {isRun  ? <div className="w-3 h-3 border-2 border-blue-300 border-t-transparent rounded-full animate-spin" /> :
           isDone ? <span className="text-emerald-400 text-xs font-bold">✓</span> :
           isErr  ? <span className="text-red-400 text-xs">✕</span> :
           <span className="text-white/15 text-xs font-mono">{step.id}</span>}
        </div>

        {/* Text */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-sm font-semibold font-display ${
              isRun  ? 'text-blue-200'    :
              isDone ? 'text-emerald-300' :
              isErr  ? 'text-red-300'     :
              'text-white/20'
            }`}>
              {step.label}
            </span>
            {isRun && (
              <span className="flex items-center gap-1 text-[9px] px-2 py-0.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-300">
                <span className="w-1 h-1 rounded-full bg-blue-400 animate-pulse" />
                LIVE
              </span>
            )}
            {isDone && event?.msg && (
              <span className="text-[10px] text-emerald-400/50 font-mono">
                {event.msg}
              </span>
            )}
          </div>
          <p className="text-xs mt-0.5 text-white/25 truncate">
            {isRun
              ? <TypingText text={step.detail} active={true} />
              : isDone
              ? <span className="text-emerald-400/40"><TypingText text={event?.msg || step.desc} active={false} /></span>
              : step.desc}
          </p>
        </div>

        {/* Dots */}
        {isRun && (
          <div className="flex gap-1 shrink-0">
            {[0,1,2].map(i => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
                style={{ animationDelay: `${i*150}ms` }} />
            ))}
          </div>
        )}
      </div>

      {/* Progress bar */}
      {isRun && (
        <div className="h-0.5 bg-white/5">
          <div className="h-full progress-shimmer rounded-full" style={{ width: '70%' }} />
        </div>
      )}
    </div>
  )
}

export default function SearchStep({ setSessionId, setData, goTo }) {
  const [query,     setQuery]     = useState('')
  const [error,     setError]     = useState('')
  const [searching, setSearching] = useState(false)
  const [progress,  setProgress]  = useState([])
  const wsRef = useRef(null)

  const connectWS = (sid) => {
    wsRef.current?.close()
    const WS_BASE = import.meta.env.VITE_API_URL.replace("https", "wss").replace("/api", "")
    const ws = new WebSocket(`${WS_BASE}/ws/${sid}`)

    ws.onopen    = () => console.log('[WS] connected')
    ws.onerror   = (e) => console.error('[WS] error', e)
    ws.onclose   = () => console.log('[WS] closed')
    ws.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data)
        console.log('[WS]', ev)
        setProgress(prev => {
          const i = prev.findIndex(p => p.agent === ev.agent)
          if (i >= 0) { const u = [...prev]; u[i] = ev; return u }
          return [...prev, ev]
        })
      } catch {}
    }
    wsRef.current = ws
  }

  const handleSearch = async () => {
    if (!query.trim()) { setError('Enter what you are looking for'); return }
    setError('')
    setSearching(true)
    setProgress([])

    try {
      const API_BASE = import.meta.env.VITE_API_URL

      // 1. Create session
      const sRes = await fetch(`${API_BASE}/session/new`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }
      })
      if (!sRes.ok) { setError('Backend unreachable — is uvicorn running on port 8000?'); return }
      const { session_id } = await sRes.json()
      console.log('[session]', session_id)

      setSessionId(session_id)

      // 2. Connect WebSocket BEFORE search
      connectWS(session_id)

      // 3. Small delay for WS handshake
      await new Promise(r => setTimeout(r, 600))

      // 4. Run search
      const res = await search(query.trim(), session_id)
      const { data, error: err } = res.data

      if (err) { setError(err); return }

      setData(data)
      await new Promise(r => setTimeout(r, 700))
      goTo('results')

    } catch (e) {
      console.error('[search]', e)
      setError(
        e.code === 'ERR_NETWORK'
          ? 'Cannot reach backend. Make sure uvicorn is running on port 8000.'
          : e.response?.data?.detail || 'Something went wrong.'
      )
    } finally {
      setSearching(false)
    }
  }

  const getEvent = (id) => progress.find(p => p.agent === id)
  const showProgress = searching || progress.length > 0

  return (
    <div className="flex flex-col items-center gap-8 pt-6 pb-12">

      {/* Hero */}
      <div className="text-center space-y-4 max-w-2xl">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass-blue text-xs text-blue-300 mb-2">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
          AI-powered outreach intelligence
        </div>
        <h1 className="font-display text-6xl font-bold leading-tight shimmer-text">
          Find anyone.<br />Reach everyone.
        </h1>
        <p className="text-white/30 text-lg">
          Discover companies, uncover decision makers,<br />craft outreach that actually lands.
        </p>
      </div>

      {/* Search */}
      <div className="w-full max-w-2xl space-y-3">
        <div className="flex gap-2">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !searching && handleSearch()}
            disabled={searching}
            placeholder="e.g. ML internships Kolkata remote"
            className="flex-1 glass rounded-xl px-5 py-4 text-white placeholder-white/20 text-sm outline-none disabled:opacity-40 transition-all"
          />
          <button
            onClick={handleSearch}
            disabled={searching}
            className="btn-moon rounded-xl px-7 py-4 text-sm font-semibold font-display disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
          >
            {searching
              ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              : 'Search'}
          </button>
        </div>

        {error && (
          <div className="flex gap-2 items-center text-red-300 text-xs px-4 py-2.5 rounded-xl bg-red-900/15 border border-red-500/20">
            <span>⚠</span> {error}
          </div>
        )}

        {/* Example chips */}
        {!showProgress && (
          <div className="flex flex-wrap gap-2">
            {EXAMPLES.map(ex => (
              <button key={ex} onClick={() => setQuery(ex)}
                className="text-[11px] px-3 py-1.5 rounded-full glass text-white/30 hover:text-blue-300 hover:border-blue-500/30 transition-all">
                {ex}
              </button>
            ))}
          </div>
        )}

        {/* Progress steps */}
        {showProgress && (
          <div className="space-y-2 pt-1">
            {STEPS.map(step => (
              <StepCard key={step.id} step={step} event={getEvent(step.id)} />
            ))}

            <div className="text-center pt-1">
              {searching && (
                <p className="text-xs text-white/20 animate-pulse">
                  This may take 1–3 minutes. Please don't close this tab.
                </p>
              )}
              {getEvent('all')?.status === 'complete' && (
                <p className="text-xs text-emerald-400/60">✓ All done — loading results...</p>
              )}
              {getEvent('all')?.status === 'error' && (
                <p className="text-xs text-red-400/60">⚠ {getEvent('all')?.msg}</p>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Feature cards */}
      {!showProgress && (
        <div className="grid grid-cols-3 gap-3 max-w-2xl w-full">
          {[
            { icon: '🎯', title: 'Precision Targeting',  desc: 'Finds exactly the right people for your goal' },
            { icon: '🔍', title: 'Deep Intelligence',    desc: 'Enriches profiles with hooks and real context' },
            { icon: '✉️', title: 'Human-sounding Copy',  desc: 'Messages that reference specifics, not templates' },
          ].map(f => (
            <div key={f.title} className="glass rounded-xl p-4 space-y-2 hover:border-blue-500/15 transition-all">
              <span className="text-lg">{f.icon}</span>
              <p className="text-xs font-semibold font-display text-white/60">{f.title}</p>
              <p className="text-xs text-white/20 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
