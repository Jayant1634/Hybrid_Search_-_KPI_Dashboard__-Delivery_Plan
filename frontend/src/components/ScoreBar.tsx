interface Props {
  value: number
  max?: number
  color?: 'purple' | 'neutral'
}

export default function ScoreBar({ value, max = 1, color = 'neutral' }: Props) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  return (
    <div className="score-bar-track">
      <div
        className={`score-bar-fill ${color === 'purple' ? 'fill-purple' : 'fill-neutral'}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
