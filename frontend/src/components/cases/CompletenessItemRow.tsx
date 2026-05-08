"use client";

import { useState } from "react";
import {
  Circle,
  Upload,
  Clock,
  CheckCircle2,
  XCircle,
  MinusCircle,
  ChevronDown,
  ChevronUp,
  Star,
  FileText,
  AlertCircle,
} from "lucide-react";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  Textarea,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
  Separator,
} from "@/components/ui";
import type {
  CompletenessItemResponse,
  ChecklistItemStatus,
  ItemUpdateRequest,
} from "@/lib/api/completeness";

interface CompletenessItemRowProps {
  item: CompletenessItemResponse;
  userRole: "admin" | "lawyer" | "client";
  onUpdate: (itemId: string, update: ItemUpdateRequest) => Promise<void>;
}

const STATUS_ICONS: Record<ChecklistItemStatus, React.ReactNode> = {
  missing: <Circle className="h-5 w-5 text-gray-400" />,
  uploaded: <Upload className="h-5 w-5 text-blue-500" />,
  review: <Clock className="h-5 w-5 text-yellow-500" />,
  approved: <CheckCircle2 className="h-5 w-5 text-green-500" />,
  rejected: <XCircle className="h-5 w-5 text-red-500" />,
  waived: <MinusCircle className="h-5 w-5 text-gray-500" />,
};

const STATUS_LABELS: Record<ChecklistItemStatus, string> = {
  missing: "Отсутствует",
  uploaded: "Загружен",
  review: "На проверке",
  approved: "Принят",
  rejected: "Отклонён",
  waived: "Не требуется",
};

const STATUS_VARIANTS: Record<ChecklistItemStatus, "default" | "secondary" | "destructive" | "outline" | "success"> = {
  missing: "secondary",
  uploaded: "outline",
  review: "default",
  approved: "success",
  rejected: "destructive",
  waived: "secondary",
};

