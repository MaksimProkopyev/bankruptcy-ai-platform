import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Частые вопросы о банкротстве — Банкротство.AI",
  description: "Ответы на популярные вопросы о процедуре банкротства физических лиц. Стоимость, сроки, последствия.",
};

export default function Page() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-16">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Частые вопросы о банкротстве</h1>
      <div className="bg-white rounded-2xl border border-gray-200 p-8">
        <p className="text-gray-500">
          Контент этой страницы будет доработан. Техническая основа готова — 
          SEO-метатеги, layout, навигация, чат-бот.
        </p>
      </div>
    </div>
  );
}
