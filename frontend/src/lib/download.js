export async function readBody(response, onProgress, fallbackTotal = 0) {
  const type = response.headers.get('Content-Type') || ''
  const total = Number(response.headers.get('Content-Length')) || fallbackTotal

  if (!response.body) return new Blob([await response.arrayBuffer()], { type })

  const reader = response.body.getReader()
  const chunks = []
  let received = 0
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
    received += value.length
    onProgress({ received, total })
  }
  return new Blob(chunks, { type })
}
