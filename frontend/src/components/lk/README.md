# Компоненты личного кабинета клиента

Компоненты для отображения прогресса сбора документов в личном кабинете клиента.

## Компоненты

### 1. ClientDocumentsView

Основной компонент для отображения всего прогресса сбора документов.

#### Props
```typescript
interface ClientDocumentsViewProps {
  caseId: string; // Идентификатор дела
}
```

#### Особенности
- Загружает данные о комплектности через API (`/api/v1/cases/{caseId}/completeness`)
- Отображает прогресс-бар и статистику
- Группирует документы по статусам:
  - **Нужно загрузить** (missing, rejected)
  - **На проверке** (uploaded, review)
  - **Принятые** (approved, waived)
- Предоставляет интерфейс для привязки загруженных документов
- Адаптивный дизайн для мобильных устройств

#### Использование
```tsx
import ClientDocumentsView from "@/components/lk/ClientDocumentsView";

export default function DocumentsPage() {
  const caseId = "550e8400-e29b-41d4-a716-446655440000";
  
  return (
    <div>
      <ClientDocumentsView caseId={caseId} />
    </div>
  );
}
```

### 2. ClientDocumentCard

Карточка отдельного документа с разными вариантами отображения.

#### Props
```typescript
interface ClientDocumentCardProps {
  item: CompletenessItemResponse; // Данные о пункте чеклиста
  onUpload: (itemId: string, documentId: string) => Promise<void>; // Обработчик привязки
  variant: "action" | "pending" | "complete"; // Вариант отображения
  availableDocuments?: Array<{ id: string; name: string }>; // Список доступных документов
}
```

#### Варианты отображения

1. **`action`** (missing, rejected)
   - Полная карточка с описанием и инструкциями
   - Поле для выбора документа
   - Кнопка привязки
   - Блок с причиной отклонения (если rejected)

2. **`pending`** (uploaded, review)
   - Компактная карточка
   - Статус и имя файла
   - Без действий (ожидание проверки)

3. **`complete`** (approved, waived)
   - Минималистичный вид (одна строка)
   - Иконка статуса и название
   - Для waived отображается "(не требуется)"

#### Маппинг статусов для клиента

| Статус API | Отображение для клиента | Цвет | Иконка |
|------------|-------------------------|------|--------|
| missing | "Нужно загрузить" | orange-500 | Upload |
| uploaded | "Загружен, ожидает проверки" | blue-500 | Clock |
| review | "На проверке у юриста" | yellow-500 | Eye |
| approved | "Принят ✓" | green-600 | CheckCircle2 |
| rejected | "Нужно заменить" | red-500 | AlertCircle |
| waived | "Не требуется" | gray-400 | MinusCircle |

## Требования к API

Компоненты используют API-клиент из `@/lib/api/completeness.ts`, который должен предоставлять:

1. `getCompleteness(caseId: string)` - получение прогресса комплектности
2. `updateChecklistItem(caseId, itemId, update)` - обновление статуса пункта
3. Типы данных: `CompletenessProgressResponse`, `CompletenessItemResponse`

## Интеграция с существующей страницей документов

Существующая страница `/lk/dokumenty` (`frontend/src/app/lk/dokumenty/page.tsx`) может быть обновлена для использования нового компонента:

```tsx
// Заменить текущую реализацию на:
import ClientDocumentsView from "@/components/lk/ClientDocumentsView";

export default function LkDocumentsPage() {
  // Получить caseId из контекста или параметров
  const caseId = "..." // из сессии или API
  
  return <ClientDocumentsView caseId={caseId} />;
}
```

## Особенности реализации

### Простой язык
- Используется дружелюбный, поддерживающий тон
- Юридический жаргон скрыт от клиента
- Подсказки "Как получить" помогают клиенту

### Мобильный дизайн
- Карточки адаптируются под экран
- Гриды перестраиваются на мобильных
- Кнопки удобного размера для касания

### Безопасность
- `legal_basis` не показывается клиенту
- `matched_by` и другие технические поля скрыты
- Показывается только необходимая информация

## Зависимости

- React 18+
- TypeScript
- Tailwind CSS
- lucide-react для иконок
- API-клиент из `@/lib/api/completeness.ts`

## Пример данных

Для тестирования можно использовать моковые данные:

```typescript
const mockItem: CompletenessItemResponse = {
  id: "item-1",
  checklist_item_id: "passport_main",
  name: "Паспорт гражданина РФ",
  category: "identity",
  required: true,
  description: "Копии всех заполненных страниц паспорта",
  legal_basis: "ФЗ-127 ст. 213.4",
  how_to_get: "Скан или качественное фото всех заполненных страниц",
  status: "missing",
  document_id: null,
  document_name: null,
  matched_by: null,
  reviewer_id: null,
  reviewed_at: null,
  rejection_reason: null,
  notes: null,
  accept_formats: ["PDF", "JPG", "PNG"],
  max_age_days: 30
};