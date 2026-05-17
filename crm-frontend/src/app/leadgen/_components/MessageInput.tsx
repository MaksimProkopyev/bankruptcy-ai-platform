'use client'
import { useState } from 'react'

export default function MessageInput({ onSend }: { onSend: (text: string) => Promise<void> }) {
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)

  const handle = async () => {
    if (!text.trim()) return
    setSending(true)
    try { await onSend(text); setText('') }
    finally { setSending(false) }
  }

  return (
    <div className="border-t bg-white px-4 py-3 flex gap-3">
      <input
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handle()}
        placeholder="Сообщение..."
        className="flex-1 border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#1B3A5C]"
      />
      <button
        onClick={handle}
        disabled={sending || !text.trim()}
        className="px-5 py-2 rounded-lg text-sm text-white font-medium disabled:opacity-40"
        style={{ backgroundColor: '#1B3A5C' }}
      >
        {sending ? '...' : 'Отправить'}
      </button>
    </div>
  )
}
