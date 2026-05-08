"use client";

import { useState, useRef, useEffect } from "react";
import { attachUtmToJson } from "@/lib/utm";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface ChatbotProps {
  apiUrl?: string;
  onQualificationComplete?: (data: any) => void;
}

const AI_CORE_URL = process.env.NEXT_PUBLIC_AI_CORE_URL || "http://localhost:8001";

export default function QualificationChatbot({ apiUrl, onQualificationComplete }: ChatbotProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [qualResult, setQualResult] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Send initial greeting when first opened
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      sendToAI([]);
    }
  }, [isOpen]);

  async function sendToAI(chatHistory: Message[]) {
    setLoading(true);

    try {
      const apiMessages = chatHistory.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // If no messages, send empty to get greeting
      const res = await fetch(`${apiUrl || AI_CORE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: apiMessages.length > 0 ? apiMessages : [{ role: "user", content: "Здравствуйте" }],
          session_id: sessionId,
        }),
      });

      if (!res.ok) throw new Error("AI service unavailable");

      const data = await res.json();
      setSessionId(data.session_id);

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.reply,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Handle qualification action
      if (data.action === "qualify" && data.action_data) {
        const bodyWithUtm = attachUtmToJson(data.action_data);
        const qualRes = await fetch(`${apiUrl || AI_CORE_URL}/qualify`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(bodyWithUtm),
        });

        if (qualRes.ok) {
          const result = await qualRes.json();
          setQualResult(result);
          onQualificationComplete?.(result);

          // Format result message
          const resultMsg = formatQualResult(result);
          const resultAssistantMsg: Message = {
            id: crypto.randomUUID(),
            role: "assistant",
            content: resultMsg,
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, resultAssistantMsg]);
        }
      }
    } catch (err) {
      // Fallback: use local qualification logic
      const fallbackMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Извините, сервис временно недоступен. Оставьте ваш телефон, и мы перезвоним в течение 15 минут.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, fallbackMsg]);
    } finally {
      setLoading(false);
    }
  }

  async function handleSend() {
    if (!input.trim() || loading) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setInput("");

    await sendToAI(newHistory);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  // Floating button when closed
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-accent text-text-on-dark rounded-full shadow-lg hover:bg-accent-hover transition-all hover:scale-110 flex items-center justify-center z-50"
        aria-label="Открыть чат"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[560px] bg-white rounded-2xl shadow-2xl border border-neutral flex flex-col z-50 overflow-hidden md:max-w-[calc(100vw-2rem)] md:w-auto md:left-4 md:right-4 md:bottom-4 md:top-auto md:h-[70vh]">
      {/* Header */}
      <div className="bg-primary-dark text-text-on-dark px-5 py-4 flex items-center justify-between flex-shrink-0">
        <div>
          <h3 className="font-semibold text-sm">Банкротство.AI</h3>
          <p className="text-text-on-dark-muted text-xs mt-0.5">Бесплатная оценка за 2 минуты</p>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="w-8 h-8 rounded-lg hover:bg-primary flex items-center justify-center transition-colors"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-primary text-text-on-dark rounded-br-md"
                  : "bg-surface-muted text-text-body rounded-bl-md"
              }`}
            >
              {msg.content.split("\n").map((line, i) => (
                <span key={i}>
                  {line}
                  {i < msg.content.split("\n").length - 1 && <br />}
                </span>
              ))}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-muted px-4 py-3 rounded-2xl rounded-bl-md">
              <div className="flex gap-1.5">
                <span className="w-2 h-2 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Qualification Result Card */}
      {qualResult && (
        <div className="mx-4 mb-3 p-4 bg-green-50 border border-green-200 rounded-xl flex-shrink-0">
          <p className="text-sm font-medium text-green-800 mb-2">
            {qualResult.is_eligible ? "Вы подходите под банкротство" : "Требуется доп. консультация"}
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs text-green-700">
            <div>
              <span className="text-green-500">Стоимость:</span>{" "}
              {qualResult.estimated_cost_min?.toLocaleString()}–{qualResult.estimated_cost_max?.toLocaleString()} ₽
            </div>
            <div>
              <span className="text-green-500">Срок:</span>{" "}
              {qualResult.estimated_duration_months_min}–{qualResult.estimated_duration_months_max} мес.
            </div>
          </div>
          <button className="mt-3 w-full py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors">
            Записаться на консультацию
          </button>
        </div>
      )}

      {/* Input */}
      <div className="p-3 border-t border-neutral flex-shrink-0">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Напишите сообщение..."
            disabled={loading}
            className="flex-1 px-4 py-2.5 bg-surface border border-neutral rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="w-10 h-10 bg-accent text-text-on-dark rounded-xl hover:bg-accent-hover disabled:opacity-50 flex items-center justify-center transition-colors flex-shrink-0"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}

function formatQualResult(result: any): string {
  const parts: string[] = [];

  if (result.is_eligible) {
    parts.push("Отлично! На основе ваших данных вы подходите под процедуру банкротства.");
  } else {
    parts.push("На основе предварительного анализа ваша ситуация требует дополнительной проверки.");
  }

  if (result.procedure_type === "asset_realization") {
    parts.push("\nРекомендуемая процедура: реализация имущества (списание долгов).");
  } else if (result.procedure_type === "restructuring") {
    parts.push("\nРекомендуемая процедура: реструктуризация долгов.");
  }

  if (result.estimated_cost_min && result.estimated_cost_max) {
    parts.push(`\nПримерная стоимость: ${result.estimated_cost_min.toLocaleString()}–${result.estimated_cost_max.toLocaleString()} ₽`);
  }

  if (result.risk_factors?.length > 0) {
    parts.push(`\nФакторы риска: ${result.risk_factors.join(", ")}`);
  }

  parts.push("\nХотите записаться на бесплатную консультацию с юристом?");

  return parts.join("");
}
