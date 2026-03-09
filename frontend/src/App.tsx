import { useState } from 'react'
import './App.css'
import { ChatPanel } from './components/ChatPanel'
import { DocumentsPanel } from './components/DocumentsPanel'

const THREAD_STORAGE_KEY = 'notebooklm.activeThreadId'

function createThreadId(): string {
  const generated =
    typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(16).slice(2)}`
  sessionStorage.setItem(THREAD_STORAGE_KEY, generated)
  return generated
}

function App() {
  const [threadId, setThreadId] = useState<string>(() => createThreadId())

  const handleNewThread = () => {
    setThreadId(createThreadId())
  }

  return (
    <div className="app-shell">
      <aside className="left-pane">
        <DocumentsPanel threadId={threadId} />
      </aside>
      <div className="right-pane">
        <header className="topbar">
          <div>
            <h1>Notebook Chat</h1>
            <p>Thread: {threadId}</p>
          </div>
          <button
            type="button"
            className="new-thread-btn"
            onClick={handleNewThread}
            title="Create new thread"
            aria-label="Create new thread"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 5v14M5 12h14" />
            </svg>
          </button>
        </header>
        <ChatPanel threadId={threadId} />
      </div>
    </div>
  )
}

export default App
