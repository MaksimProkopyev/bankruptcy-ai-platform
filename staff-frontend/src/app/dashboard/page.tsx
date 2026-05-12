"use client";

import { useEffect, useState } from "react";
import {
  Briefcase,
  CheckSquare,
  Clock,
  AlertTriangle,
  Users,
  BarChart2,
} from "lucide-react";
import { apiGet } from "@/lib/api";
import { getUser } from "@/lib/auth";

const ROLE_LABELS: Record<string, string> = {
  admin: "Администратор",
  operations_director: "Директор операций",
  lawyer: "Юрист",
  paralegal: "Помощник юриста",
  client_manager: "Клиентский менеджер",
  marketer: "Маркетолог",
  ai_engineer: "AI-инженер",
};

interface DashboardData {
  user: {
    id: string;
    first_name: string;
    last_name: string;
    role: string;
  };
  my_cases_count: number;
  my_tasks_count: number;
  my_deadlines_today: number;
  my_deadlines_overdue: number;
  team_cases_active?: number;
  team_tasks_open?: number;
  team_overdue_deadlines?: number;
}

function MetricCard({
  icon,
  label,
  value,
  colorClass,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  colorClass: string;
}) {
  return (
    <div className={`bg-white rounded-xl border shadow-sm p-5 flex items-center gap-4 ${colorClass}`}>
      <div className="flex-shrink-0 w-11 h-11 rounded-full bg-gray-50 flex items-center justify-center">
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-xl border border-gray-100 p-5 flex items-center gap-4 animate-pulse">
      <div className="w-11 h-11 rounded-full bg-gray-100 flex-shrink-0" />
      <div className="flex-1 space-y-2">
        <div className="h-6 w-12 bg-gray-100 rounded" />
        <div className="h-3 w-24 bg-gray-100 rounded" />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet("/staff/me/dashboard")
      .then((d) => {
        if (d) setData(d);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const today = new Date().toLocaleDateString("ru-RU", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  // Get first name from JWT for greeting (available before API response)
  const tokenUser = getUser();
  const firstName = data?.user?.first_name || tokenUser?.first_name || "";

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-red-500 text-sm">
        Ошибка загрузки: {error}
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-[#1B3A5C] font-heading">
          {firstName ? `Добрый день, ${firstName}` : "Мой кабинет"}
        </h1>
        <div className="flex items-center gap-3 mt-1">
          {data && (
            <span className="text-sm text-gray-500 capitalize">
              {ROLE_LABELS[data.user.role] ?? data.user.role}
            </span>
          )}
          {data && <span className="text-gray-300">·</span>}
          <span className="text-sm text-gray-500 capitalize">{today}</span>
        </div>
      </div>

      {/* Personal metrics */}
      <h2 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
        Мои показатели
      </h2>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {loading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : data ? (
          <>
            <MetricCard
              icon={<Briefcase size={20} className="text-[#1B3A5C]" />}
              label="Мои дела"
              value={data.my_cases_count}
              colorClass="border-[#1B3A5C]/20"
            />
            <MetricCard
              icon={
                <CheckSquare
                  size={20}
                  className={data.my_tasks_count > 0 ? "text-orange-500" : "text-gray-400"}
                />
              }
              label="Открытые задачи"
              value={data.my_tasks_count}
              colorClass={data.my_tasks_count > 0 ? "border-orange-200" : "border-gray-100"}
            />
            <MetricCard
              icon={<Clock size={20} className="text-[#C9A84C]" />}
              label="Дедлайны сегодня"
              value={data.my_deadlines_today}
              colorClass="border-[#C9A84C]/30"
            />
            <MetricCard
              icon={
                <AlertTriangle
                  size={20}
                  className={data.my_deadlines_overdue > 0 ? "text-red-500" : "text-gray-400"}
                />
              }
              label="Просроченные"
              value={data.my_deadlines_overdue}
              colorClass={data.my_deadlines_overdue > 0 ? "border-red-200" : "border-gray-100"}
            />
          </>
        ) : null}
      </div>

      {/* Team stats (admin / ops only — shown if API returns team data) */}
      {data &&
        (data.team_cases_active !== undefined ||
          data.team_tasks_open !== undefined ||
          data.team_overdue_deadlines !== undefined) && (
          <>
            <h2 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
              Команда
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 flex items-center gap-4">
                <Users size={22} className="text-[#1B3A5C] flex-shrink-0" />
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {data.team_cases_active ?? 0}
                  </p>
                  <p className="text-sm text-gray-500">Активные дела</p>
                </div>
              </div>
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 flex items-center gap-4">
                <BarChart2 size={22} className="text-orange-500 flex-shrink-0" />
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {data.team_tasks_open ?? 0}
                  </p>
                  <p className="text-sm text-gray-500">Открытые задачи</p>
                </div>
              </div>
              <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 flex items-center gap-4">
                <AlertTriangle
                  size={22}
                  className={
                    (data.team_overdue_deadlines ?? 0) > 0
                      ? "text-red-500 flex-shrink-0"
                      : "text-gray-400 flex-shrink-0"
                  }
                />
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {data.team_overdue_deadlines ?? 0}
                  </p>
                  <p className="text-sm text-gray-500">Просроченные дедлайны</p>
                </div>
              </div>
            </div>
          </>
        )}
    </div>
  );
}
