import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import type { BfsBlock, CallGraphDoc, FileMeta, FunctionMeta, GraphEdge } from '../callgraphTypes'

type Kind = 'files' | 'functions'

interface Props {
  graph: CallGraphDoc
}

interface LayoutNode {
  id: string
  x: number
  y: number
  col: 'in' | 'focus' | 'out'
}

const NODE_W = 210
const NODE_H = 36
const COL_GAP = 56
const ROW = 46
const PAD = 20

function shortFile(path: string): string {
  const parts = path.split('/')
  return parts.slice(-2).join('/')
}

function shortNode(id: string, kind: Kind): string {
  if (kind === 'files') return shortFile(id)
  const [file, name] = id.split('::')
  return `${shortFile(file)} · ${name ?? ''}`
}

function outgoing(graph: CallGraphDoc, kind: Kind, id: string): string[] {
  if (kind === 'files') return graph.files[id]?.calls ?? []
  return graph.functions[id]?.calls ?? []
}

function incoming(graph: CallGraphDoc, kind: Kind, id: string): string[] {
  if (kind === 'files') {
    const meta: FileMeta | undefined = graph.files[id]
    return meta ? [...new Set([...meta.called_by, ...meta.imported_by])] : []
  }
  const meta: FunctionMeta | undefined = graph.functions[id]
  return meta?.called_by ?? []
}

function edgePath(a: LayoutNode, b: LayoutNode): string {
  const x1 = a.x + NODE_W
  const y1 = a.y + NODE_H / 2
  const x2 = b.x
  const y2 = b.y + NODE_H / 2
  const mid = (x1 + x2) / 2
  return `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`
}

