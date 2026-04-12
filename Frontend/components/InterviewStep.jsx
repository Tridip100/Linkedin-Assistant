import { useState } from 'react'
import { submitAnswers } from '../api/client'

export default function InterviewStep({ data, sessionId, setData, goTo }) {
  const questions        = data.questions || []
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(false)

  const toggle = (qid, opt, question, weight_key) => {
    setAnswers(prev => {
      const cur = prev[qid]?.selected || []
      const upd = cur.includes(opt) ? cur.filter(o => o !== opt) : [...cur, opt]
      return { ...prev, [qid]: { selected: upd, question, weight_key } }
    })
  }

  const allAnswered = questions.every(q => (answers[q.id]?.selected || []).length > 0)

  const handleSubmit = async () => {
    setLoading(true)
    const formatted = {}
    questions.forEach(q => {
      formatted[q.id] = {
        question:   q.question,
        answer:     answers[q.id]?.selected || [],
        weight_key: q.weight_key,
      }
    })
    try {
      const res = await submitAnswers(sessionId, formatted)
      setData(prev => ({ ...prev,
        scored_leads:   res.data.data.scored_leads   || [],
        scoring_config: res.data.data.scoring_config || {},
      }))
      goTo('scored')
    } catch (e) {
      console.error('[submit]', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 pb-12">
      <div className="space-y-1">
        <h2 className="font-display text-3xl font-bold text-white/90">Set your priorities</h2>
        <p className="text-white/30 text-sm">Help me rank your leads by what matters most to you.</p>
      </div>

      <div className="space-y-5">
        {questions.map((q, qi) => {
          const selected = answers[q.id]?.selected || []
          return (
            <div key={q.id} className="space-y-2.5">
              <p className="text-sm font-medium text-white/70 font-display">
                <span className="text-white/25 mr-2 font-mono">{qi + 1}.</span>
                {q.question}
              </p>
              {q.multi_select && (
                <p className="text-[10px] text-white/20">Select all that apply</p>
              )}
              <div className="grid grid-cols-2 gap-1.5">
                {q.options.map(opt => {
                  const isSel = selected.includes(opt)
                  return (
                    <button
                      key={opt}
                      onClick={() => toggle(q.id, opt, q.question, q.weight_key)}
                      className={`text-left text-xs px-4 py-3 rounded-xl border transition-all ${
                        isSel
                          ? 'glass-blue text-blue-200 border-blue-500/40'
                          : 'glass text-white/35 hover:text-white/60 hover:border-white/10'
                      }`}
                    >
                      <span className={`inline-block w-3 h-3 rounded mr-2 border transition-all align-middle ${
                        isSel ? 'bg-blue-500 border-blue-400' : 'border-white/20'
                      }`} />
                      {opt}
                    </button>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      <div className="flex justify-end pt-2">
        <button
          onClick={handleSubmit}
          disabled={!allAnswered || loading}
          className="btn-moon rounded-xl px-8 py-3 text-sm font-semibold font-display disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {loading
            ? <span className="flex items-center gap-2"><div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Scoring...</span>
            : 'Score My Leads →'}
        </button>
      </div>
    </div>
  )
}
