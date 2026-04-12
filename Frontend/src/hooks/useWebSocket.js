import { useEffect, useRef, useState } from 'react'

export default function useWebSocket(sessionId) {
  const [progress, setProgress] = useState([])
  const ws = useRef(null)

  useEffect(() => {
    if (!sessionId) return

    ws.current = new WebSocket(`ws://localhost:8000/ws/${sessionId}`)

    ws.current.onmessage = (e) => {
      const event = JSON.parse(e.data)
      setProgress(prev => {
        // Update existing agent or add new
        const exists = prev.findIndex(p => p.agent === event.agent)
        if (exists >= 0) {
          const updated = [...prev]
          updated[exists] = event
          return updated
        }
        return [...prev, event]
      })
    }

    ws.current.onerror = () => console.log('WebSocket error')

    return () => ws.current?.close()
  }, [sessionId])

  const reset = () => setProgress([])

  return { progress, reset }
}