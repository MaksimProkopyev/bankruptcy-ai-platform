"use client";

import { useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Wand2,
  FileWarning,
  Loader2,
} from "lucide-react";

import CompletenessItemRow from "./CompletenessItemRow";
import {
  getCompleteness,
  initChecklist,
  autoMatchDocuments,
  updateChecklistItem,
  type CompletenessProgressResponse,
  type ItemUpdateRequest,
} from "@/lib/api/completeness";

interface CompletenessWidgetProps {
  caseId: string;
  userRole: "admin" | "lawyer" | "client";
}

export default function CompletenessWidget({
  caseId,
  userRole,
}: CompletenessWidgetProps) {
  const [data, setData] = useState<CompletenessProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("");
  const [isInitializing, setIsInitializing] = useState(false);
  const [isAutoMatching, setIsAutoMatching] = useState(false);
  const [autoMatchResult, setAutoMatchResult] = useState<{
    matched: number;
    details: Array<{ checklist_item_id: string; document_name: string }>;
  } | null>(null);

  const isAdminOrLawyer = userRole === "admin" || userRole === "lawyer";

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const progress = await getCompleteness(caseId);
      setData(progress);
      if (!activeTab && progress.categories.length > 0) {
        setActiveTab(progress.categories[0].category);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Ошибка загрузки данных комплектности"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [caseId]);

  const handleInitChecklist = async () => {
    if (!isAdminOrLawyer) return;
    try {
      setIsInitializing(true);
      await initChecklist(caseId);
      await loadData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Ошибка инициализации чеклиста"
      );
    } finally {
      setIsInitializing(false);
    }
  };

  const handleAutoMatch = async () => {
    if (!isAdminOrLawyer) return;
    try {
      setIsAutoMatching(true);
      const result = await autoMatchDocuments(caseId);
      setAutoMatchResult({
        matched: result.matched,
        details: result.details.map((d) => ({
          checklist_item_id: d.checklist_item_id,
          document_name: d.document_name,
        })),
      });
      // Reload data to reflect changes
      await loadData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Ошибка авто-сопоставления"
      );
    } finally {
      setIsAutoMatching(false);
    }
  };

  const handleItemUpdate = async (
    itemId: string,
    update: ItemUpdateRequest
  ) => {
    if (!isAdminOrLawyer) return;
    try {
      await updateChecklistItem(caseId, itemId, update);
      // Reload data to reflect changes
      await loadData();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Ошибка обновления документа"
      );
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Комплектность документов</CardTitle>
        </CardHeader>
        <CardContent className="flex justify-center items-center py-12">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-gray-500">Загрузка данных...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Комплектность документов</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <Button onClick={loadData} className="mt-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            Повторить
          </Button>
        </CardContent>
      </Card>
    );
  }

  // No checklist initialized
  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Комплектность документов</CardTitle>
          <CardDescription>
            Чеклист документов для дела не инициализирован
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isAdminOrLawyer ? (
            <div className="space-y-4">
              <p className="text-gray-600">
                Для начала работы с комплектностью документов необходимо
                инициализировать чеклист.
              </p>
              <Button onClick={handleInitChecklist} disabled={isInitializing}>
                {isInitializing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Инициализация...
                  </>
                ) : (
                  "Инициализировать чеклист"
                )}
              </Button>
            </div>
          ) : (
            <p className="text-gray-600">
              Чеклист документов ещё не создан. Обратитесь к юристу.
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <CardTitle>{data.checklist_name}</CardTitle>
            <CardDescription>
              Собрано {data.required_completed} из {data.required_items}{" "}
              обязательных документов
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              variant={data.is_complete ? "success" : "secondary"}
              className="text-sm"
            >
              {data.is_complete ? (
                <>
                  <CheckCircle className="h-3 w-3 mr-1" />
                  Комплект собран
                </>
              ) : (
                "В процессе"
              )}
            </Badge>
            {isAdminOrLawyer && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleAutoMatch}
                  disabled={isAutoMatching}
                >
                  {isAutoMatching ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Wand2 className="h-4 w-4 mr-1" />
                  )}
                  Авто-сопоставление
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={loadData}
                >
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </>
            )}
          </div>
        </div>
        <div className="mt-4">
          <div className="flex justify-between text-sm mb-1">
            <span>Общий прогресс</span>
            <span>{data.progress_percent}%</span>
          </div>
          <Progress value={data.progress_percent} className="h-2" />
        </div>
      </CardHeader>

      <CardContent>
        {autoMatchResult && (
          <Alert className="mb-4">
            <AlertDescription>
              Авто-сопоставление завершено. Сопоставлено{" "}
              <strong>{autoMatchResult.matched}</strong> документов.
              {autoMatchResult.details.length > 0 && (
                <div className="mt-2 text-sm">
                  {autoMatchResult.details.slice(0, 3).map((detail, idx) => (
                    <div key={idx} className="text-gray-600">
                      • {detail.document_name}
                    </div>
                  ))}
                  {autoMatchResult.details.length > 3 && (
                    <div className="text-gray-500">
                      ... и ещё {autoMatchResult.details.length - 3}
                    </div>
                  )}
                </div>
              )}
            </AlertDescription>
          </Alert>
        )}

        {data.missing_required.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <FileWarning className="h-5 w-5 text-red-500" />
              <h3 className="font-semibold text-red-700">Требуют внимания</h3>
              <Badge variant="destructive">
                {data.missing_required.length}
              </Badge>
            </div>
            <div className="space-y-2">
              {data.missing_required.slice(0, 5).map((item) => (
                <CompletenessItemRow
                  key={item.id}
                  item={item}
                  userRole={userRole}
                  onUpdate={handleItemUpdate}
                />
              ))}
              {data.missing_required.length > 5 && (
                <div className="text-center text-sm text-gray-500 py-2">
                  ... и ещё {data.missing_required.length - 5} документов
                </div>
              )}
            </div>
            <Separator className="my-4" />
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full overflow-x-auto">
            {data.categories.map((category) => (
              <TabsTrigger
                key={category.category}
                value={category.category}
                className="flex items-center gap-2"
              >
                {category.category_name}
                <Badge variant="outline" className="ml-1">
                  {category.completed}/{category.total}
                </Badge>
              </TabsTrigger>
            ))}
          </TabsList>
          {data.categories.map((category) => (
            <TabsContent
              key={category.category}
              value={category.category}
              className="mt-4"
            >
              <div className="mb-4">
                <div className="flex justify-between items-center">
                  <div>
                    <h4 className="font-medium">{category.category_name}</h4>
                    <p className="text-sm text-gray-500">
                      Обязательных: {category.required_completed}/
                      {category.required_total}
                    </p>
                  </div>
                  <Badge variant="secondary">
                    Прогресс:{" "}
                    {category.total > 0
                      ? Math.round((category.completed / category.total) * 100)
                      : 0}
                    %
                  </Badge>
                </div>
                <Progress
                  value={
                    category.total > 0
                      ? (category.completed / category.total) * 100
                      : 0
                  }
                  className="h-1 mt-2"
                />
              </div>
              <ScrollArea className="h-[400px] pr-4">
                <div className="space-y-2">
                  {category.items.map((item) => (
                    <CompletenessItemRow
                      key={item.id}
                      item={item}
                      userRole={userRole}
                      onUpdate={handleItemUpdate}
                    />
                  ))}
                </div>
              </ScrollArea>
            </TabsContent>
          ))}
        </Tabs>
      </CardContent>
    </Card>
  );
}