export default function CompletenessItemRow({
  item,
  userRole,
  onUpdate,
}: CompletenessItemRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [rejectionDialogOpen, setRejectionDialogOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);

  const isAdminOrLawyer = userRole === "admin" || userRole === "lawyer";

  const handleStatusChange = async (newStatus: ChecklistItemStatus) => {
    if (!isAdminOrLawyer) return;
    try {
      setIsUpdating(true);
      await onUpdate(item.id, { status: newStatus });
    } finally {
      setIsUpdating(false);
    }
  };

  const handleReject = async () => {
    if (!rejectionReason.trim()) return;
    try {
      setIsUpdating(true);
      await onUpdate(item.id, {
        status: "rejected",
        rejection_reason: rejectionReason,
      });
      setRejectionDialogOpen(false);
      setRejectionReason("");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleUpload = async () => {
    // In a real app, this would open a document picker
    // For now, we'll just change status to uploaded
    await handleStatusChange("uploaded");
  };

  const getAvailableActions = () => {
    if (!isAdminOrLawyer) return [];

    const actions: Array<{
      label: string;
      onClick: () => void | Promise<void>;
      variant?: "default" | "secondary" | "destructive" | "outline";
      disabled?: boolean;
    }> = [];

    switch (item.status) {
      case "missing":
        actions.push({
          label: "Привязать документ",
          onClick: handleUpload,
          variant: "default",
        });
        break;
      case "uploaded":
        actions.push({
          label: "На проверку",
          onClick: () => handleStatusChange("review"),
          variant: "default",
        });
        break;
      case "review":
        actions.push(
          {
            label: "Принять",
            onClick: () => handleStatusChange("approved"),
            variant: "default",
          },
          {
            label: "Отклонить",
            onClick: () => setRejectionDialogOpen(true),
            variant: "destructive",
          }
        );
        break;
      case "rejected":
        actions.push({
          label: "Повторная загрузка",
          onClick: () => handleStatusChange("uploaded"),
          variant: "outline",
        });
        break;
    }

    // "Не требуется" available for all statuses except approved
    if (item.status !== "approved") {
      actions.push({
        label: "Не требуется",
        onClick: () => handleStatusChange("waived"),
        variant: "secondary",
      });
    }

    return actions;
  };

  const actions = getAvailableActions();

  return (
    <div className="border rounded-lg overflow-hidden mb-2">
      {/* Main row */}
      <div
        className="flex items-center justify-between p-4 hover:bg-gray-50 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0">
            {STATUS_ICONS[item.status]}
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-medium">{item.name}</span>
              {item.required && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger>
                      <Star className="h-4 w-4 text-red-500 fill-red-500" />
                    </TooltipTrigger>
                    <TooltipContent>
                      Обязательный документ
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant={STATUS_VARIANTS[item.status]}>
                {STATUS_LABELS[item.status]}
              </Badge>
              {item.document_name && (
                <Badge variant="outline" className="flex items-center gap-1">
                  <FileText className="h-3 w-3" />
                  {item.document_name}
                </Badge>
              )}
              {item.matched_by && item.matched_by !== "manual" && (
                <Badge variant="outline" className="text-xs">
                  Авто-сопоставление ({item.matched_by})
                </Badge>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {actions.length > 0 && (
            <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
              {actions.map((action, idx) => (
                <Button
                  key={idx}
                  size="sm"
                  variant={action.variant || "default"}
                  onClick={action.onClick}
                  disabled={isUpdating || action.disabled}
                >
                  {action.label}
                </Button>
              ))}
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={(e) => {
              e.stopPropagation();
              setExpanded(!expanded);
            }}
          >
            {expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="p-4 border-t bg-gray-50">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h4 className="font-medium mb-2">Описание</h4>
              <p className="text-sm text-gray-600">{item.description}</p>
            </div>
            <div>
              <h4 className="font-medium mb-2">Правовое основание</h4>
              <p className="text-sm text-gray-600">{item.legal_basis}</p>
            </div>
            <div>
              <h4 className="font-medium mb-2">Как получить</h4>
              <p className="text-sm text-gray-600">{item.how_to_get}</p>
            </div>
            <div>
              <h4 className="font-medium mb-2">Допустимые форматы</h4>
              <div className="flex flex-wrap gap-1">
                {item.accept_formats.map((format) => (
                  <Badge key={format} variant="secondary" className="text-xs">
                    {format}
                  </Badge>
                ))}
              </div>
              {item.max_age_days && (
                <div className="mt-2">
                  <h4 className="font-medium mb-1">Срок действия</h4>
                  <p className="text-sm text-gray-600">
                    Документ должен быть не старше {item.max_age_days} дней
                  </p>
                </div>
              )}
            </div>
          </div>

          {item.notes && (
            <div className="mt-4">
              <h4 className="font-medium mb-2">Заметки</h4>
              <p className="text-sm text-gray-600 bg-white p-2 rounded border">
                {item.notes}
              </p>
            </div>
          )}

          {item.rejection_reason && (
            <div className="mt-4">
              <h4 className="font-medium mb-2 flex items-center gap-2 text-red-600">
                <AlertCircle className="h-4 w-4" />
                Причина отклонения
              </h4>
              <p className="text-sm text-gray-600 bg-red-50 p-2 rounded border border-red-200">
                {item.rejection_reason}
              </p>
            </div>
          )}

          <div className="mt-4 text-xs text-gray-500">
            ID: {item.checklist_item_id} • Категория: {item.category}
            {item.reviewed_at && ` • Проверено: ${new Date(item.reviewed_at).toLocaleDateString("ru-RU")}`}
          </div>
        </div>
      )}

      {/* Rejection Dialog */}
      <Dialog open={rejectionDialogOpen} onOpenChange={setRejectionDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Отклонить документ</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="mb-4">
              Укажите причину отклонения документа "{item.name}":
            </p>
            <Textarea
              placeholder="Например: нечёткое изображение, неполные данные, несоответствие формату..."
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              rows={4}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRejectionDialogOpen(false)}
            >
              Отмена
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={!rejectionReason.trim() || isUpdating}
            >
              Отклонить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}