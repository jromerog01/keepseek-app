const BATCH_BYTES = 16 * 1024 * 1024

export async function readBody(response, onProgress, fallbackTotal = 0) {
  const type = response.headers.get('Content-Type') || ''
  const total = Number(response.headers.get('Content-Length')) || fallbackTotal

  if (!response.body) return new Blob([await response.arrayBuffer()], { type })

  // Cada tanda se convierte en un Blob (el navegador puede respaldarlo en disco) y se libera la memoria JS.
  const reader = response.body.getReader()
  const parts = []
  let batch = []
  let batchBytes = 0
  let received = 0
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    batch.push(value)
    batchBytes += value.length
    received += value.length
    onProgress({ received, total })
    if (batchBytes >= BATCH_BYTES) {
      parts.push(new Blob(batch))
      batch = []
      batchBytes = 0
    }
  }
  if (batch.length) parts.push(new Blob(batch))
  return new Blob(parts, { type })
}
