import { useCallback, useEffect, useMemo, useState, type ChangeEvent, type DragEvent } from 'react'
import { deleteDocument, listDocuments, uploadDocument } from '../services/api'
import type { DocumentItem } from '../types/api'

interface DocumentsPanelProps {
  threadId: string
}

function formatDate(value: string): string {
  const utcValue = /Z$|[+-]\d{2}(:\d{2})?$/.test(value) ? value : `${value}Z`
  const date = new Date(utcValue)
  if (Number.isNaN(date.getTime())) {
    return 'Unknown date'
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  }).format(date)
}

export function DocumentsPanel({ threadId }: DocumentsPanelProps) {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uploadSummary, setUploadSummary] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const loadDocuments = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const items = await listDocuments(threadId)
      setDocuments(items)
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : 'Failed to load documents'
      setError(message)
    } finally {
      setIsLoading(false)
    }
  }, [threadId])

  useEffect(() => {
    void loadDocuments()
  }, [loadDocuments])

  const ALLOWED_EXTENSIONS = useMemo(() => ['.txt', '.pdf', '.docx'], [])

  const processFiles = useCallback(
    async (files: File[]) => {
      const filtered = files.filter((file) => {
        const ext = '.' + (file.name.split('.').pop() ?? '').toLowerCase()
        return ALLOWED_EXTENSIONS.includes(ext)
      })

      if (filtered.length === 0) {
        return
      }

      setIsUploading(true)
      setError(null)
      setUploadSummary(null)

      let uploadedCount = 0
      const failedFiles: string[] = []

      for (const file of filtered) {
        try {
          await uploadDocument(threadId, file)
          uploadedCount += 1
        } catch {
          failedFiles.push(file.name)
        }
      }

      if (uploadedCount > 0) {
        await loadDocuments()
      }

      if (failedFiles.length === 0) {
        setUploadSummary(`Uploaded ${uploadedCount} file${uploadedCount === 1 ? '' : 's'}.`)
      } else {
        const failedMessage = failedFiles.join(', ')
        setUploadSummary(
          `Uploaded ${uploadedCount}/${filtered.length}. Failed: ${failedMessage}.`,
        )
      }

      setIsUploading(false)
    },
    [threadId, loadDocuments, ALLOWED_EXTENSIONS],
  )

  const handleUpload = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files ? Array.from(event.target.files) : []
    event.target.value = ''
    void processFiles(files)
  }

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    if (!isUploading) {
      setIsDragging(true)
    }
  }

  const handleDragLeave = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    if (!event.currentTarget.contains(event.relatedTarget as Node)) {
      setIsDragging(false)
    }
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    event.stopPropagation()
    setIsDragging(false)
    if (isUploading) return
    const files = event.dataTransfer.files ? Array.from(event.dataTransfer.files) : []
    void processFiles(files)
  }

  const handleDelete = async (documentId: number) => {
    setDeletingId(documentId)
    setError(null)

    try {
      await deleteDocument(documentId)
      setDocuments((prev) => prev.filter((doc) => doc.id !== documentId))
    } catch (deleteError) {
      const message = deleteError instanceof Error ? deleteError.message : 'Failed to delete document'
      setError(message)
    } finally {
      setDeletingId(null)
    }
  }

  const documentCountLabel = useMemo(() => {
    if (documents.length === 1) {
      return '1 document'
    }

    return `${documents.length} documents`
  }, [documents.length])

  return (
    <section className="panel panel-documents">
      <header className="panel-header">
        <h2>Documents</h2>
        <p>{documentCountLabel}</p>
      </header>

      <div
        className={`upload-box ${isDragging ? 'upload-box--dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <label className="upload-label" htmlFor="upload-input">
          Upload files or drag and drop
        </label>
        <input
          id="upload-input"
          type="file"
          accept=".txt,.pdf,.docx"
          multiple
          disabled={isUploading}
          onChange={handleUpload}
        />
        <small>Supported: TXT, PDF, DOCX</small>
      </div>

      {isLoading && <p className="muted">Loading documents...</p>}
      {isUploading && <p className="muted">Uploading files...</p>}
      {uploadSummary && <p className="muted">{uploadSummary}</p>}
      {error && <p className="error-text">{error}</p>}

      <ul className="document-list">
        {documents.map((document) => (
          <li key={document.id} className="document-item">
            <div className="document-meta">
              <strong title={document.documentName}>{document.documentName}</strong>
              <span>{formatDate(document.createdAt)}</span>
            </div>
            <button
              type="button"
              className="danger-button"
              disabled={deletingId === document.id}
              onClick={() => {
                void handleDelete(document.id)
              }}
            >
              {deletingId === document.id ? 'Deleting...' : 'Delete'}
            </button>
          </li>
        ))}
      </ul>

      {!isLoading && documents.length === 0 && (
        <p className="muted">No files yet. Upload documents to ground the chat.</p>
      )}
    </section>
  )
}
