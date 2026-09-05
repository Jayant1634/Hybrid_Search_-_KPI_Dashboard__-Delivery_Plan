interface Props {
  value: number
  raw?: number
  max?: number
  color?: 'purple' | 'neutral' | 'hybrid'
}

const MIN_FILL_PCT = 6

export default function ScoreBar({ value, raw, max = 1, color = 'neutral' }: Props) {
  const ratio = max <= 0 ? 0 : value / max
  const pct = value <= 0 ? 0 : Math.min(100, Math.max(MIN_FILL_PCT, ratio * 100))
  const fillClass =
    color === 'purple' ? 'fill-purple' : color === 'hybrid' ? 'fill-hybrid' : 'fill-neutral'
  const tooltip = raw === undefined ? undefined : String(raw)

  return (
    <div className="score-bar" title={tooltip}>
      <div className="score-bar-track">
        <div
          className={`score-bar-fill ${fillClass}${value <= 0 ? ' is-empty' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="score-num">{value.toFixed(3)}</span>
    </div>
  )
}
