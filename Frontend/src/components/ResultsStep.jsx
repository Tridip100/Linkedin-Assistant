import { getQuestions } from '../api/client'

export default function ResultsStep({ data, sessionId, setData, goTo }) {
  const { companies = [], enriched_people = [], intent = {} } = data

  const handleNext = async () => {
    try {
      const res = await getQuestions(sessionId)
      setData(prev => ({ ...prev, questions: res.data.data.questions }))
      goTo('interview')
    } catch (e) {
      console.error('[questions]', e)
    }
  }

  return (
    <div className="space-y-6 pb-12">

      {/* Header */}
      <div className="space-y-3">
        <div className="flex flex-wrap gap-2">
          {[intent.role, intent.opportunity_type, intent.location, intent.work_mode]
            .filter(Boolean).map(tag => (
              <span key={tag} className="tag">{tag}</span>
            ))}
        </div>
        <h2 className="font-display text-3xl font-bold text-white/90">Results</h2>
        <p className="text-white/30 text-sm">Found {companies.length} companies and {enriched_people.length} contacts</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Companies',  value: companies.length,                                             icon: '🏢' },
          { label: 'People',     value: enriched_people.length,                                       icon: '👤' },
          { label: 'With Links', value: enriched_people.filter(p => p.linkedin_url).length,           icon: '🔗' },
        ].map(s => (
          <div key={s.label} className="glass rounded-xl p-4 text-center space-y-1">
            <div className="text-2xl">{s.icon}</div>
            <div className="font-display text-2xl font-bold text-white">{s.value}</div>
            <div className="text-xs text-white/30">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Companies grid */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider font-display">Companies Found</h3>
        <div className="grid grid-cols-2 gap-2">
          {companies.map((c, i) => (
            <div key={i} className="glass rounded-xl p-4 space-y-2 hover:border-blue-500/20 transition-all">
              <div className="flex justify-between items-start gap-2">
                <p className="font-semibold text-sm text-white/90 font-display">{c.name}</p>
                <span className="text-xs text-blue-300 font-mono shrink-0">{c.fit_score}/100</span>
              </div>
              <p className="text-xs text-white/30 leading-relaxed line-clamp-2">{c.tagline}</p>
              <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                <div className="score-bar h-full" style={{ width: `${c.fit_score}%` }} />
              </div>
              <div className="flex flex-wrap gap-1">
                {(c.tech_stack || []).slice(0, 3).map(t => (
                  <span key={t} className="text-[9px] px-2 py-0.5 rounded-full bg-white/5 text-white/25">{t}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* People preview */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider font-display">
          Contacts Discovered
        </h3>
        <div className="space-y-1.5">
          {enriched_people.slice(0, 8).map((p, i) => (
            <div key={i} className="glass rounded-xl px-4 py-3 flex items-center gap-3 hover:border-blue-500/15 transition-all">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-800/40 to-blue-600/20 flex items-center justify-center text-xs font-bold text-blue-300 shrink-0 font-display">
                {p.name?.[0] || '?'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white/80 font-medium truncate">{p.name}</p>
                <p className="text-xs text-white/25 truncate">{p.title} @ {p.company}</p>
              </div>
              <div className="flex gap-1.5 shrink-0">
                {p.linkedin_url && <span className="tag">LinkedIn</span>}
                {p.email_hint   && <span className="tag">Email</span>}
              </div>
            </div>
          ))}
          {enriched_people.length > 8 && (
            <p className="text-xs text-white/20 text-center py-2">
              +{enriched_people.length - 8} more contacts
            </p>
          )}
        </div>
      </div>

      <div className="flex justify-end pt-2">
        <button onClick={handleNext} className="btn-moon rounded-xl px-8 py-3 text-sm font-semibold font-display">
          Set My Priorities →
        </button>
      </div>
    </div>
  )
}
