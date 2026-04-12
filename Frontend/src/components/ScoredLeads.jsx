import { useState } from 'react'
import { runTargeting } from '../api/client'

const PRIORITY_CLASS = {
  HIGH:   'badge-high',
  MEDIUM: 'badge-medium',
  LOW:    'badge-low',
}

export default function ScoredLeads({ data, sessionId, setData, goTo }) {
  const scored          = data.scored_leads || []
  const [loading, setLoading] = useState(false)
  const [show, setShow]       = useState(10)

  const handleNext = async () => {
    setLoading(true)
    try {
      const res = await runTargeting(sessionId)
      setData(prev => ({ ...prev, ...res.data.data }))
      goTo('dashboard')
    } catch (e) {
      console.error('[target]', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="font-display text-3xl font-bold text-white/90">Ranked Leads</h2>
          <p className="text-white/30 text-sm mt-1">{scored.length} contacts scored by your priorities</p>
        </div>
        <select
          value={show}
          onChange={e => setShow(Number(e.target.value))}
          className="glass rounded-lg px-3 py-2 text-xs text-white/50 outline-none"
        >
          {[5, 10, 15, scored.length].map(n => (
            <option key={n} value={n} className="bg-gray-900">Show {n}</option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        {scored.slice(0, show).map((p, i) => {
          const score = p.final_score || 0
          return (
            <div key={i} className="glass rounded-xl p-4 hover:border-blue-500/15 transition-all">
              <div className="flex items-center gap-3">
                <span className="text-white/20 text-sm font-mono w-6 shrink-0">#{i+1}</span>

                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-800/40 to-blue-600/20 flex items-center justify-center text-xs font-bold text-blue-300 shrink-0 font-display">
                  {p.name?.[0]}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-semibold text-sm text-white/90 font-display">{p.name}</p>
                    {p.priority && (
                      <span className={`text-[9px] px-2 py-0.5 rounded-full font-semibold ${PRIORITY_CLASS[p.priority] || ''}`}>
                        {p.priority}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-white/25 truncate mt-0.5">{p.title} @ {p.company}</p>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <div className="w-20 h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className="score-bar h-full" style={{ width: `${score}%` }} />
                  </div>
                  <span className="text-xs text-white/35 font-mono w-10 text-right">{score}/100</span>
                </div>
              </div>

              {p.best_hook && (
                <p className="text-xs text-white/18 mt-2 ml-14 truncate">
                  💡 {p.best_hook}
                </p>
              )}
            </div>
          )
        })}
      </div>

      <div className="flex justify-end pt-2">
        <button
          onClick={handleNext}
          disabled={loading}
          className="btn-moon rounded-xl px-8 py-3 text-sm font-semibold font-display disabled:opacity-40"
        >
          {loading
            ? <span className="flex items-center gap-2"><div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Building list...</span>
            : 'Build Target List →'}
        </button>
      </div>
    </div>
  )
}
