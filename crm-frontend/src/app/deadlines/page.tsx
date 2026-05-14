"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatDate } from "@/lib/case-utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface DeadlineItem {
  id: string;
  title: string;
  due_date: string;
  priority: string;
  status: string;
  case_id: string;
  case_number?: string;
}

export default function DeadlinesPage() {
  const [deadlines, setDeadlines] = useState<DeadlineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "overdue" | "upcoming">("upcoming");

  useEffect(() => {
    const token = localStorage.getItem("token");
    fetch(`${API_URL}/cases/?per_page=100`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.json())
      .then(async (cases) => {
        const allDeadlines: DeadlineItem[] = [];
        for (const c of cases.slice(0, 50)) {
          try {
            const res = await fetch(`${API_URL}/cases/${c.id}`, {
              headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            const detail = await res.json();
            for (const d of detail.deadlines || []) {
              allDeadlines.push({ ...d, case_id: c.id, case_number: c.case_number });
            }
          } catch {}
        }
        allDeadlines.sort((a, b) => new Date(a.due_date).getTime() - new Date(b.due_date).getTime());
        setDeadlines(allDeadlines);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const now = new Date();
  const filtered = deadlines.filter((d) => {
    if (filter === "overdue") return d.status === "overdue" || new Date(d.due_date) < now;
    if (filter === "upcoming") return d.status === "pending" && new Date(d.due_date) >= now;
    return true;
  });

  const priorityStyles: Record<string, string> = {
    critical: "bg-red-100 text-red-700 border-l-red-500",
    high: "bg-orange-50 text-orange-700 border-l-orange-400",
    medium: "bg-white text-gray-700 border-l-blue-400",
    low: "bg-white text-gray-500 border-l-gray-300",
  };

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Процессуальные сроки</h1>

      <div className="flex gap-2 mb-6">
        {(["upcoming", "overdue", "all"] as const).map((f) => (
          <button key={f} onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-sm rounded-lg border ${filter === f ? "bg-primary-light border-primary text-primary-dark font-medium" : "bg-white border-gray-200 text-gray-600"}`}>
            {f === "upcoming" ? "Предстоящие" : f === "overdue" ? "Просроченные" : "Все"}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-gray-400">Загрузка...</p>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400">
          Нет дедлайнов
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((d) => {
            const isOverdue = new Date(d.due_date) < now && d.status !== "completed";
            const daysLeft = Math.ceil((new Date(d.due_date).getTime() - now.getTime()) / 86400000);

            return (
              <div key={d.id} className={`bg-white rounded-lg border border-gray-200 border-l-4 p-4 ${priorityStyles[d.priority] || ""}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{d.title}</p>
                    <div className="flex items-center gap-3 mt-1">
                      <Link href={`/cases/${d.case_id}`} className="text-xs text-primary hover:underline">
                        {d.case_number || d.case_id.slice(0, 8)}
                      </Link>
                      <span className="text-xs text-gray-400">{formatDate(d.due_date)}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    {isOverdue ? (
                      <span className="text-sm font-medium text-red-600">Просрочено</span>
                    ) : (
                      <span className={`text-sm font-medium ${daysLeft <= 3 ? "text-orange-600" : "text-gray-600"}`}>
                        {daysLeft} дн.
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
