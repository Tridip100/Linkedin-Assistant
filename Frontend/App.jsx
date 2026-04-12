import { useState } from 'react'
import SpaceBackground from './components/SpaceBackground'
import SearchStep      from './components/SearchStep'
import ResultsStep     from './components/ResultsStep'
import InterviewStep   from './components/InterviewStep'
import ScoredLeads     from './components/ScoredLeads'
import Dashboard       from './components/Dashboard'
import SenderProfile   from './components/SenderProfile'
import Messages        from './components/Messages'

const STEPS = ['search', 'results', 'interview', 'scored', 'dashboard', 'profile', 'messages']

const STEP_LABELS = {
  search:    'Search',
  results:   'Results',
  interview: 'Priorities',
  scored:    'Ranking',
  dashboard: 'Dashboard',
  profile:   'Profile',
  messages:  'Messages',
}

export default function App() {
  const [step,      setStep]      = useState('search')
  const [sessionId, setSessionId] = useState(null)
  const [data,      setData]      = useState({})

  const goTo = (s) => setStep(s)
  const currentIdx = STEPS.indexOf(step)

  return (
    <div className="min-h-screen relative" style={{ fontFamily: "'DM Sans', sans-serif" }}>

      {/* Space background canvas */}
      <SpaceBackground />

      {/* Content layer */}
      <div className="relative z-10 min-h-screen flex flex-col">

        {/* Header */}
        <header className="flex items-center justify-between px-8 py-4 border-b border-white/5">
          <div className="flex items-center gap-3">
            {/* Moon logo */}
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-200/80 to-blue-400/40 moon-glow flex items-center justify-center text-sm">
              🌙
            </div>
            <div>
              <span className="font-display font-bold text-white tracking-tight">Prospera</span>
              <span className="text-white/20 text-xs ml-2">by AI</span>
            </div>
          </div>

          {/* Step indicators */}
          <div className="hidden md:flex items-center gap-1">
            {STEPS.map((s, i) => {
              const done    = i < currentIdx
              const current = i === currentIdx
              return (
                <div key={s} className="flex items-center gap-1">
                  <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-display transition-all ${
                    current ? 'bg-blue-500/15 border border-blue-500/30 text-blue-300' :
                    done    ? 'text-white/30' :
                    'text-white/15'
                  }`}>
                    {done && <span className="text-emerald-400">✓</span>}
                    {STEP_LABELS[s]}
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className={`w-4 h-px ${done ? 'bg-white/20' : 'bg-white/5'}`} />
                  )}
                </div>
              )
            })}
          </div>

          {/* Session badge */}
          {sessionId && (
            <div className="text-[9px] font-mono text-white/15 hidden lg:block">
              {sessionId.slice(0, 8)}...
            </div>
          )}
        </header>

        {/* Main content */}
        <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-8">
          {step === 'search' && (
            <SearchStep
              setSessionId={setSessionId}
              setData={setData}
              goTo={goTo}
            />
          )}
          {step === 'results' && (
            <ResultsStep
              data={data}
              sessionId={sessionId}
              setData={setData}
              goTo={goTo}
            />
          )}
          {step === 'interview' && (
            <InterviewStep
              data={data}
              sessionId={sessionId}
              setData={setData}
              goTo={goTo}
            />
          )}
          {step === 'scored' && (
            <ScoredLeads
              data={data}
              sessionId={sessionId}
              setData={setData}
              goTo={goTo}
            />
          )}
          {step === 'dashboard' && (
            <Dashboard
              data={data}
              sessionId={sessionId}
              goTo={goTo}
            />
          )}
          {step === 'profile' && (
            <SenderProfile
              data={data}
              sessionId={sessionId}
              setData={setData}
              goTo={goTo}
            />
          )}
          {step === 'messages' && (
            <Messages
              data={data}
              sessionId={sessionId}
            />
          )}
        </main>

        {/* Footer */}
        <footer className="text-center py-4 text-white/10 text-xs border-t border-white/5">
          Prospera • AI-powered outreach intelligence
        </footer>
      </div>
    </div>
  )
}
