"use client";

import { useEffect, useState } from "react";
import { clients as clientsApi, type Client } from "@/lib/api";
import { formatDate } from "@/lib/case-utils";

export default function ClientsPage() {
  const [clientList, setClientList] = useState<Client[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    clientsApi.list({ search: search || undefined })
      .then(setClientList)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [search]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Клиенты</h1>
      </div>
      <div className="mb-6">
        <input type="text" placeholder="Поиск по фамилии или телефону..."
          value={search} onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-md px-4 py-2.5 border border-gray-200 rounded-lg text-sm bg-white" />
      </div>
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50/50">
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">ФИО</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Телефон</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Регион</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Источник</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Дата</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="text-center py-12 text-gray-400">Загрузка...</td></tr>
            ) : clientList.length === 0 ? (
              <tr><td colSpan={5} className="text-center py-12 text-gray-400">Нет клиентов</td></tr>
            ) : (
              clientList.map((c) => (
                <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{c.last_name} {c.first_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{c.phone}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{c.region || "—"}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{c.lead_source || "—"}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{formatDate(c.created_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
