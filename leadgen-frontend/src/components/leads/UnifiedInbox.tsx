"use client";

import { useState, useEffect, useRef } from "react";
import { getMessages, sendMessage, Message } from "@/lib/api";
import { Send } from "lucide-react";

interface Props {
  leadId: string;
}

export default function UnifiedInbox({ leadId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getMessages(leadId)
      .then(data => setMessages(data))
      .catch(() => {});
  }, [leadId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim() || sending) return;
    setSending(true);
    try {
      const msg = await sendMessage(leadId, text.trim());
      setMessages(prev => [...prev, msg]);
      setText("");
    } finally { setSending(false); }
  }

  return (
    <div className="bg-white rounded-xl border border-neutral shadow-card flex flex-col h-full">
      <div className="px-5 py-4 border-b border-neutral">
        <h2 className="font-semibold text-text">Переписка</h2>
      </div>

      {/* Messages list */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-center text-text-muted text-sm py-8">Нет сообщений</p>
        )}
        {messages.map(msg => (
          <div
            key={msg.id}
            className={`flex ${msg.direction === "outbound" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm ${
                msg.direction === "outbound"
                  ? "bg-primary text-text-on-dark rounded-br-sm"
                  : "bg-surface text-text-body rounded-bl-sm"
              }`}
            >
              <p>{msg.text}</p>
              <p className={`text-xs mt-1 ${
                msg.direction === "outbound" ? "text-text-on-dark-muted" : "text-text-muted"
              }`}>
                {new Date(msg.created_at).toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })}
                {msg.channel && <span className="ml-1 opacity-70">· {msg.channel}</span>}
              </p>
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Send form */}
      <form onSubmit={handleSend} className="px-5 py-4 border-t border-neutral flex gap-3">
        <input
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Написать сообщение..."
          className="flex-1 px-4 py-2.5 border border-neutral rounded-xl text-sm focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary"
        />
        <button
          type="submit"
          disabled={!text.trim() || sending}
          className="px-4 py-2.5 bg-accent text-text-on-dark rounded-xl hover:bg-accent-hover disabled:opacity-50 transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}
