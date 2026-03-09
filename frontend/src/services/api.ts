import type {
  DeleteDocumentResponse,
  DocumentItem,
  StreamRequestPayload,
  UploadDocumentResponse,
} from '../types/api'

const API_BASE = '/api'

async function parseApiError(response: Response): Promise<string> {
  const fallback = `Request failed with status ${response.status}`
  const contentType = response.headers.get('content-type') ?? ''

  if (contentType.includes('application/json')) {
    const payload = (await response.json()) as { detail?: unknown }
    if (typeof payload.detail === 'string') {
      return payload.detail
    }

    if (Array.isArray(payload.detail) && payload.detail.length > 0) {
      const firstDetail = payload.detail[0] as { msg?: string }
      if (typeof firstDetail?.msg === 'string') {
        return firstDetail.msg
      }
    }
  }

  const text = await response.text()
  return text || fallback
}

export async function listDocuments(threadId: string): Promise<DocumentItem[]> {
  const response = await fetch(`${API_BASE}/documents?thread_id=${encodeURIComponent(threadId)}`)
  if (!response.ok) {
    throw new Error(await parseApiError(response))
  }

  return (await response.json()) as DocumentItem[]
}

export async function uploadDocument(
  threadId: string,
  file: File,
): Promise<UploadDocumentResponse> {
  const formData = new FormData()
  formData.append('thread_id', threadId)
  formData.append('file', file)

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error(await parseApiError(response))
  }

  return (await response.json()) as UploadDocumentResponse
}

export async function deleteDocument(documentId: number): Promise<DeleteDocumentResponse> {
  const response = await fetch(`${API_BASE}/upload/${documentId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    throw new Error(await parseApiError(response))
  }

  return (await response.json()) as DeleteDocumentResponse
}

export async function streamChat(
  payload: StreamRequestPayload,
  onChunk: (chunk: string) => void,
): Promise<string> {
  const response = await fetch(`${API_BASE}/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(await parseApiError(response))
  }

  if (!response.body) {
    const text = await response.text()
    if (text) {
      onChunk(text)
    }
    return text
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let accumulated = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }

    const chunk = decoder.decode(value, { stream: true })
    if (!chunk) {
      continue
    }

    accumulated += chunk
    onChunk(chunk)
  }

  const tailChunk = decoder.decode()
  if (tailChunk) {
    accumulated += tailChunk
    onChunk(tailChunk)
  }

  return accumulated
}
