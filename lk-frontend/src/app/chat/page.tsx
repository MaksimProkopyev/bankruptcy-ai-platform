"use client";
import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
function getCookie(n: string): string { if (typeof document === "undefined") return ""; const m = document.cookie.match(new RegExp("(^| )" + n + "=([^;]+)")); return m ? decodeURIComponent(m[2]) : ""; }
function hdr() { return { Authorization: `Bearer ${getCookie("client_token")}`, "Content-Type": "application/json" }; }

interface Msg { role: "user" | "assistant" | "staff"; content: string; date?: string; }

export default function LkChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // Load previous messages + add greeting
  useEffect(() => {
    const token = getCookie("client_token");
    if (!token) { router.push("/login"); return; }

    fetch(`${API}/cabinet/messages`, { headers: hdr() })
      .then(r => r.json())
      .then(data => {
        const prev: Msg[] = (Array.isArray(data) ? data : []).map((m: any) => ({
          role: m.is_ai ? "assistant" : m.direction === "inbound" ? "user" : "staff",
          content: m.content,
          date: m.date,
        }));
        if (prev.length === 0) {
          prev.push({ role: "assistant", content: "Здравствуйте! Я AI-ассистент по вашему делу. Задайте любой вопрос — о статусе дела, документах, сроках. Или я передам вопрос юристу." });
        }
        setMessages(prev);
      })
      .catch(() => {
        setMessages([{ role: "assistant", content: "Здравствуйте! Задайте вопрос о вашем деле." }]);
      })
      .finally(() => setInitialLoading(false));
  }, [router]);

  async function send() {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setMessages(prev => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API}/cabinet/chat?message=${encodeURIComponent(text)}`, {
        method: "POST",
        headers: hdr(),
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.reply || "Ответ не получен." }]);

      await fetch(`${API}/cabinet/messages`, {
        method: "POST",
        headers: hdr(),
        body: JSON.stringify({ content: text }),
      }).catch(() => {});
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Ошибка связи. Позвоните: 8 800 123-45-67." }]);
    } finally {
      setLoading(false);
    }
  }

  const QUICK_QUESTIONS = [
    "Какой сейчас статус моего дела?",
    "Когда следующее заседание?",
    "Какие документы ещё нужны?",
    "Сколько я должен кредиторам?",
  ];

  if (initialLoading) return <div className="py-12 text-center text-text-muted">Загрузка чата...</div>;

  return (
    <div className="flex flex-col" style={{ height: "calc(100vh - 200px)" }}>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-xl font-semibold text-text">Чат</h1>
        <span className="text-xs text-success flex items-center gap-1">
          <span className="w-2 h-2 bg-success rounded-full" /> AI-ассистент онлайн
        </span>
      </div>

      {/* Quick questions */}
      {messages.length <= 1 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {QUICK_QUESTIONS.map(q => (
            <button key={q} onClick={() => { setInput(q); }}
              className="px-3 py-1.5 bg-primary/10 text-primary text-xs rounded-full hover:bg-primary/20 transition-colors">
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 bg-white rounded-2xl border border-neutral p-4 overflow-y-auto space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm ${
              m.role === "user"
                ? "bg-primary text-text-on-dark rounded-br-md"
                : m.role === "staff"
                ? "bg-success/10 text-text rounded-bl-md border border-success/20"
                : "bg-surface-muted text-text rounded-bl-md"
            }`}>
              {m.role === "staff" && <p className="text-xs text-success font-medium mb-1">Юрист</p>}
              {m.content.split("\n").map((line, j) => <span key={j}>{line}{j < m.content.split("\n").length - 1 && <br />}</span>)}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-surface-muted px-4 py-3 rounded-2xl rounded-bl-md flex gap-1">
              <span className="w-2 h-2 bg-text-muted rounded-full animate-bounce" />
              <span className="w-2 h-2 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 bg-text-muted rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2 mt-4">
        <input type="text" value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && send()}
          placeholder="Задайте вопрос..."
          className="flex-1 px-4 py-3 bg-white border border-neutral rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary" />
        <button onClick={send} disabled={loading || !input.trim()}
          className="px-5 py-3 bg-accent text-text-on-dark rounded-xl text-sm font-medium hover:bg-accent-hover disabled:opacity-50">
          Отправить
        </button>
      </div>
    </div>
  );
}
