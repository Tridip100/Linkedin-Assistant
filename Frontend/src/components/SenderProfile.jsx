import { useState } from 'react'
import { generateMessages } from '../api/client'

const FIELDS = [
  { key: 'name',    label: 'Full name',              placeholder: 'Your full name',                    span: 1 },
  { key: 'college', label: 'College / Company',      placeholder: 'IIT Delhi, BITS Pilani...',          span: 1 },
  { key: 'degree',  label: 'Degree / Role',          placeholder: 'B.Tech CS, SDE, Data Scientist...',  span: 1 },
  { key: 'year',    label: 'Year / Experience',      placeholder: 'Final year, 2 years exp...',          span: 1 },
  { key: 'skills',  label: 'Top skills',             placeholder: 'Python, PyTorch, LangChain (comma separated)', span: 2 },
  { key: 'project', label: 'Best project',           placeholder: 'One line about your best project',   span: 2 },
  { key: 'achieve', label: 'Achievement',            placeholder: 'Hackathon win, Kaggle rank, award...', span: 1 },
  { key: 'linkedin',label: 'Your LinkedIn URL',      placeholder: 'https://linkedin.com/in/yourname',   span: 1 },
  { key: 'goal',    label: "What you're looking for", placeholder: 'ML internship, full-time SDE...',   span: 2 },
]

export default function SenderProfile({ data, sessionId, setData, goTo }) {
  const [form,    setForm]    = useState({ name:'', college:'', degree:'', year:'', skills:'', project:'', achieve:'', linkedin:'', goal:'' })
  const [loading, setLoading] = useState(false)

  const set = (k, v) => setForm(p => ({ ...p, [k]: v }))

  const handleGenerate = async () => {
    setLoading(true)
    try {
      const payload = { ...form, skills: form.skills.split(',').map(s => s.trim()).filter(Boolean) }
      const res     = await generateMessages(sessionId, payload)
      setData(prev => ({ ...prev, ...res.data.data }))
      goTo('messages')
    } catch (e) {
      console.error('[generate]', e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 pb-12">
      <div className="space-y-1">
        <h2 className="font-display text-3xl font-bold text-white/90">Tell me about yourself</h2>
        <p className="text-white/30 text-sm">I'll use this to write messages from your perspective. Press Enter to skip any field.</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {FIELDS.map(f => (
          <div key={f.key} className={`space-y-1.5 ${f.span === 2 ? 'col-span-2' : ''}`}>
            <label className="text-xs text-white/35 font-medium font-display">{f.label}</label>
            <input
              className="w-full glass rounded-xl px-4 py-3 text-sm text-white placeholder-white/15 outline-none hover:border-white/10 focus:border-blue-500/40 transition-all"
              placeholder={f.placeholder}
              value={form[f.key]}
              onChange={e => set(f.key, e.target.value)}
            />
          </div>
        ))}
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleGenerate}
          disabled={!form.name.trim() || loading}
          className="btn-moon rounded-xl px-8 py-3 text-sm font-semibold font-display disabled:opacity-30 disabled:cursor-not-allowed"
        >
          {loading
            ? <span className="flex items-center gap-2"><div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Writing messages...</span>
            : 'Generate Messages →'}
        </button>
      </div>
    </div>
  )
}
