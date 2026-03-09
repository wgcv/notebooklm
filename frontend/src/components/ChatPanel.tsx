import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { streamChat } from '../services/api'
import type { ChatMessage } from '../types/api'

interface ChatPanelProps {
  threadId: string
}

function createId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: createId(),
    role: 'assistant',
    content: 'Upload documents on the left, then ask a question about them here.',
  },
]

export function ChatPanel({ threadId }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES)
  const [input, setInput] = useState('')

  useEffect(() => {
    setMessages([
      {
        id: createId(),
        role: 'assistant',
        content: 'Upload documents on the left, then ask a question about them here.',
      },
    ])
    setError(null)
  }, [threadId])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const endRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isStreaming])

  const sendMessage = async () => {
    const messageText = input.trim()
    if (!messageText || isStreaming) {
      return
    }

    setInput('')
    setError(null)
    setIsStreaming(true)

    const userMessage: ChatMessage = {
      id: createId(),
      role: 'user',
      content: messageText,
    }
    const assistantMessageId = createId()
    const assistantPlaceholder: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
    }

    setMessages((prev) => [...prev, userMessage, assistantPlaceholder])

    try {
      const finalAnswer = await streamChat(
        {
          thread_id: threadId,
          message: messageText,
        },
        (chunk) => {
          setMessages((prev) =>
            prev.map((message) =>
              message.id === assistantMessageId
                ? { ...message, content: `${message.content}${chunk}` }
                : message,
            ),
          )
        },
      )

      if (!finalAnswer.trim()) {
        setMessages((prev) =>
          prev.map((message) =>
            message.id === assistantMessageId
              ? { ...message, content: 'No response returned from the model.' }
              : message,
          ),
        )
      }
    } catch (streamError) {
      const message = streamError instanceof Error ? streamError.message : 'Failed to stream response'
      setError(message)
      setMessages((prev) =>
        prev.map((entry) =>
          entry.id === assistantMessageId
            ? { ...entry, content: 'Unable to complete this response.' }
            : entry,
        ),
      )
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <section className="panel panel-chat">
      <header className="panel-header">
        <h2>Chat</h2>
        <p>{isStreaming ? 'Assistant is typing...' : 'Ask about your uploaded files'}</p>
      </header>

      <div className="chat-scroll">
        {messages.map((message) => (
          <article key={message.id} className={`message message-${message.role}`}>
            <span className="message-role">{message.role === 'user' ? 'You' : 'Assistant'}</span>
            {message.content ? (
              <div className="message-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
              </div>
            ) : (
              <p className="message-placeholder">...</p>
            )}
          </article>
        ))}
        <div ref={endRef} />
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="composer">
        <textarea
          value={input}
          placeholder="Ask a question..."
          onChange={(event) => {
            setInput(event.target.value)
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              void sendMessage()
            }
          }}
          rows={3}
          disabled={isStreaming}
        />
        <button
          type="button"
          disabled={isStreaming || !input.trim()}
          onClick={() => {
            void sendMessage()
          }}
        >
          {isStreaming ? 'Streaming...' : 'Send'}
        </button>
      </div>
    </section>
  )
}
