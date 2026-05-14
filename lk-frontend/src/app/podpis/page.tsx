"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
function getCookie(n: string) { if (typeof document === "undefined") return ""; const m = document.cookie.match(new RegExp("(^| )" + n + "=([^;]+)")); return m ? decodeURIComponent(m[2]) : ""; }
function hdr() { return { Authorization: `Bearer ${getCookie("client_token")}`, "Content-Type": "application/json" }; }

interface DocToSign {
  id: string;
  title: string;
  status: string;
  created_at: string;
}

export default function LkSigningPage() {
  const router = useRouter();
  const [docs, setDocs] = useState<DocToSign[]>([]);
  const [loading, setLoading] = useState(true);
  const [signingDoc, setSigningDoc] = useState<string | null>(null);
  const [signatureId, setSignatureId] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"list" | "code" | "done">("list");
  const [error, setError] = useState("");
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    const token = getCookie("client_token");
    if (!token) { router.push("/login"); return; }
    fetch(`${API}/cabinet/documents-to-sign`, { headers: hdr() })
      .then(r => r.json())
      .then(d => setDocs(d.documents || []))
      .catch(() => router.push("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  async function requestCode(docId: string) {
    setError("");
    setProcessing(true);
    try {
      const res = await fetch(`${API}/cabinet/sign/request-code?draft_id=${docId}`, { method: "POST", headers: hdr() });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Ошибка");
      setSignatureId(data.signature_id);
      setSigningDoc(docId);
      setStep("code");
    } catch (e: any) { setError(e.message); }
    finally { setProcessing(false); }
  }

  async function verifyCode() {
    if (!signatureId || code.length !== 6) return;
    setError("");
    setProcessing(true);
    try {
      const res = await fetch(`${API}/cabinet/sign/verify?signature_id=${signatureId}&code=${code}`, { method: "POST", headers: hdr() });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Неверный код");
      setStep("done");
      setDocs(prev => prev.filter(d => d.id !== signingDoc));
    } catch (e: any) { setError(e.message); }
    finally { setProcessing(false); }
  }

  if (loading) return <div className="py-12 text-center text-text-muted">Загрузка...</div>;

  return (
    <div>
      <h1 className="text-xl font-semibold text-text mb-2">Подписание документов</h1>
      <p className="text-sm text-text-muted mb-6">
        Для подписания мы отправим SMS-код на ваш телефон. Это юридически равнозначно собственноручной подписи (ФЗ-63, ст. 6).
      </p>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>
      )}

      {step === "done" && (
        <div className="mb-6 p-5 bg-green-50 border border-green-200 rounded-2xl text-center">
          <p className="text-lg font-semibold text-green-700">✅ Документ подписан!</p>
          <p className="text-sm text-green-600 mt-1">Подпись зафиксирована. Юрист получил уведомление.</p>
          <button onClick={() => { setStep("list"); setCode(""); setSignatureId(null); }}
            className="mt-4 text-sm text-green-700 underline">Вернуться к списку</button>
        </div>
      )}

      {step === "code" && (
        <div className="bg-white rounded-2xl border border-primary/20 p-6 mb-6">
          <h2 className="text-base font-semibold text-text mb-4">Введите код из SMS</h2>
          <p className="text-sm text-text-muted mb-4">
            Код отправлен на ваш телефон. Действителен 5 минут.
          </p>
          <input
            type="text"
            value={code}
            onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
            placeholder="123456"
            maxLength={6}
            className="w-full px-4 py-3 border border-neutral rounded-xl text-center text-2xl tracking-widest mb-4"
            autoFocus
          />
          <div className="flex gap-3">
            <button onClick={verifyCode} disabled={processing || code.length !== 6}
              className="flex-1 py-3 bg-accent text-white rounded-xl text-sm font-semibold disabled:opacity-50">
              {processing ? "Проверка..." : "Подписать"}
            </button>
            <button onClick={() => { setStep("list"); setCode(""); }}
              className="px-4 py-3 text-text-muted text-sm">Отмена</button>
          </div>
        </div>
      )}

      {step === "list" && (
        <>
          {docs.length === 0 ? (
            <div className="bg-white rounded-2xl border border-neutral p-8 text-center">
              <p className="text-text-muted">Нет документов на подписание</p>
              <p className="text-xs text-text-muted mt-1">Когда юрист подготовит документ, он появится здесь</p>
            </div>
          ) : (
            <div className="space-y-3">
              {docs.map(d => (
                <div key={d.id} className="bg-white rounded-2xl border border-primary/20 p-5 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-text">{d.title}</p>
                    <p className="text-xs text-text-muted mt-1">
                      {d.created_at ? new Date(d.created_at).toLocaleDateString("ru-RU") : ""}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button className="px-3 py-2 bg-surface-muted text-text-muted rounded-xl text-xs">Просмотреть</button>
                    <button onClick={() => requestCode(d.id)} disabled={processing}
                      className="px-4 py-2 bg-accent text-white rounded-xl text-xs font-semibold disabled:opacity-50">
                      {processing ? "..." : "Подписать"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      <div className="mt-8">
        <h2 className="text-sm font-semibold text-text-muted uppercase mb-3">Подписанные документы</h2>
        <div className="bg-white rounded-2xl border border-neutral p-5 text-center text-sm text-text-muted">
          Подписанные документы доступны в разделе «Документы»
        </div>
      </div>
    </div>
  );
}
