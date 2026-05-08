"use client";

import { useState, useEffect } from "react";
import { CheckCircle2, Clock, Upload, AlertCircle, ChevronDown, ChevronUp, Info } from "lucide-react";
import {
  getCompleteness,
  updateChecklistItem,
  type CompletenessProgressResponse,
  type CompletenessItemResponse,
} from "@/lib/api/completeness";
import ClientDocumentCard from "./ClientDocumentCard";

interface ClientDocumentsViewProps {
  caseId: string;
}

// Вспомогательная функция для получения документов дела (заглушка)
// В реальном приложении нужно будет получать список документов через API
async function fetchCaseDocuments(caseId: string): Promise<Array<{ id: string; name: string }>> {
  // Заглушка - в реальности нужно вызывать API для получения документов дела
  return [
    { id: "doc1", name: "Паспорт_скан.pdf" },
    { id: "doc2", name: "СНИЛС_фото.jpg" },
    { id: "doc3", name: "Справка_2НДФЛ.pdf" },
  ];
}

export default function ClientDocumentsView({ caseId }: ClientDocumentsViewProps) {
  const [data, setData] = useState<CompletenessProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [availableDocuments, setAvailableDocuments] = useState<Array<{ id: string; name: string }>>([]);
  const [showApproved, setShowApproved] = useState(false);

  // Загрузка данных о комплектности
  const loadCompleteness = async () => {
    try {
      setLoading(true);
      const [completenessData, documents] = await Promise.all([
        getCompleteness(caseId),
        fetchCaseDocuments(caseId),
      ]);
      setData(completenessData);
      setAvailableDocuments(documents);
      setError(null);
    } catch (err) {
      console.error("Ошибка загрузки данных:", err);
      setError("Не удалось загрузить информацию о документах. Пожалуйста, попробуйте позже.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCompleteness();
  }, [caseId]);

  // Обработчик загрузки документа
  const handleUploadDocument = async (itemId: string, documentId: string) => {
    try {
      await updateChecklistItem(caseId, itemId, {
        status: "uploaded",
        document_id: documentId,
      });
      // Перезагружаем данные
      await loadCompleteness();
    } catch (err) {
      console.error("Ошибка при обновлении документа:", err);
      throw err;
    }
  };

  // Группировка элементов по статусам
  const actionItems: CompletenessItemResponse[] = [];
  const pendingItems: CompletenessItemResponse[] = [];
  const completedItems: CompletenessItemResponse[] = [];

  if (data) {
    data.categories.forEach((category) => {
      category.items.forEach((item) => {
        if (item.status === "missing" || item.status === "rejected") {
          actionItems.push(item);
        } else if (item.status === "uploaded" || item.status === "review") {
          pendingItems.push(item);
        } else if (item.status === "approved" || item.status === "waived") {
          completedItems.push(item);
        }
      });
    });
  }

  // Сортировка: rejected первыми, затем missing
  actionItems.sort((a, b) => {
    if (a.status === "rejected" && b.status !== "rejected") return -1;
    if (a.status !== "rejected" && b.status === "rejected") return 1;
    return 0;
  });

  // Подсчёт статистики
  const stats = {
    total: data?.total_items || 0,
    completed: data?.completed_items || 0,
    required: data?.required_items || 0,
    requiredCompleted: data?.required_completed || 0,
    approved: completedItems.filter((item) => item.status === "approved").length,
    pending: pendingItems.length,
    action: actionItems.length,
  };

  const progressPercent = data?.progress_percent || 0;

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Загружаем информацию о документах...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
        <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-red-800 mb-2">Ошибка загрузки</h3>
        <p className="text-red-700 mb-4">{error}</p>
        <button
          onClick={loadCompleteness}
          className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Шапка с прогрессом */}
      <div className="bg-white rounded-2xl shadow-lg p-6 border border-gray-200">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
              <span className="p-2 bg-blue-100 rounded-lg">
                📋
              </span>
              Сбор документов
            </h1>
            <p className="text-gray-600 mt-2">
              Мы поможем вам собрать все необходимые документы для процедуры банкротства
            </p>
          </div>
          {data?.is_complete && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-6 w-6 text-green-600" />
                <div>
                  <h3 className="font-semibold text-green-800">Все документы собраны! 🎉</h3>
                  <p className="text-green-700 text-sm">Юрист проверит документы и свяжется с вами</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Прогресс-бар */}
        <div className="mt-8">
          <div className="flex justify-between items-center mb-2">
            <span className="text-lg font-semibold text-gray-900">
              {progressPercent.toFixed(0)}% готово
            </span>
            <span className="text-gray-600">
              Собрано {stats.completed} из {stats.total} документов
            </span>
          </div>
          <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Мини-счётчики */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
          <div className="bg-green-50 p-4 rounded-xl border border-green-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Принято</p>
                <p className="text-2xl font-bold text-gray-900">{stats.approved}</p>
              </div>
            </div>
          </div>
          <div className="bg-yellow-50 p-4 rounded-xl border border-yellow-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-yellow-100 rounded-lg">
                <Clock className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">На проверке</p>
                <p className="text-2xl font-bold text-gray-900">{stats.pending}</p>
              </div>
            </div>
          </div>
          <div className="bg-orange-50 p-4 rounded-xl border border-orange-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 rounded-lg">
                <Upload className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Нужно загрузить</p>
                <p className="text-2xl font-bold text-gray-900">{stats.action}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Секция 1: Нужно загрузить */}
      {actionItems.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <AlertCircle className="h-5 w-5 text-orange-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-900">
              Нужно загрузить ({actionItems.length} документ{actionItems.length !== 1 ? "а" : ""})
            </h2>
          </div>
          <p className="text-gray-600">
            Пожалуйста, загрузите эти документы. Мы подскажем, как их получить.
          </p>
          <div className="space-y-4">
            {actionItems.map((item) => (
              <ClientDocumentCard
                key={item.id}
                item={item}
                onUpload={handleUploadDocument}
                variant="action"
                availableDocuments={availableDocuments}
              />
            ))}
          </div>
        </section>
      )}

      {/* Секция 2: На проверке */}
      {pendingItems.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <Clock className="h-5 w-5 text-yellow-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-900">
              На проверке ({pendingItems.length} документ{pendingItems.length !== 1 ? "а" : ""})
            </h2>
          </div>
          <p className="text-gray-600">
            Эти документы уже загружены и ожидают проверки юристом.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {pendingItems.map((item) => (
              <ClientDocumentCard
                key={item.id}
                item={item}
                onUpload={handleUploadDocument}
                variant="pending"
              />
            ))}
          </div>
        </section>
      )}

      {/* Секция 3: Принятые документы */}
      {completedItems.length > 0 && (
        <section className="space-y-4">
          <button
            onClick={() => setShowApproved(!showApproved)}
            className="flex items-center justify-between w-full p-4 bg-gray-50 rounded-xl border border-gray-200 hover:bg-gray-100 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              </div>
              <div className="text-left">
                <h2 className="text-xl font-bold text-gray-900">
                  Принятые документы ({completedItems.length})
                </h2>
                <p className="text-gray-600 text-sm">
                  Все документы из этого списка уже проверены и приняты
                </p>
              </div>
            </div>
            {showApproved ? (
              <ChevronUp className="h-5 w-5 text-gray-500" />
            ) : (
              <ChevronDown className="h-5 w-5 text-gray-500" />
            )}
          </button>

          {showApproved && (
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {completedItems.map((item) => (
                  <ClientDocumentCard
                    key={item.id}
                    item={item}
                    onUpload={handleUploadDocument}
                    variant="complete"
                  />
                ))}
              </div>
              <div className="mt-4 pt-4 border-t border-gray-200 text-center text-sm text-gray-500">
                ✅ Зелёная галочка — документ принят<br />
                — Серый минус — документ не требуется
              </div>
            </div>
          )}
        </section>
      )}

      {/* Информационная панель */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
        <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
          <Info className="h-5 w-5" />
          Как это работает?
        </h3>
        <ul className="space-y-2 text-blue-800">
          <li className="flex items-start gap-2">
            <span className="font-medium">1.</span>
            <span>Загрузите документы через раздел "Документы" или прямо здесь</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-medium">2.</span>
            <span>Привяжите загруженный документ к нужному пункту</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-medium">3.</span>
            <span>Юрист проверит документ в течение 1-2 рабочих дней</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="font-medium">4.</span>
            <span>После проверки всех документов мы начнём процедуру банкротства</span>
          </li>
        </ul>
        <div className="mt-4 flex gap-3">
          <a
            href="/lk/dokumenty"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Перейти к документам
          </a>
          <button
            onClick={loadCompleteness}
            className="px-4 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 transition-colors"
          >
            Обновить статус
          </button>
        </div>
      </div>
    </div>
  );
}