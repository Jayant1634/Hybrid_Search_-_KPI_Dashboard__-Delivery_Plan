const STOPWORDS = new Set([
  'the', 'a', 'an', 'and', 'or', 'but', 'if', 'of', 'to', 'in', 'on', 'at',
  'by', 'for', 'with', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
  'it', 'its', 'this', 'that', 'these', 'those', 'he', 'she', 'they', 'we',
  'you', 'his', 'her', 'their', 'not', 'from', 'into',
])

export function queryTerms(query: string): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const match of query.toLowerCase().match(/\w+/g) ?? []) {
    if (match.length < 2 || STOPWORDS.has(match) || seen.has(match)) continue
    seen.add(match)
    out.push(match)
  }
  return out
}

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

export function decodeSnippet(snippet: string): string {
  return snippet
    .replace(/<\/?em>/gi, '')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
}

function termMatchesWord(term: string, word: string): boolean {
  if (!term || !word) return false
  if (word === term) return true
  return term.length >= 3 && word.includes(term)
}

export function highlightContaining(text: string, query: string): string {
  const needles = queryTerms(query)
  const escaped = escapeHtml(text)
  if (needles.length === 0) return escaped
  return escaped.replace(/\w+/g, word => {
    const low = word.toLowerCase()
    return needles.some(term => termMatchesWord(term, low)) ? `<em>${word}</em>` : word
  })
}
