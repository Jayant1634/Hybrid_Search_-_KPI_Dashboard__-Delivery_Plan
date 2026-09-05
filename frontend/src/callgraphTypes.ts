export interface GraphEdge {
  from: string
  to: string
}

export interface BfsBlock {
  roots: string[]
  layers: [string[], string[]]
  edges: GraphEdge[]
  hops: GraphEdge[]
  topo: string[]
  nodes: string[]
}

export interface FileMeta {
  language: string
  functions: string[]
  imports: string[]
  imported_by: string[]
  calls: string[]
  called_by: string[]
}

export interface FunctionMeta {
  file: string
  name: string
  qualname: string
  lineno: number
  calls: string[]
  called_by: string[]
}

export interface CallGraphDoc {
  generated_at: string
  stats: {
    file_count: number
    function_count: number
    uncalled_file_count: number
    uncalled_function_count: number
    file_edge_count: number
    function_edge_count: number
  }
  files: Record<string, FileMeta>
  functions: Record<string, FunctionMeta>
  uncalled_files: string[]
  uncalled_functions: string[]
  bfs_files: BfsBlock
  bfs_functions: BfsBlock
  topo_files: string[]
  topo_functions: string[]
  hops_files: GraphEdge[]
  hops_functions: GraphEdge[]
}
