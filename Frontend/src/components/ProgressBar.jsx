import { useEffect, useState } from 'react'

const dots = ['.', '..', '...']

export default function ProgressBar({ message }) {
  const [dot, setDot] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setDot(d => (d + 1) % 3), 500)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="w-10 h-10 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
      <p className="text-white/60 text-sm text-center">
        {message}{dots[dot]}
      </p>
    </div>
  )
}