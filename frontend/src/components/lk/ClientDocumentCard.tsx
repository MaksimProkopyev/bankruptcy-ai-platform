"use client";

import { useState } from "react";
import {
  Upload,
  Clock,
  Eye,
  CheckCircle2,
  AlertCircle,
  MinusCircle,
  FileText,
  Info,
  AlertTriangle,
} from "lucide-react";
import type { CompletenessItemResponse } from "@/lib/api/completeness";

const CLIENT_STATUS_MAP = {
  missing: { label: "Нужно загрузить", color: "text-orange-500", icon: Upload },
  uploaded: { label: "Загружен, ожидает проверки", color: "text-blue-500", icon: Clock },
  review: { label: "На проверке у юриста", color: "text-yellow-500", icon: Eye },
  approved: { label: "Принят ✓", color: "text-green-600", icon: CheckCircle2 },
  rejected: { label: "Нужно заменить", color: "text-red-500", icon: AlertCircle },
  waived: { label: "Не требуется", color: "text-gray-400", icon: MinusCircle },
} as const;

export interface ClientDocumentCardProps {
  item: CompletenessItemResponse;
  onUpload: (itemId: string, documentId: string) => Promise<void>;
  variant: "action" | "pending" | "complete";
  availableDocuments?: Array<{ id: string; name: string }>;
}

export default function ClientDocumentCard({
  item,
  onUpload,
  variant,
  availableDocuments = [],
}: ClientDocumentCardProps) {
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [showAllInfo, setShowAllInfo] = useState(false);

  const statusConfig = CLIENT_STATUS_MAP[item.status];
  const StatusIcon = statusConfig.icon;

  const handleAttachDocument = async () => {
    if (!selectedDocumentId) return;
    setIsUploading(true);
    try {
      await onUpload(item.id, selectedDocumentId);
      setSelectedDocumentId("");
    } catch (error) {
      console.error("Ошибка при привязке документа:", error);
    } finally {
      setIsUploading(false);
    }
  };

  // Variant: complete (approved/waived) - компактный вид
  if (variant === "complete") {
    return (
      <div className="flex items-center gap-2 py-2 px-3 border border-gray-200 rounded-lg bg-gray-50">
        <StatusIcon className={`h-4 w-4 ${statusConfig.color}`} />
        <span className="text-sm font-medium">{item.name}</span>
        {item.status === "waived" && (
          <span className="text-xs text-gray-500 ml-auto">(не требуется)</span>
        )}
      </div>
    );
  }

  // Variant: pending (uploaded/review) - компактный с файлом
  if (variant === "pending") {
    return (
      <div className="p-4 border border-gray-300 rounded-xl bg-white shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${statusConfig.color.replace("text", "bg")}/10`}>
              <StatusIcon className={`h-5 w-5 ${statusConfig.color}`} />
            </div>
            <div>
              <h4 className="font-semibold text-gray-900">{item.name}</h4>
              <div className="flex items-center gap-2 mt-1">
                <span className={`text-sm font-medium ${statusConfig.color}`}>
                  {statusConfig.label}
                </span>
                {item.document_name && (
                  <>
                    <span className="text-gray-400">•</span>
                    <div className="flex items-center gap-1 text-sm text-gray-600">
                      <FileText className="h-3 w-3" />
                      <span className="truncate max-w-[200px]">{item.document_name}</span>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
          {item.max_age_days && (
            <div className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
              <AlertTriangle className="h-3 w-3" />
              <span>Не старше {item.max_age_days} дней</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Variant: action (missing/rejected) - полная карточка с действиями
  return (
    <div className="p-5 border border-gray-300 rounded-xl bg-white shadow-md">
      {/* Заголовок с бейджем обязательности */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-full ${statusConfig.color.replace("text", "bg")}/10`}>
            <StatusIcon className={`h-5 w-5 ${statusConfig.color}`} />
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900">{item.name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className={`text-sm font-medium ${statusConfig.color}`}>
                {statusConfig.label}
              </span>
              {item.required && (
                <span className="text-xs font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded">
                  * обязательный
                </span>
              )}
            </div>
          </div>
        </div>
        {item.max_age_days && (
          <div className="flex items-center gap-1 text-sm text-amber-600 bg-amber-50 px-3 py-1 rounded-lg">
            <AlertTriangle className="h-4 w-4" />
            <span>Документ должен быть не старше {item.max_age_days} дней</span>
          </div>
        )}
      </div>

      {/* Описание */}
      <p className="text-gray-700 mb-4">{item.description}</p>

      {/* Как получить */}
      {item.how_to_get && (
        <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-100">
          <div className="flex items-center gap-2 mb-1">
            <Info className="h-4 w-4 text-blue-600" />
            <span className="font-medium text-blue-800">Как получить:</span>
          </div>
          <p className="text-blue-700 text-sm">{item.how_to_get}</p>
        </div>
      )}

      {/* Причина отклонения (если rejected) */}
      {item.status === "rejected" && item.rejection_reason && (
        <div className="mb-4 p-3 bg-red-50 rounded-lg border border-red-200">
          <div className="flex items-center gap-2 mb-1">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <span className="font-medium text-red-800">Причина отклонения:</span>
          </div>
          <p className="text-red-700">{item.rejection_reason}</p>
        </div>
      )}

      {/* Форматы файлов */}
      {item.accept_formats.length > 0 && (
        <div className="mb-4">
          <span className="text-sm font-medium text-gray-700">📎 Форматы: </span>
          <span className="text-sm text-gray-600">{item.accept_formats.join(", ")}</span>
        </div>
      )}

      {/* Выбор документа для привязки */}
      <div className="border-t pt-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Выберите документ
            </label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              value={selectedDocumentId}
              onChange={(e) => setSelectedDocumentId(e.target.value)}
              disabled={isUploading || availableDocuments.length === 0}
            >
              <option value="">{availableDocuments.length === 0 ? "Нет доступных документов" : "Выберите документ..."}</option>
              {availableDocuments.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.name}
                </option>
              ))}
            </select>
            {availableDocuments.length === 0 && (
              <p className="text-sm text-gray-500 mt-1">
                Сначала загрузите документ через раздел "Документы"
              </p>
            )}
          </div>
          <div className="flex items-end">
            <button
              onClick={handleAttachDocument}
              disabled={!selectedDocumentId || isUploading}
              className="px-4 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isUploading ? "Привязка..." : "Привязать →"}
            </button>
          </div>
        </div>
        <div className="mt-3 flex justify-between items-center">
          <button
            onClick={() => setShowAllInfo(!showAllInfo)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {showAllInfo ? "Скрыть детали" : "Показать все детали"}
          </button>
          <a
            href="/lk/dokumenty"
            className="text-sm text-gray-600 hover:text-gray-900 underline"
          >
            Загрузить новый документ
          </a>
        </div>
      </div>

      {/* Дополнительная информация (legal_basis и т.д.) - скрыта по умолчанию */}
      {showAllInfo && (
        <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
          <h5 className="font-medium text-gray-700 mb-2">Дополнительная информация</h5>
          <p className="text-sm text-gray-600">
            <span className="font-medium">Категория:</span> {item.category}
          </p>
          {item.notes && (
            <p className="text-sm text-gray-600 mt-1">
              <span className="font-medium">Примечания:</span> {item.notes}
            </p>
          )}
        </div>
      )}
    </div>
  );
}