export default function CallGraphView({ graph }: Props) {
  const [kind, setKind] = useState<Kind>('files')
  const [query, setQuery] = useState('')
  const [focus, setFocus] = useState<string | null>(null)
  const [trail, setTrail] = useState<string[]>([])
  const [hopD, setHopD] = useState<string | null>(null)
  const [hopKey, setHopKey] = useState(0)
  const [playing, setPlaying] = useState(false)
  const playRef = useRef(false)

  const bfs: BfsBlock = kind === 'files' ? graph.bfs_files : graph.bfs_functions
  const hops: GraphEdge[] = kind === 'files' ? graph.hops_files : graph.hops_functions
  const topo = kind === 'files' ? graph.topo_files : graph.topo_functions
  const uncalled = kind === 'files' ? graph.uncalled_files : graph.uncalled_functions

  const q = query.trim().toLowerCase()
  const match = useCallback(
    (id: string) => (q ? id.toLowerCase().includes(q) : true),
    [q],
  )

  const filteredTopo = useMemo(() => topo.filter(match), [topo, match])

  const current = focus ?? (bfs.roots.find(match) ?? bfs.roots[0] ?? null)

  const inNodes = useMemo(() => {
    if (!current) return []
    if (!focus) return []
    return incoming(graph, kind, current).filter(match)
  }, [current, focus, graph, kind, match])

  const outNodes = useMemo(() => {
    if (!current) return []
    const src = focus ? outgoing(graph, kind, current) : (bfs.layers[1] ?? [])
    if (!focus) {
      const fromRoots = new Set(
        hops.filter(h => match(h.from) && match(h.to)).map(h => h.to),
      )
      return bfs.layers[1].filter(id => fromRoots.has(id) || match(id))
    }
    return src.filter(match)
  }, [bfs.layers, current, focus, graph, hops, kind, match])

  const leftIds = focus ? inNodes : bfs.roots.filter(match)
  const rightIds = outNodes
  const centerId = focus ? current : null

  const layout = useMemo(() => {
    const left: LayoutNode[] = leftIds.map((id, i) => ({
      id,
      x: PAD,
      y: PAD + i * ROW,
      col: 'in',
    }))
    const focusX = PAD + NODE_W + COL_GAP
    const rightX = centerId ? focusX + NODE_W + COL_GAP : PAD + NODE_W + COL_GAP
    const centerY =
      PAD + Math.max(0, Math.floor((Math.max(leftIds.length, rightIds.length) - 1) / 2)) * ROW
    const center: LayoutNode[] = centerId
      ? [{ id: centerId, x: focusX, y: centerY, col: 'focus' }]
      : []
    const right: LayoutNode[] = rightIds.map((id, i) => ({
      id,
      x: rightX,
      y: PAD + i * ROW,
      col: 'out',
    }))
    return { left, center, right, rightX }
  }, [centerId, leftIds, rightIds])

  const svgW = layout.rightX + NODE_W + PAD
  const svgH = PAD * 2 + Math.max(leftIds.length, rightIds.length, 1) * ROW

  const edges = useMemo(() => {
    const list: { key: string; d: string; from: string; to: string }[] = []
    if (focus && layout.center[0]) {
      const c = layout.center[0]
      for (const n of layout.left) {
        list.push({ key: `in-${n.id}`, d: edgePath(n, c), from: n.id, to: c.id })
      }
      for (const n of layout.right) {
        list.push({ key: `out-${n.id}`, d: edgePath(c, n), from: c.id, to: n.id })
      }
    } else {
      const leftMap = new Map(layout.left.map(n => [n.id, n]))
      const rightMap = new Map(layout.right.map(n => [n.id, n]))
      for (const h of hops) {
        const a = leftMap.get(h.from)
        const b = rightMap.get(h.to)
        if (a && b) list.push({ key: `${h.from}->${h.to}`, d: edgePath(a, b), from: h.from, to: h.to })
      }
    }
    return list
  }, [focus, hops, layout])

  const triggerHop = (d: string) => {
    setHopD(d)
    setHopKey(k => k + 1)
  }

  const goTo = (id: string, fromId?: string) => {
    const edge = fromId
      ? edges.find(e => (e.from === fromId && e.to === id) || (e.from === id && e.to === fromId))
      : undefined
    if (edge) triggerHop(edge.d)
    else {
      const fallback = edges.find(e => e.to === id || e.from === id)
      if (fallback) triggerHop(fallback.d)
    }
    setFocus(id)
    setTrail(t => (t[t.length - 1] === id ? t : [...t, id]))
  }

  const resetView = () => {
    setFocus(null)
    setTrail([])
    setHopD(null)
    setPlaying(false)
    playRef.current = false
  }

  const playHops = async () => {
    if (playing) {
      playRef.current = false
      setPlaying(false)
      return
    }
    setPlaying(true)
    playRef.current = true
    setFocus(null)
    setTrail([])
    const roots = bfs.roots.filter(match)
    const targets = bfs.layers[1]
    const leftMap = new Map(
      roots.map((id, i) => [id, { id, x: PAD, y: PAD + i * ROW, col: 'in' as const }]),
    )
    const rightX = PAD + NODE_W + COL_GAP
    const rightMap = new Map(
      targets.map((id, i) => [id, { id, x: rightX, y: PAD + i * ROW, col: 'out' as const }]),
    )
    const seq = hops.filter(h => match(h.from) && match(h.to))
    for (const h of seq) {
      if (!playRef.current) break
      const a = leftMap.get(h.from)
      const b = rightMap.get(h.to)
      if (a && b) {
        setTrail([h.from, h.to])
        triggerHop(edgePath(a, b))
        await new Promise(r => setTimeout(r, 850))
      }
    }
    playRef.current = false
    setPlaying(false)
  }

  useEffect(() => {
    setFocus(null)
    setTrail([])
    setHopD(null)
  }, [kind])

  const detailId = trail[trail.length - 1] ?? current
  const detailFile = kind === 'files' ? detailId : graph.functions[detailId ?? '']?.file
  const detailFn = kind === 'functions' ? graph.functions[detailId ?? ''] : undefined

  return (
    <div className="cg-wrap">
      <div className="cg-toolbar">
        <div className="cg-toggle" role="tablist">
          <button
            type="button"
            role="tab"
            className={kind === 'files' ? 'active' : ''}
            onClick={() => setKind('files')}
          >
            Files
          </button>
          <button
            type="button"
            role="tab"
            className={kind === 'functions' ? 'active' : ''}
            onClick={() => setKind('functions')}
          >
            Functions
          </button>
        </div>
        <label className="cg-search">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
            <circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.4" />
            <path d="M11 11l2.5 2.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          </svg>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Filter nodes…"
          />
        </label>
        <button type="button" className="btn-secondary" onClick={() => void playHops()}>
          {playing ? 'Stop hops' : 'Play hops'}
        </button>
        <button type="button" className="btn-secondary" onClick={resetView} disabled={!focus && trail.length === 0}>
          Reset
        </button>
      </div>

      <div className="cg-legend">
        <span><i className="cg-dot cg-dot-root" /> Uncalled (BFS start)</span>
        <span><i className="cg-dot cg-dot-hop" /> One-hop callee</span>
        <span><i className="cg-dot cg-dot-focus" /> Hop focus</span>
        <span className="cg-legend-note">
          {focus ? 'Click a neighbour to hop along the path.' : 'Click a root to hop into it. Play hops animates the one-level BFS edges.'}
        </span>
      </div>

      {trail.length > 0 && (
        <div className="cg-trail" aria-label="Hop path">
          {trail.map((id, i) => (
            <span key={`${id}-${i}`} className="cg-trail-seg">
              {i > 0 && <span className="cg-trail-arrow">→</span>}
              <button type="button" className="cg-trail-chip" onClick={() => goTo(id, trail[i - 1])}>
                {shortNode(id, kind)}
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="cg-body">
        <aside className="cg-topo">
          <div className="cg-panel-label">Topological order</div>
          <p className="cg-panel-hint">Uncalled roots first, then their one-hop callees (Kahn).</p>
          <ol className="cg-topo-list">
            {filteredTopo.map((id, i) => {
              const isRoot = uncalled.includes(id)
              const active = id === detailId
              return (
                <li key={id}>
                  <button
                    type="button"
                    className={`cg-topo-item${active ? ' active' : ''}${isRoot ? ' root' : ''}`}
                    onClick={() => goTo(id, trail[trail.length - 1])}
                    title={id}
                  >
                    <span className="cg-topo-idx">{i + 1}</span>
                    <span className="cg-topo-name">{shortNode(id, kind)}</span>
                  </button>
                </li>
              )
            })}
          </ol>
        </aside>

        <div className="cg-canvas-wrap">
          <svg
            className="cg-svg"
            width={svgW}
            height={svgH}
            viewBox={`0 0 ${svgW} ${svgH}`}
            role="img"
            aria-label="Call graph hop canvas"
          >
            {edges.map(e => (
              <path
                key={e.key}
                d={e.d}
                className={`cg-edge${trail.includes(e.from) && trail.includes(e.to) ? ' active' : ''}`}
                fill="none"
              />
            ))}
            {hopD && (
              <circle
                key={hopKey}
                r="4.5"
                className="cg-hopper"
                style={{ offsetPath: `path('${hopD}')` } as CSSProperties}
              />
            )}
            {[...layout.left, ...layout.center, ...layout.right].map(n => {
              const isRoot = uncalled.includes(n.id)
              const isFocus = n.col === 'focus' || n.id === focus
              const inTrail = trail.includes(n.id)
              return (
                <g
                  key={`${n.col}:${n.id}`}
                  transform={`translate(${n.x}, ${n.y})`}
                  onClick={() => goTo(n.id, centerId ?? trail[trail.length - 1])}
                  style={{ cursor: 'pointer' }}
                >
                  <title>{n.id}</title>
                  <rect
                    width={NODE_W}
                    height={NODE_H}
                    rx="6"
                    className={`cg-node${isFocus ? ' focus' : ''}${isRoot ? ' root' : ''}${inTrail ? ' trail' : ''}`}
                  />
                  <text x={12} y={23} className="cg-node-label">
                    {shortNode(n.id, kind).slice(0, 28)}
                  </text>
                </g>
              )
            })}
          </svg>
          {leftIds.length === 0 && rightIds.length === 0 && (
            <div className="cg-empty">No nodes match this filter.</div>
          )}
        </div>

        <aside className="cg-detail">
          <div className="cg-panel-label">Selected</div>
          {detailId ? (
            <>
              <h3 className="cg-detail-title">{shortNode(detailId, kind)}</h3>
              <p className="cg-detail-path">{detailId}</p>
              {detailFn && (
                <p className="cg-detail-meta">
                  {detailFile}:{detailFn.lineno}
                </p>
              )}
              <div className="cg-detail-block">
                <div className="cg-panel-label">Calls</div>
                <ul>
                  {outgoing(graph, kind, detailId).length === 0 && <li className="cg-muted">None</li>}
                  {outgoing(graph, kind, detailId).map(id => (
                    <li key={id}>
                      <button type="button" className="cg-link" onClick={() => goTo(id, detailId)}>
                        {shortNode(id, kind)}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="cg-detail-block">
                <div className="cg-panel-label">Called by</div>
                <ul>
                  {incoming(graph, kind, detailId).length === 0 && (
                    <li className="cg-muted">Uncalled — BFS start</li>
                  )}
                  {incoming(graph, kind, detailId).map(id => (
                    <li key={id}>
                      <button type="button" className="cg-link" onClick={() => goTo(id, detailId)}>
                        {shortNode(id, kind)}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          ) : (
            <p className="cg-muted">Select a node to inspect callers and callees.</p>
          )}
        </aside>
      </div>
    </div>
  )
}
