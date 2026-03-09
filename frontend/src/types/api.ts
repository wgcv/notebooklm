export type Role = 'user' | 'assistant'

export interface ChatMessage {
  id: string
  role: Role
  content: string
}

export interface StreamRequestPayload {
  thread_id: string
  message: string
}

export interface DocumentItem {
  id: number
  thread_id: string
  documentUrl: string
  documentName: string
  createdAt: string
  updatedAt: string
}

export interface UploadDocumentResponse {
  id: number
  thread_id: string
  documentUrl: string
  documentName: string
  bucket: string
  key: string
  chunk_ids: string[]
}

export interface DeleteDocumentResponse {
  id: number
  thread_id: string
  documentUrl: string
  documentName: string
  bucket: string
  key: string
  deleted: boolean
}
