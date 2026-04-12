import { useState } from 'react'

const TABS = [
  { key: 'linkedin_request', label: 'LI Request' },
  { key: 'linkedin_dm',      label: 'LI DM'      },
  { key: 'cold_email',       label: 'Cold Email'  },
  { key: 'followup',         label: 'Follow-up'   },
]

const PRIORITY_CLASS = { HIGH: 'badge-high', MEDIUM: 'badge-medium', LOW: 'badge-low' }

function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy}
      className="text-xs px-3 py-1.5 rounded-lg glass text-white/35 hover:text-blue-300 hover:border-blue-500/20 transition-all">
      {copied ? '✓ Copied' : 'Copy'}
    </button>
  )
}

function MessageCard({ m }) {
  const [tab, setTab] = useState('linkedin_request')

  const getContent = (t) => {
    if (t === 'cold_email') {
      const ce = m.cold_email || {}
      return ce.subject ? `Subject: ${ce.subject}\n\n${ce.body || ''}` : ce.body || ''
    }
    return m[t]?.message || ''
  }

  const charCount = tab === 'linkedin_request' ? m.linkedin_request?.char_count : null

  return (
    <div className="glass rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-800/50 to-blue-600/20 flex items-center justify-center text-sm font-bold text-blue-300 font-display shrink-0">
            {m.person?.[0]}
          </div>
          <div>
            <p className="text-sm font-semibold text-white/90 font-display">{m.person}</p>
            <p className="text-xs text-white/30">{m.title} @ {m.company}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {m.priority && (
            <span className={`text-[9px] px-2 py-1 rounded-full font-semibold ${PRIORITY_CLASS[m.priority] || ''}`}>
              {m.priority}
            </span>
          )}
          {m.quality_scores?.overall && (
            <span className="text-xs text-white/20 font-mono">Q:{m.quality_scores.overall}/10</span>
          )}
          {m.rewritten && (
            <span className="text-[9px] text-blue-400/60">🔄 rewritten</span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-white/5">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex-1 py-2.5 text-xs font-medium font-display transition-all ${
              tab === t.key ? 'tab-active' : 'text-white/20 hover:text-white/40'
            }`}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="p-5 space-y-3">
        <div className="bg-black/20 rounded-xl p-4 text-sm text-white/65 leading-relaxed whitespace-pre-wrap min-h-28 font-mono text-xs">
          {getContent(tab) || <span className="text-white/15 italic">No message generated</span>}
        </div>
        <div className="flex items-center justify-between">
          <div>
            {charCount !== null && (
              <span className={`text-xs font-mono ${charCount > 300 ? 'text-red-400' : 'text-white/20'}`}>
                {charCount}/300 chars
              </span>
            )}
          </div>
          <CopyBtn text={getContent(tab)} />
        </div>
      </div>

      {/* Links */}
      <div className="flex gap-4 px-5 pb-4">
        {m.linkedin_url && (
          <a href={m.linkedin_url} target="_blank" rel="noreferrer"
            className="text-xs text-blue-400/60 hover:text-blue-300 transition-all">
            View LinkedIn →
          </a>
        )}
        {m.email && (
          <span className="text-xs text-white/25 font-mono">{m.email}</span>
        )}
      </div>
    </div>
  )
}

export default function Messages({ data }) {
  const messages  = data.generated_messages || []
  const campaign  = data.campaign_plan      || {}
  const [view, setView] = useState('messages')

  const high   = messages.filter(m => m.priority === 'HIGH').length
  const medium = messages.filter(m => m.priority === 'MEDIUM').length

  return (
    <div className="space-y-6 pb-12">

      {/* Header */}
      <div className="flex items-end justify-between">
        <div>
          <h2 className="font-display text-3xl font-bold text-white/90">Your Messages</h2>
          <p className="text-white/30 text-sm mt-1">
            {messages.length} contacts ready — {high} HIGH, {medium} MEDIUM priority
          </p>
        </div>
        <div className="flex gap-2">
          {['messages', 'campaign'].map(v => (
            <button key={v} onClick={() => setView(v)}
              className={`text-xs px-4 py-2 rounded-xl font-display transition-all ${
                view === v ? 'btn-moon' : 'glass text-white/30 hover:text-white/60'
              }`}>
              {v === 'messages' ? 'Messages' : '7-Day Plan'}
            </button>
          ))}
        </div>
      </div>

      {view === 'messages' && (
        <div className="space-y-4">
          {messages.length === 0 && (
            <div className="glass rounded-2xl p-8 text-center text-white/20 text-sm">
              No messages generated yet.
            </div>
          )}
          {messages.map((m, i) => <MessageCard key={i} m={m} />)}
        </div>
      )}

      {view === 'campaign' && (
        <div className="space-y-2">
          {Object.entries(campaign).map(([day, details]) => (
            <div key={day} className="glass rounded-xl p-4 space-y-1.5">
              <div className="flex items-start gap-3">
                <span className="text-xs font-bold text-blue-300 font-display uppercase tracking-wider w-10 shrink-0 pt-0.5">
                  {day.replace('_', ' ')}
                </span>
                <div className="flex-1">
                  <p className="text-sm text-white/80">{details.action}</p>
                  {details.contacts?.length > 0 && (
                    <p className="text-xs text-white/25 mt-1">→ {details.contacts.join(', ')}</p>
                  )}
                  <p className="text-xs text-white/18 italic mt-1">{details.note}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
