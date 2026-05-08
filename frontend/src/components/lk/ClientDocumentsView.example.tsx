"use client";

/**
 * Пример использования ClientDocumentsView
 * 
 * Этот файл демонстрирует, как использовать компоненты
 * ClientDocumentsView и ClientDocumentCard в приложении.
 */

import ClientDocumentsView from "./ClientDocumentsView";

export default function ExamplePage() {
  // В реальном приложении caseId будет получен из контекста или параметров маршрута
  const caseId = "550e8400-e29b-41d4-a716-446655440000";
  
  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Личный кабинет клиента</h1>
      <p className="text-gray-600 mb-8">
        Здесь вы можете отслеживать прогресс сбора документов для процедуры банкротства.
      </p>
      
      <ClientDocumentsView caseId={caseId} />
      
      <div className="mt-12 p-6 bg-gray-50 rounded-xl border border-gray-200">
        <h2 className="text-xl font-bold mb-4">Как использовать компоненты</h2>
        <ul className="space-y-3 text-gray-700">
          <li className="flex items-start gap-2">
            <span className="font-medium">1.</span>
            <span>Импортируйте ClientDocumentsView в вашу страницу</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-medium">2.</span>
            <span>Передайте caseId (идентификатор дела) как пропс</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-medium">3.</span>
            <span>Компонент сам загрузит данные через API</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-medium">4.</span>
            <span>Для загрузки документов клиент должен сначала загрузить файлы через раздел "Документы"</span>
          </li>
        </ul>
        
        <div className="mt-6 p-4 bg-blue-50 rounded-lg">
          <h3 className="font-semibold text-blue-800 mb-2">Примечания:</h3>
          <ul className="text-blue-700 text-sm space-y-1">
            <li>• API-клиент уже настроен в <code>@/lib/api/completeness.ts</code></li>
            <li>• Для работы нужен access_token в localStorage</li>
            <li>• Функция fetchCaseDocuments в ClientDocumentsView — заглушка, нужно реализовать получение документов дела</li>
            <li>• Компоненты адаптивны и работают на мобильных устройствах</li>
          </ul>
        </div>
      </div>
    </div>
  );
}