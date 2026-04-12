import { useEffect, useRef } from 'react'

export default function SpaceBackground() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx    = canvas.getContext('2d')
    let animId

    const resize = () => {
      canvas.width  = window.innerWidth
      canvas.height = window.innerHeight
    }
    resize()
    window.addEventListener('resize', resize)

    // Stars
    const stars = Array.from({ length: 200 }, () => ({
      x:       Math.random() * canvas.width,
      y:       Math.random() * canvas.height,
      r:       Math.random() * 1.5 + 0.2,
      alpha:   Math.random() * 0.7 + 0.1,
      twinkle: Math.random() * 0.02 + 0.005,
      phase:   Math.random() * Math.PI * 2,
    }))

    // Shooting stars
    let shooters = []
    const spawnShooter = () => {
      shooters.push({
        x:     Math.random() * canvas.width,
        y:     Math.random() * canvas.height * 0.5,
        vx:    (Math.random() * 3 + 2) * (Math.random() > 0.5 ? 1 : -1),
        vy:    Math.random() * 2 + 1,
        life:  1,
        decay: Math.random() * 0.015 + 0.01,
        len:   Math.random() * 80 + 40,
      })
    }

    // Moon position
    const moon = {
      x:    canvas.width * 0.75,
      y:    canvas.height * 0.22,
      r:    90,
      t:    0,
    }

    // Nebula particles
    const nebula = Array.from({ length: 60 }, () => ({
      x:     Math.random() * canvas.width,
      y:     Math.random() * canvas.height,
      r:     Math.random() * 120 + 40,
      alpha: Math.random() * 0.04 + 0.01,
      hue:   Math.random() > 0.5 ? 220 : 200,
    }))

    let t = 0
    let shootTimer = 0

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Deep space gradient
      const bg = ctx.createRadialGradient(
        canvas.width * 0.5, canvas.height * 0.3, 0,
        canvas.width * 0.5, canvas.height * 0.5, canvas.height
      )
      bg.addColorStop(0,   'rgba(5, 15, 35, 1)')
      bg.addColorStop(0.4, 'rgba(2, 8, 20, 1)')
      bg.addColorStop(1,   'rgba(1, 3, 8, 1)')
      ctx.fillStyle = bg
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      // Nebula clouds
      nebula.forEach(n => {
        const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r)
        grad.addColorStop(0,   `hsla(${n.hue}, 70%, 60%, ${n.alpha})`)
        grad.addColorStop(1,   'transparent')
        ctx.fillStyle = grad
        ctx.beginPath()
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2)
        ctx.fill()
      })

      // Stars
      stars.forEach(s => {
        s.phase += s.twinkle
        const a = s.alpha * (0.6 + 0.4 * Math.sin(s.phase))
        ctx.beginPath()
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(200, 220, 255, ${a})`
        ctx.fill()
      })

      // Moon glow halo
      moon.t = t
      const mx = moon.x + Math.sin(t * 0.3) * 8
      const my = moon.y + Math.cos(t * 0.2) * 5

      // Outer glow rings
      ;[200, 150, 110].forEach((r, i) => {
        const halo = ctx.createRadialGradient(mx, my, moon.r * 0.8, mx, my, r)
        halo.addColorStop(0,   `rgba(100, 149, 237, ${0.12 - i * 0.03})`)
        halo.addColorStop(1,   'transparent')
        ctx.fillStyle = halo
        ctx.beginPath()
        ctx.arc(mx, my, r, 0, Math.PI * 2)
        ctx.fill()
      })

      // Moon body
      const moonGrad = ctx.createRadialGradient(
        mx - moon.r * 0.3, my - moon.r * 0.3, moon.r * 0.1,
        mx, my, moon.r
      )
      moonGrad.addColorStop(0,   'rgba(210, 225, 255, 0.95)')
      moonGrad.addColorStop(0.3, 'rgba(180, 205, 250, 0.85)')
      moonGrad.addColorStop(0.7, 'rgba(140, 170, 220, 0.70)')
      moonGrad.addColorStop(1,   'rgba(80, 110, 180, 0.40)')
      ctx.fillStyle = moonGrad
      ctx.beginPath()
      ctx.arc(mx, my, moon.r, 0, Math.PI * 2)
      ctx.fill()

      // Moon craters
      const craters = [
        { ox: -25, oy: -15, r: 12 },
        { ox:  20, oy:  20, r:  8 },
        { ox: -10, oy:  30, r:  6 },
        { ox:  35, oy: -25, r:  5 },
        { ox: -35, oy:  10, r:  4 },
      ]
      craters.forEach(c => {
        const cg = ctx.createRadialGradient(
          mx + c.ox - 2, my + c.oy - 2, 0,
          mx + c.ox, my + c.oy, c.r
        )
        cg.addColorStop(0,   'rgba(60, 90, 140, 0.5)')
        cg.addColorStop(0.7, 'rgba(100, 130, 190, 0.2)')
        cg.addColorStop(1,   'transparent')
        ctx.fillStyle = cg
        ctx.beginPath()
        ctx.arc(mx + c.ox, my + c.oy, c.r, 0, Math.PI * 2)
        ctx.fill()
      })

      // Orbiting particles around moon
      const orbitCount = 5
      for (let i = 0; i < orbitCount; i++) {
        const angle  = t * 0.4 + (i / orbitCount) * Math.PI * 2
        const ox     = mx + Math.cos(angle) * (moon.r + 20 + i * 8)
        const oy     = my + Math.sin(angle) * (moon.r + 20 + i * 8) * 0.4
        const alpha  = 0.3 + 0.3 * Math.sin(angle + t)
        ctx.beginPath()
        ctx.arc(ox, oy, 1.5 - i * 0.2, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(150, 190, 255, ${alpha})`
        ctx.fill()
      }

      // Shooting stars
      shootTimer++
      if (shootTimer > 180 + Math.random() * 120) {
        spawnShooter()
        shootTimer = 0
      }

      shooters = shooters.filter(s => s.life > 0)
      shooters.forEach(s => {
        const ex = s.x + s.vx * s.len
        const ey = s.y + s.vy * s.len
        const sg  = ctx.createLinearGradient(s.x, s.y, ex, ey)
        sg.addColorStop(0,   `rgba(200, 220, 255, 0)`)
        sg.addColorStop(0.5, `rgba(200, 220, 255, ${s.life * 0.6})`)
        sg.addColorStop(1,   `rgba(200, 220, 255, 0)`)
        ctx.beginPath()
        ctx.moveTo(s.x, s.y)
        ctx.lineTo(ex, ey)
        ctx.strokeStyle = sg
        ctx.lineWidth   = 1.5
        ctx.stroke()
        s.x    += s.vx * 3
        s.y    += s.vy * 3
        s.life -= s.decay
      })

      t += 0.01
      animId = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 pointer-events-none"
      style={{ zIndex: 0 }}
    />
  )
}
