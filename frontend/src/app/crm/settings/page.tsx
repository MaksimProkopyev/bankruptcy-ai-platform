"use client";

import { useEffect, useState } from "react";
import { auth, type User } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const ROLE_LABELS: Record<string, string> = {
  admin: "Администратор",
  operations_director: "Операционный директор",
  lawyer: "Юрист",
  paralegal: "Параюрист",
  client_manager: "Менеджер по клиентам",
  marketer: "Маркетолог",
  ai_engineer: "AI-инженер",
};

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<"profile" | "team" | "integrations" | "ai">("profile");

  useEffect(() => {
    auth.me().then(setUser).catch(console.error);
  }, []);

  const tabs = [
    { key: "profile" as const, label: "Профиль" },
    { key: "team" as const, label: "Команда" },
    { key: "integrations" as const, label: "Интеграции" },
    { key: "ai" as const, label: "AI-настройки" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-gray-900 mb-6">Настройки</h1>

      <div className="flex gap-1 mb-6 border-b border-gray-200">
        {tabs.map((t) => (
          <button key={t.key} onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2.5 text-sm border-b-2 ${activeTab === t.key ? "border-brand-600 text-brand-700 font-medium" : "border-transparent text-gray-500"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === "profile" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 max-w-xl">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Профиль</h2>
          {user ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Имя</label>
                  <input type="text" value={user.first_name} readOnly className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Фамилия</label>
                  <input type="text" value={user.last_name} readOnly className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50" />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input type="email" value={user.email} readOnly className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Роль</label>
                <span className="inline-block px-3 py-1.5 bg-brand-50 text-brand-700 rounded-lg text-sm font-medium">
                  {ROLE_LABELS[user.role] || user.role}
                </span>
              </div>
            </div>
          ) : <p className="text-sm text-gray-400">Загрузка...</p>}
        </div>
      )}

      {activeTab === "team" && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900">Команда</h2>
            <button className="px-4 py-2 text-sm bg-brand-600 text-white rounded-lg">+ Добавить сотрудника</button>
          </div>
          <p className="text-sm text-gray-400">Управление сотрудниками через API: GET /api/v1/users/</p>
        </div>
      )}

      {activeTab === "integrations" && (
        <div className="space-y-4">
          {[
            { name: "Telegram Bot", desc: "Квалификация + уведомления клиентов", status: "config_needed", key: "TELEGRAM_BOT_TOKEN" },
            { name: "WhatsApp Business", desc: "Мультиканальная коммуникация", status: "not_connected", key: "WHATSAPP_API_TOKEN" },
            { name: "SMS-шлюз", desc: "Авторизация клиентов в ЛК", status: "not_connected", key: "SMS_API_KEY" },
            { name: "kad.arbitr.ru", desc: "Мониторинг судебных дел", status: "planned", key: "" },
            { name: "ЕФРСБ", desc: "Публикации о банкротстве", status: "planned", key: "" },
          ].map((int) => (
            <div key={int.name} className="bg-white rounded-xl border border-gray-200 p-5 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-900">{int.name}</p>
                <p className="text-xs text-gray-500 mt-0.5">{int.desc}</p>
              </div>
              <span className={`px-2.5 py-1 text-xs rounded-full ${
                int.status === "connected" ? "bg-green-100 text-green-700" :
                int.status === "config_needed" ? "bg-yellow-100 text-yellow-700" :
                int.status === "planned" ? "bg-gray-100 text-gray-500" :
                "bg-gray-100 text-gray-500"
              }`}>
                {int.status === "connected" ? "Подключено" :
                 int.status === "config_needed" ? "Нужен токен" :
                 int.status === "planned" ? "В плане" : "Не подключено"}
              </span>
            </div>
          ))}
        </div>
      )}

      {activeTab === "ai" && (
        <div className="space-y-4 max-w-xl">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">AI-конфигурация</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Основной LLM</label>
                <select className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                  <option>Claude Sonnet 4 (claude-sonnet-4-20250514)</option>
                  <option>Claude Opus 4</option>
                  <option>GPT-4o (fallback)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">AI Core URL</label>
                <input type="text" value="http://localhost:8001" readOnly className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Confidence threshold (эскалация на юриста)</label>
                <input type="range" min="50" max="95" defaultValue="70" className="w-full" />
                <p className="text-xs text-gray-400 mt-1">Если AI уверен менее чем на 70%, задача передаётся юристу</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
