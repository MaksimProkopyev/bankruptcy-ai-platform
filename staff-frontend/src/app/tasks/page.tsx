"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPatch } from "@/lib/api";

interface TaskItem {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  due_date?: string;
  case_id?: string;
  case_number?: string;
  created_at: string;
}

const STATUS_OPTIONS = [
  { value: "", label: "Все (кроме done)" },
  { value: "new", label: "Новые" },
  { value: "in_progress", label: "В работе" },
  { value: "all", label: "Все" },
];

const PRIORITY_OPTIONS = [
  { value: "", label: "Любой приоритет" },
  { value: "high", label: "Высокий" },
  { value: "medium", label: "Средний" },
  { value: "low", label: "Низкий" },
];

const STATUS_BADGE: Record<string, string> = {
  new: "bg-gray-100 text-gray-600",
  in_progress: "bg-blue-100 text-blue-700",
  done: "bg-green-100 text-green-700",
};

const STATUS_LABELS: Record<string, string> = {
  new: "Новая",
  in_progress: "В работе",
  done: "Выполнена",
};

const PRIORITY_BADGE: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-gray-100 text-gray-500",
};

const PRIORITY_LABELS: Record<string, string> = {
  high: "Высокий",
  medium: "Средний",
  low: "Низкий",
};

const NEXT_STATUS: Record<string, string | null> = {
  new: "in_progress",
  in_progress: "done",
  done: "in_progress",
};

const NEXT_LABEL: Record<string, string> = {
  new: "Взять в работу",
  in_progress: "Завершить",
  done: "Вернуть в работу",
};

function isOverdue(due_date?: string, status?: string): boolean {
  if (!due_date || status === "done") return false;
  return new Date(due_date) < new Date();
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [updating, setUpdating] = useState<string | null>(null);

  function fetchTasks() {
    const params = new URLSearchParams();
    if (statusFilter) params.set("status", statusFilter);
    if (priorityFilter) params.set("priority", priorityFilter);
    setLoading(true);
    apiGet(`/staff/me/tasks?${params.toString()}`)
      .then((d) => setTasks(Array.isArray(d) ? d : []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchTasks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, priorityFilter]);

  async function handleStatusChange(taskId: string, newStatus: string) {
    setUpdating(taskId);
    try {
      const updated = await apiPatch(`/staff/me/tasks/${taskId}/status`, {
        status: newStatus,
      });
      if (updated) {
        setTasks((prev) =>
          prev.map((t) => (t.id === taskId ? { ...t, ...updated } : t))
        );
      }
    } catch (e) {
      console.error(e);
    } finally {
      setUpdating(null);
    }
  }

  const overdueCount = tasks.filter((t) => isOverdue(t.due_date, t.status)).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#1B3A5C] font-heading">
            Мои задачи
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {tasks.length} задач
            {overdueCount > 0 && (
              <span className="text-red-500"> · {overdueCount} просрочено</span>
            )}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="flex gap-1 bg-gray-100 rounded-lg p-0.5">
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s.value}
              onClick={() => setStatusFilter(s.value)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                statusFilter === s.value
                  ? "bg-white shadow-sm text-gray-900 font-medium"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white text-gray-700"
        >
          {PRIORITY_OPTIONS.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-[#1B3A5C]">
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Задача
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Дело
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Приоритет
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Срок
              </th>
              <th className="text-left px-4 py-3 text-xs font-medium text-white/60 uppercase tracking-wide">
                Статус
              </th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {loading ? (
              <tr>
                <td colSpan={6} className="text-center py-12 text-gray-400">
                  Загрузка...
                </td>
              </tr>
            ) : tasks.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-12 text-gray-400">
                  Задач нет 🎉
                </td>
              </tr>
            ) : (
              tasks.map((task) => {
                const overdueMark = isOverdue(task.due_date, task.status);
                const nextStatus = NEXT_STATUS[task.status];
                return (
                  <tr
                    key={task.id}
                    className={`hover:bg-gray-50 transition-colors ${
                      overdueMark ? "bg-red-50" : ""
                    }`}
                  >
                    <td className="px-4 py-3">
                      <p
                        className={`text-sm font-medium ${
                          overdueMark ? "text-red-700" : "text-gray-900"
                        }`}
                      >
                        {task.title}
                      </p>
                      {task.description && (
                        <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">
                          {task.description}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {task.case_number || task.case_id?.slice(0, 8) || "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          PRIORITY_BADGE[task.priority] ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {PRIORITY_LABELS[task.priority] ?? task.priority}
                      </span>
                    </td>
                    <td
                      className={`px-4 py-3 text-sm ${
                        overdueMark ? "text-red-600 font-medium" : "text-gray-500"
                      }`}
                    >
                      {task.due_date
                        ? new Date(task.due_date).toLocaleDateString("ru-RU")
                        : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                          STATUS_BADGE[task.status] ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {STATUS_LABELS[task.status] ?? task.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {nextStatus && (
                        <button
                          disabled={updating === task.id}
                          onClick={() => handleStatusChange(task.id, nextStatus)}
                          className="text-xs px-3 py-1 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors disabled:opacity-50"
                        >
                          {updating === task.id ? "..." : NEXT_LABEL[task.status]}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
