import { useId, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

interface Pos {
  top: number
  left: number
  width: number
  above: boolean
}

interface InfoTipProps {
  label: string
  hint: string
  className?: string
  children: ReactNode
}

function placePop(anchor: DOMRect): Pos {
  const width = Math.min(280, window.innerWidth - 16)
  let left = anchor.left
  if (left + width > window.innerWidth - 8) {
    left = window.innerWidth - width - 8
  }
  if (left < 8) left = 8
  const above = window.innerHeight - anchor.bottom < 140 && anchor.top > 140
  return {
    top: above ? anchor.top - 8 : anchor.bottom + 8,
    left,
    width,
    above,
  }
}

export function InfoMark({ label }: { label: string }) {
  return (
    <button
      type="button"
      className="info-tip-mark"
      aria-label={`About ${label}`}
      onClick={event => event.stopPropagation()}
    >
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none" aria-hidden="true">
        <circle cx="6.5" cy="6.5" r="5.25" stroke="currentColor" strokeWidth="1.2" />
        <path
          d="M6.5 6v3.1M6.5 4.15v.2"
          stroke="currentColor"
          strokeWidth="1.3"
          strokeLinecap="round"
        />
      </svg>
    </button>
  )
}

export function InfoLabel({ text }: { text: string }) {
  return (
    <span className="info-tip-label">
      {text}
      <InfoMark label={text} />
    </span>
  )
}

export default function InfoTip({ label, hint, className, children }: InfoTipProps) {
  const id = useId()
  const rootRef = useRef<HTMLDivElement>(null)
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState<Pos | null>(null)

  const show = () => {
    const box = rootRef.current?.getBoundingClientRect()
    if (!box) return
    setPos(placePop(box))
    setOpen(true)
  }

  const hide = () => setOpen(false)

  useLayoutEffect(() => {
    if (!open) return
    const onMove = () => {
      const box = rootRef.current?.getBoundingClientRect()
      if (box) setPos(placePop(box))
    }
    window.addEventListener('scroll', onMove, true)
    window.addEventListener('resize', onMove)
    return () => {
      window.removeEventListener('scroll', onMove, true)
      window.removeEventListener('resize', onMove)
    }
  }, [open])

  const classes = className ? `info-tip ${className}` : 'info-tip'

  return (
    <div
      ref={rootRef}
      className={classes}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocusCapture={show}
      onBlurCapture={event => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          hide()
        }
      }}
    >
      {children}
      {open &&
        pos &&
        createPortal(
          <div
            className={`info-tip-pop${pos.above ? ' is-above' : ''}`}
            id={id}
            role="tooltip"
            style={{ top: pos.top, left: pos.left, width: pos.width }}
          >
            <div className="info-tip-pop-label">{label}</div>
            <p className="info-tip-pop-body">{hint}</p>
          </div>,
          document.body,
        )}
    </div>
  )
}
