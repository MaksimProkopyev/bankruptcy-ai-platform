"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Lead, Message } from "@/types/leadgen";
import { API_BASE } from "@/lib/leadgen-utils";
import MessageBubble from "@/components/leadgen/MessageBubble";
import MessageInput from "@/components/leadgen/MessageInput";
import LeadDataPanel from "@/components/leadgen/LeadDataPanel";
import ChannelBadge from "@/components/leadgen/ChannelBadge";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

interface Toast {
  id: number;
  message: string;
  type: "success" | "error";
}

let toastCounter = 0;

export default function LeadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [lead, setLead] = useState<Lead | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingLead, setLoadingLead] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(true);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  function showToast(message: string, type: "success" | "error" = "success") {
    const tid = ++toastCounter;
    setToasts((prev) => [...prev, { id: tid, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== tid));
    }, 4000);
  }

  const fetchLead = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/leads/${id}`);
      if (!res.ok) throw new Error();
      const data: Lead = await res.json();
      setLead(data);
    } catch {
      setLead(null);
    } finally {
      setLoadingLead(false);
    }
  }, [id]);

  const fetchMessages = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/leads/${id}/messages`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      const items: Message[] = Array.isArray(data)
        ? data
        : data.items ?? data.messages ?? [];
      setMessages(items);
    } catch {
      setMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  }, [id]);

  useEffect(() => {
    fetchLead();
    fetchMessages();
  }, [fetchLead, fetchMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSendMessage(content: string) {
    const res = await fetch(`${API_BASE}/api/v1/leads/${id}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content, direction: "outbound" }),
    });

    if (!res.ok) {
      showToast("Ошибка отправки сообщения", "error");
      throw new Error();
    }

    const newMsg: Message = await res.json();
    setMessages((prev) => [...prev, newMsg]);
  }

  function handleConvert() {
    showToast("Функция конвертации в разработке", "success");
  }

  if (loadingLead) {
    return (
      <div className="flex gap-6 h-full animate-pulse">
        <div className="flex-[3] bg-white rounded-xl shadow-card" />
        <div className="flex-[2] bg-white rounded-xl shadow-card" />
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-text-muted">Лид не найден</p>
        <Link
          href="/leadgen/pipeline"
          className="text-sm underline"
          style={{ color: "#C9A84C" }}
        >
          Вернуться в воронку
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-0" style={{ height: "calc(100vh - 48px)" }}>
      {/* Toast */}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="px-4 py-3 rounded-lg shadow-hover text-sm font-medium text-white"
            style={{
              background: t.type === "success" ? "#1D9E75" : "#E24B4A",
              minWidth: "240px",
            }}
          >
            {t.message}
          </div>
        ))}
      </div>

      {/* Back nav */}
      <div className="flex items-center gap-2 mb-4 flex-shrink-0">
        <Link
          href="/leadgen/pipeline"
          className="flex items-center gap-1.5 text-sm text-text-muted hover:text-primary transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Воронка
        </Link>
        <span className="text-text-muted">/</span>
        <span className="text-sm font-medium text-text">
          {lead.name ?? "Без имени"}
        </span>
      </div>

      {/* Two-column layout */}
      <div className="flex gap-6 flex-1 min-h-0">
        {/* Left: Chat (60%) */}
        <div
          className="flex-[3] flex flex-col bg-white rounded-xl shadow-card overflow-hidden min-h-0"
        >
          {/* Chat header */}
          <div
            className="flex items-center gap-3 px-5 py-4 border-b border-neutral flex-shrink-0"
            style={{ background: "#F8F7F4" }}
          >
            <div>
              <p
                className="font-semibold text-base"
                style={{ color: "#1B3A5C", fontFamily: "Georgia, serif" }}
              >
                {lead.name ?? "Без имени"}
              </p>
            </div>
            <ChannelBadge channel={lead.channel} showLabel size="md" />
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-5 py-4 min-h-0">
            {loadingMessages ? (
              <div className="flex flex-col gap-3 animate-pulse">
                {[...Array(4)].map((_, i) => (
                  <div
                    key={i}
                    className={`flex ${i % 2 === 0 ? "justify-start" : "justify-end"}`}
                  >
                    <div className="h-10 bg-gray-100 rounded-2xl w-48" />
                  </div>
                ))}
              </div>
            ) : messages.length === 0 ? (
              <div className="flex items-center justify-center h-32">
                <p className="text-sm text-text-muted">
                  История сообщений пуста
                </p>
              </div>
            ) : (
              messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Message input */}
          <div className="flex-shrink-0">
            <MessageInput onSend={handleSendMessage} />
          </div>
        </div>

        {/* Right: Lead data (40%) */}
        <div className="flex-[2] min-h-0 overflow-y-auto">
          <LeadDataPanel
            lead={lead}
            onUpdate={setLead}
            onSpam={() => router.push("/leadgen/pipeline")}
            onConvert={handleConvert}
            showToast={showToast}
          />
        </div>
      </div>
    </div>
  );
}
