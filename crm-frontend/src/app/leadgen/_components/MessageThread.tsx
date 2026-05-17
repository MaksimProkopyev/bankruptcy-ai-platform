import { LeadMessage } from '@/lib/leadgen-api'
import { useEffect, useRef } from 'react'

export default function MessageThread({ messages }: { messages: LeadMessage[] }) {
  const bottomRef = useRef<HTMLDivElement>(null)
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  return (
    <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-3" style={{ backgroundColor: '#F8F7F4' }}>
      {messages.length === 0 && (
        <div className="flex items-center justify-center h-32">
          <p className="text-sm text-gray-400">История сообщений пуста</p>
        </div>
      )}
      {messages.map(msg => (
        <div key={msg.id} className={`flex ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}>
          <div
            className={`max-w-sm rounded-2xl px-4 py-2 text-sm ${
              msg.direction === 'outbound' ? 'text-white' : 'bg-white text-gray-800 shadow-sm'
            }`}
            style={msg.direction === 'outbound' ? { backgroundColor: '#1B3A5C' } : {}}
          >
            <p>{msg.content}</p>
            <p className={`text-xs mt-1 ${msg.direction === 'outbound' ? 'text-blue-200' : 'text-gray-400'}`}>
              {new Date(msg.sent_at).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
