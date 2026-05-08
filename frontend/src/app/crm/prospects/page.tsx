"use client";

import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Play,
  Plus,
  Filter,
  Search,
  ChevronRight,
  RefreshCw,
  TrendingUp,
  Users,
  Target,
  BarChart3,
} from "lucide-react";

// Типы
interface Prospect {
  id: string;
  source_category: string;
  source_type: string;
  full_name: string | null;
  phone: string | null;
  email: string | null;
  region: string | null;
  debt_amount: number | null;
  debt_type: string | null;
  status: string;
  prospect_score: number;
  temperature: "hot" | "warm" | "cold";
  outreach_attempts: number;
  utm_source: string | null;
  referral_code: string | null;
  converted_lead_id: string | null;
  created_at: string;
  updated_at: string;
}

interface SourceConfig {
  source_type: string;
  display_name: string;
  display_icon: string;
  source_category: string;
  is_automated: boolean;
  is_enabled: boolean;
  last_run_at: string | null;
  last_run_count: number;
}

interface Stats {
  total: number;
  by_status: Record<string, number>;
  by_category: Record<string, number>;
  by_temperature: Record<string, number>;
  conversion_rate: number;
  today_count: number;
  week_count: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ProspectsPage() {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [sources, setSources] = useState<SourceConfig[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedProspect, setSelectedProspect] = useState<Prospect | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [filters, setFilters] = useState({
    status: "",
    source_type: "",
    temperature: "",
    search: "",
  });
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Загрузка данных
  const loadData = async () => {
    setLoading(true);
    try {
      // Загрузка статистики
      const statsRes = await fetch(`${API_URL}/api/v1/prospects/stats`);
      const statsData = await statsRes.json();
      setStats(statsData);

      // Загрузка источников
      const sourcesRes = await fetch(`${API_URL}/api/v1/prospects/sources`);
      const sourcesData = await sourcesRes.json();
      setSources(sourcesData);

      // Загрузка prospects
      const query = new URLSearchParams();
      if (filters.status) query.set("status", filters.status);
      if (filters.source_type) query.set("source_type", filters.source_type);
      if (filters.temperature) query.set("temperature", filters.temperature);
      if (filters.search) query.set("search", filters.search);
      query.set("page", page.toString());
      query.set("per_page", "20");

      const prospectsRes = await fetch(`${API_URL}/api/v1/prospects?${query}`);
      const prospectsData = await prospectsRes.json();
      setProspects(prospectsData.items);
      setTotalPages(prospectsData.pages);
    } catch (error) {
      console.error("Ошибка загрузки данных:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [filters, page]);

  // Запуск парсера
  const runParser = async (sourceType: string) => {
    try {
      await fetch(`${API_URL}/api/v1/prospects/run/${sourceType}`, {
        method: "POST",
      });
      loadData(); // Перезагрузить данные
    } catch (error) {
      console.error("Ошибка запуска парсера:", error);
    }
  };

  // Конвертация
  const convertProspect = async (id: string) => {
    try {
      await fetch(`${API_URL}/api/v1/prospects/${id}/convert`, {
        method: "POST",
      });
      loadData();
    } catch (error) {
      console.error("Ошибка конвертации:", error);
    }
  };

  // Массовая конвертация
  const bulkConvert = async () => {
    if (selectedIds.length === 0) return;
    try {
      await fetch(`${API_URL}/api/v1/prospects/bulk-convert`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prospect_ids: selectedIds }),
      });
      setSelectedIds([]);
      loadData();
    } catch (error) {
      console.error("Ошибка массовой конвертации:", error);
    }
  };

  // Отклонение
  const rejectProspect = async (id: string, reason: string) => {
    try {
      await fetch(`${API_URL}/api/v1/prospects/${id}/reject?reason=${encodeURIComponent(reason)}`, {
        method: "POST",
      });
      loadData();
    } catch (error) {
      console.error("Ошибка отклонения:", error);
    }
  };

  // Вспомогательные функции
  const getTemperatureColor = (temp: string) => {
    switch (temp) {
      case "hot": return "bg-red-100 text-red-700";
      case "warm": return "bg-amber-100 text-amber-700";
      case "cold": return "bg-gray-100 text-gray-600";
      default: return "bg-gray-100 text-gray-600";
    }
  };

  const formatCurrency = (amount: number | null) => {
    if (!amount) return "—";
    return new Intl.NumberFormat("ru-RU", {
      style: "currency",
      currency: "RUB",
      maximumFractionDigits: 0,
    }).format(amount);
  };

  if (loading && !stats) {
    return <div className="p-8 text-center">Загрузка...</div>;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Заголовок */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-serif font-bold text-[#1B2A4A]">Лидогенерация</h1>
          <p className="text-[#6B7280]">Управление потенциальными клиентами из всех источников</p>
        </div>
        <div className="flex gap-2">
          <Dialog>
            <DialogTrigger asChild>
              <Button className="bg-[#C9A84C] hover:bg-[#B8973F] text-white">
                <Plus className="w-4 h-4 mr-2" /> Добавить
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Добавить prospect вручную</DialogTitle>
                <DialogDescription>
                  Заполните данные для ручного ввода prospect.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <Input placeholder="ФИО" />
                <Input placeholder="Телефон" />
                <Input placeholder="Email" />
                <Input placeholder="Регион" />
                <Button className="w-full">Сохранить</Button>
              </div>
            </DialogContent>
          </Dialog>
          <Button variant="outline" className="border-[#1B3A5C] text-[#1B3A5C]">
            <RefreshCw className="w-4 h-4 mr-2" /> Обновить
          </Button>
        </div>
      </div>

      {/* Статистика */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-[#6B7280]">Всего</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-[#1B2A4A]">{stats?.total || 0}</div>
            <p className="text-xs text-[#6B7280]">prospects</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-[#6B7280] flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-red-500" /> Hot
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">{stats?.by_temperature?.hot || 0}</div>
            <p className="text-xs text-[#6B7280]">высокий приоритет</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-[#6B7280] flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-amber-500" /> Warm
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-amber-600">{stats?.by_temperature?.warm || 0}</div>
            <p className="text-xs text-[#6B7280]">средний приоритет</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-[#6B7280]">Конверсия</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-[#1B2A4A]">{stats?.conversion_rate ? `${(stats.conversion_rate * 100).toFixed(1)}%` : "0%"}</div>
            <p className="text-xs text-[#6B7280]">в лиды</p>
          </CardContent>
        </Card>
      </div>

      {/* Источники (горизонтальный скролл) */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Источники</h2>
        <ScrollArea className="w-full">
          <div className="flex gap-3 pb-2">
            {sources.map((source) => (
              <Card key={source.source_type} className="min-w-[180px]">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <span>{source.display_icon}</span>
                    {source.display_name}
                  </CardTitle>
                  <CardDescription>
                    {source.last_run_count > 0 ? `${source.last_run_count} записей` : "Нет данных"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <span className="text-2xl font-bold">
                      {prospects.filter(p => p.source_type === source.source_type).length}
                    </span>
                    {source.is_automated && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => runParser(source.source_type)}
                        disabled={!source.is_enabled}
                      >
                        <Play className="w-3 h-3" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </ScrollArea>
      </div>

      {/* Фильтры */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 flex flex-wrap gap-2">
              <Select value={filters.status} onValueChange={(v) => setFilters({ ...filters, status: v })}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Статус" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Все статусы</SelectItem>
                  <SelectItem value="new">Новый</SelectItem>
                  <SelectItem value="enriched">Обогащён</SelectItem>
                  <SelectItem value="contacted">Контакт</SelectItem>
                  <SelectItem value="converted">Конвертирован</SelectItem>
                  <SelectItem value="rejected">Отклонён</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filters.source_type} onValueChange={(v) => setFilters({ ...filters, source_type: v })}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Источник" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Все источники</SelectItem>
                  {Array.from(new Set(sources.map(s => s.source_category))).map(cat => (
                    <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={filters.temperature} onValueChange={(v) => setFilters({ ...filters, temperature: v })}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Температура" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Все</SelectItem>
                  <SelectItem value="hot">Hot</SelectItem>
                  <SelectItem value="warm">Warm</SelectItem>
                  <SelectItem value="cold">Cold</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="Поиск по ФИО, телефону..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="max-w-xs"
              />
              <Button variant="outline">
                <Search className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Таблица */}
      <Card>
        <CardHeader>
          <CardTitle>Prospects</CardTitle>
          <CardDescription>
            {prospects.length} из {stats?.total} записей
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">
                  <Checkbox
                    checked={selectedIds.length === prospects.length && prospects.length > 0}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setSelectedIds(prospects.map(p => p.id));
                      } else {
                        setSelectedIds([]);
                      }
                    }}
                  />
                </TableHead>
                <TableHead>Темп.</TableHead>
                <TableHead>ФИО</TableHead>
                <TableHead>Регион</TableHead>
                <TableHead>Долг</TableHead>
                <TableHead>Источник</TableHead>
                <TableHead>Скор</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead className="text-right">Действия</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {prospects.map((prospect) => (
                <TableRow
                  key={prospect.id}
                  className="hover:bg-[#F8F7F4] cursor-pointer"
                  onClick={() => setSelectedProspect(prospect)}
                >
                  <TableCell>
                    <Checkbox
                      checked={selectedIds.includes(prospect.id)}
                      onCheckedChange={(checked) => {
                        if (checked) {
                          setSelectedIds([...selectedIds, prospect.id]);
                        } else {
                          setSelectedIds(selectedIds.filter(id => id !== prospect.id));
                        }
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Badge className={getTemperatureColor(prospect.temperature)}>
                      {prospect.temperature}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-medium">
                    {prospect.full_name || "—"}
                  </TableCell>
                  <TableCell>{prospect.region || "—"}</TableCell>
                  <TableCell>{formatCurrency(prospect.debt_amount)}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <span>{sources.find(s => s.source_type === prospect.source_type)?.display_icon || "📄"}</span>
                      <span className="text-sm">{prospect.source_type}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="font-bold">{prospect.prospect_score}</div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{prospect.status}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={(e) => {
                        e.stopPropagation();
                        convertProspect(prospect.id);
                      }}
                      disabled={prospect.status === "converted"}
                    >
                      Конвертировать
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Пагинация */}
          <div className="flex items-center justify-between mt-4">
            <div className="text-sm text-[#6B7280]">
              Выбрано: {selectedIds.length}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
              >
                Назад
              </Button>
              <span className="flex items-center px-3">
                Страница {page} из {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page === totalPages}
              >
                Вперёд
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Массовые действия */}
      {selectedIds.length > 0 && (
        <Card className="sticky bottom-4 border-[#C9A84C]">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="font-medium">
                Выбрано {selectedIds.length} prospects
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setSelectedIds([])}
                >
                  Снять выделение
                </Button>
                <Button
                  className="bg-[#C9A84C] hover:bg-[#B8973F]"
                  onClick={bulkConvert}
                >
                  Конвертировать ({selectedIds.length})
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Детали prospect (Sheet) */}
      <Sheet open={!!selectedProspect} onOpenChange={(open) => !open && setSelectedProspect(null)}>
        <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
          {selectedProspect && (
            <>
              <SheetHeader>
                <SheetTitle>{selectedProspect.full_name || "Без имени"}</SheetTitle>
                <SheetDescription>
                  {selectedProspect.source_type} • {new Date(selectedProspect.created_at).toLocaleDateString("ru-RU")}
                </SheetDescription>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-sm font-medium text-[#6B7280]">Телефон</h4>
                    <p>{selectedProspect.phone || "—"}</p>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-[#6B7280]">Email</h4>
                    <p>{selectedProspect.email || "—"}</p>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-[#6B7280]">Регион</h4>
                    <p>{selectedProspect.region || "—"}</p>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-[#6B7280]">Долг</h4>
                    <p>{formatCurrency(selectedProspect.debt_amount)}</p>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-[#6B7280]">Температура</h4>
                    <Badge className={getTemperatureColor(selectedProspect.temperature)}>
                      {selectedProspect.temperature} ({selectedProspect.prospect_score})
                    </Badge>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-[#6B7280]">Статус</h4>
                    <Badge variant="outline">{selectedProspect.status}</Badge>
                  </div>
                </div>

                <Separator />

                <div>
                  <h4 className="text-sm font-medium text-[#6B7280] mb-2">Действия</h4>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => convertProspect(selectedProspect.id)}
                      disabled={selectedProspect.status === "converted"}
                    >
                      Конвертировать в лид
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => rejectProspect(selectedProspect.id, "Ручное отклонение")}
                    >
                      Отклонить
                    </Button>
                  </div>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}