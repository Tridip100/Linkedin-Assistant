const PRIORITY_CLASS = {
  HIGH:   'badge-high',
  MEDIUM: 'badge-medium',
  LOW:    'badge-low',
}

export default function Dashboard({ data, goTo }) {
  const stats   = data.dashboard_stats || {}
  const targets = data.target_list     || []

  const high   = targets.filter(p => p.priority === 'HIGH').length
  const medium = targets.filter(p => p.priority === 'MEDIUM').length
  const low    = targets.filter(p => p.priority === 'LOW').length

  return (
    <div className="space-y-6 pb-12">
      <div>
        <h2 className="font-display text-3xl font-bold text-white/90">Pipeline Results</h2>
        <p className="text-white/30 text-sm mt-1">Here's what the pipeline found for you.</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { icon: '🏢', label: 'Companies found',   value: stats.companies_found   || 0 },
          { icon: '👥', label: 'People discovered', value: stats.people_found      || 0 },
          { icon: '✨', label: 'After enrichment',  value: stats.after_enrichment  || 0 },
          { icon: '📊', label: 'After scoring',     value: stats.after_scoring     || 0 },
          { icon: '🎯', label: 'Final targets',     value: stats.final_targets     || 0 },
          { icon: '📧', label: 'Emails found',      value: stats.emails_found      || 0 },
        ].map(s => (
          <div key={s.label} className="glass rounded-xl p-4 space-y-1">
            <span className="text-xl">{s.icon}</span>
            <p className="font-display text-2xl font-bold text-white">{s.value}</p>
            <p className="text-xs text-white/30">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Priority breakdown */}
      <div className="glass rounded-xl p-5 space-y-4">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider font-display">Priority Breakdown</h3>
        {[
          { label: '🔴 HIGH',   count: high,   pct: targets.length ? (high   / targets.length) * 100 : 0 },
          { label: '🟡 MEDIUM', count: medium, pct: targets.length ? (medium / targets.length) * 100 : 0 },
          { label: '🟢 LOW',    count: low,    pct: targets.length ? (low    / targets.length) * 100 : 0 },
        ].map(row => (
          <div key={row.label} className="flex items-center gap-4">
            <span className="text-xs text-white/40 w-24 shrink-0">{row.label}</span>
            <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
              <div className="h-full score-bar rounded-full transition-all duration-1000"
                style={{ width: `${row.pct}%` }} />
            </div>
            <span className="text-xs font-mono text-white/35 w-4 shrink-0">{row.count}</span>
          </div>
        ))}
      </div>

      {/* Target list */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider font-display">Your Targets</h3>
        {targets.map((p, i) => (
          <div key={i} className="glass rounded-xl px-4 py-3 flex items-center gap-3 hover:border-blue-500/15 transition-all">
            <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-800/40 to-blue-600/20 flex items-center justify-center text-xs font-bold text-blue-300 shrink-0 font-display">
              {p.name?.[0]}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-white/80 font-medium truncate">{p.name}</p>
              <p className="text-xs text-white/25 truncate">{p.title} @ {p.company}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {p.priority && (
                <span className={`text-[9px] px-2 py-0.5 rounded-full font-semibold ${PRIORITY_CLASS[p.priority] || ''}`}>
                  {p.priority}
                </span>
              )}
              {p.email_hint   && <span className="tag">Email</span>}
              {p.linkedin_url && <span className="tag">LinkedIn</span>}
              <span className="text-xs font-mono text-white/20">{p.final_score}</span>
            </div>
          </div>
        ))}
      </div>

      {/* CTA */}
      <div className="glass-blue rounded-2xl p-6 space-y-4">
        <div>
          <h3 className="font-display font-bold text-white text-lg">Generate personalized messages?</h3>
          <p className="text-white/35 text-sm mt-1">
            I'll write LinkedIn requests, DMs, cold emails and follow-ups for each contact — personalized to their profile.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => goTo('profile')}
            className="btn-moon rounded-xl px-6 py-3 text-sm font-semibold font-display"
          >
            Yes, Generate Messages →
          </button>
          <button className="glass rounded-xl px-6 py-3 text-sm text-white/35 hover:text-white/60 transition-all">
            Save & Exit
          </button>
        </div>
      </div>
    </div>
  )
}
