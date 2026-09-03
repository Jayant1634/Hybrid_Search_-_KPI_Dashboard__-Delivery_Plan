import { useEffect, useRef } from 'react'

declare global {
  interface Window {
    VANTA: {
      NET: (opts: Record<string, unknown>) => { destroy: () => void }
    }
  }
}

interface Props {
  dark: boolean
}

export default function VantaHero({ dark }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const effect = useRef<{ destroy: () => void } | null>(null)

  useEffect(() => {
    if (!ref.current || !window.VANTA?.NET) return
    if (effect.current) effect.current.destroy()
    effect.current = window.VANTA.NET({
      el: ref.current,
      mouseControls: true,
      touchControls: true,
      gyroControls: false,
      minHeight: 200,
      minWidth: 200,
      scale: 1.0,
      scaleMobile: 1.0,
      color: dark ? 0x7823dc : 0x7823dc,
      backgroundColor: dark ? 0x111111 : 0xffffff,
      points: 14,
      maxDistance: 22,
      spacing: 18,
    })
    return () => { effect.current?.destroy() }
  }, [dark])

  return <div ref={ref} className="vanta-hero" />
}
