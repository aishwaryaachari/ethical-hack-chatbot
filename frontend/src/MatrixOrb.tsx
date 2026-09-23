'use client'

import React, { useEffect, useRef } from 'react'

export type MatrixOrbState = 'idle' | 'listening' | 'thinking'

export type MatrixOrbProps = React.ComponentProps<'div'> & {
  state?: MatrixOrbState
  level?: number
  size?: number
  color?: string
  dots?: number
  forceMotion?: boolean
  labels?: Partial<Record<MatrixOrbState, string>>
}

// Faithful port of Matrix Orb.html: same constants, same loop, same draw.
const TAU = Math.PI * 2
const STATES: MatrixOrbState[] = ['idle', 'listening', 'thinking']
const LABELS: Record<MatrixOrbState, string> = {
  idle: 'Idle',
  listening: 'Listening',
  thinking: 'Thinking',
}
const SCALE: Record<MatrixOrbState, number> = {
  idle: 0.88,
  listening: 1,
  thinking: 0.92,
}
const STIFFNESS = 180
const DAMPING = 26
const ATTACK = 0.22
const RELEASE = 0.08
const BLEND = 0.16
const ORBITERS = [
  { radius: 0.62, speed: 2.2, phase: 0, spread: 0.42 },
  { radius: 0.4, speed: -1.7, phase: 2.1, spread: 0.36 },
  { radius: 0.8, speed: 1.15, phase: 4, spread: 0.34 },
]

function envelope(t: number) {
  const slow = 0.5 + 0.5 * Math.sin(t * 0.62 + 0.4)
  const fast = 0.5 + 0.5 * Math.sin(t * 1.9 + 1.1)
  return 0.22 + 0.78 * (0.45 + 0.55 * slow) * fast
}

function intensityOf(
  state: MatrixOrbState,
  d: number,
  nx: number,
  ny: number,
  t: number,
  amp: number,
) {
  if (state === 'listening') {
    const ripple = 0.5 + 0.5 * Math.sin(d * 4.2 - t * 3)
    return 0.32 + amp * (0.34 + 0.38 * ripple)
  }
  if (state === 'thinking') {
    let heat = 0
    for (const o of ORBITERS) {
      const a = t * o.speed + o.phase
      const dx = nx - Math.cos(a) * o.radius
      const dy = ny - Math.sin(a) * o.radius
      heat += Math.exp(-(dx * dx + dy * dy) / (o.spread * o.spread))
    }
    return 0.26 + 0.8 * Math.min(1, heat)
  }
  // idle: visible slow swell so the orb reads as alive even at rest
  return 0.5 + 0.34 * Math.sin(t * 2.4 - d * 2.8)
}

const MatrixOrb = ({
  state = 'idle',
  level,
  size = 240,
  color = '#F75001',
  dots = 11,
  forceMotion = false,
  labels,
  className,
  style,
  ...props
}: MatrixOrbProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const cfgRef = useRef({ state, size, color, dots })
  cfgRef.current = { state, size, color, dots }
  const levelRef = useRef(level)
  levelRef.current = level

  useEffect(() => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx) return

    let dpr = 1
    let raf = 0
    const weights: Record<MatrixOrbState, number> = { idle: 0, listening: 0, thinking: 0 }
    weights[cfgRef.current.state] = 1
    let t = 0
    let amplitude = 0
    let scale = SCALE[cfgRef.current.state]
    let velocity = 0
    let last = performance.now()

    function setup() {
      const cfg = cfgRef.current
      dpr = Math.min(window.devicePixelRatio || 1, 4)
      const buffer = Math.round(cfg.size * dpr)
      canvas!.width = canvas!.height = buffer
      canvas!.style.width = cfg.size + 'px'
      canvas!.style.height = cfg.size + 'px'
      ctx!.setTransform(1, 0, 0, 1, 0, 0)
      ctx!.scale(buffer / cfg.size, buffer / cfg.size)
    }

    function levelAt(tt: number) {
      const v = levelRef.current
      return v === undefined || !Number.isFinite(v)
        ? envelope(tt)
        : Math.min(1, Math.max(0, v))
    }

    function draw(tt: number, amp: number, sc: number) {
      const cfg = cfgRef.current
      const size = cfg.size
      ctx!.clearRect(0, 0, size, size)
      ctx!.fillStyle = cfg.color
      const grid = Math.max(3, Math.round(cfg.dots))
      const half = (grid - 1) / 2
      const spacing = (size * 0.74) / (grid - 1)
      const maxRadius = spacing * 0.6
      const center = size / 2

      for (let iy = 0; iy < grid; iy++) {
        for (let ix = 0; ix < grid; ix++) {
          const nx = (ix - half) / half
          const ny = (iy - half) / half
          const d = Math.hypot(nx, ny)
          if (d > 1.12) continue
          let blended = 0
          for (const s of STATES) {
            if (weights[s] < 0.001) continue
            blended += weights[s] * intensityOf(s, d, nx, ny, tt, amp)
          }
          const intensity = Math.min(1, Math.max(0, blended))
          const radius = maxRadius * Math.exp(-d * d * 1.7) * intensity * sc
          if (radius * dpr < 0.5) continue
          ctx!.beginPath()
          ctx!.arc(center + (ix - half) * spacing * sc, center + (iy - half) * spacing * sc, radius, 0, TAU)
          ctx!.fill()
        }
      }
    }

    function frame(now: number) {
      const dt = Math.min((now - last) / 1000, 0.05)
      last = now
      t += dt
      const current = cfgRef.current.state
      const target = levelAt(t)
      const rate = target > amplitude ? ATTACK : RELEASE
      amplitude += (target - amplitude) * (1 - Math.pow(1 - rate, dt * 60))
      const step = 1 - Math.pow(1 - BLEND, dt * 60)
      for (const s of STATES) {
        weights[s] += ((s === current ? 1 : 0) - weights[s]) * step
      }
      velocity += (-STIFFNESS * (scale - SCALE[current]) - DAMPING * velocity) * dt
      scale += velocity * dt
      draw(t, amplitude, scale)
      raf = requestAnimationFrame(frame)
    }

    const onResize = () => {
      const next = Math.min(window.devicePixelRatio || 1, 4)
      if (next !== dpr) setup()
    }
    window.addEventListener('resize', onResize)

    const reduce = !forceMotion && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    setup()
    if (reduce) {
      draw(0, levelAt(0), SCALE[cfgRef.current.state])
    } else {
      raf = requestAnimationFrame(frame)
    }

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', onResize)
    }
  }, [])

  return (
    <div
      data-slot="matrix-orb"
      data-state={state}
      className={className}
      style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12, ...style }}
      {...props}
    >
      <canvas ref={canvasRef} aria-hidden style={{ display: 'block' }} />
      <span role="status" aria-live="polite" style={{ fontSize: 18, color: 'var(--text-3)' }}>
        {labels?.[state] ?? LABELS[state]}
      </span>
    </div>
  )
}

export default MatrixOrb
