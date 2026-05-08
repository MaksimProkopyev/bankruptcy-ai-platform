# Интеграция уведомлений комплектности с CompletenessChecker

## Добавленные файлы

1. `notifications.py` - `CompletenessNotifier` - сервис отправки уведомлений
2. `scheduler.py` - `CompletenessReminderScheduler` - планировщик напоминаний

## Интеграция с CompletenessChecker

Добавьте следующие строки в `checker.py`:

### 1. Импорт в начале файла:

```python
from .notifications import CompletenessNotifier
```

### 2. В методе `init_checklist()` после создания чеклиста:

```python
# После успешного создания чеклиста (после строки 108):
notifier = CompletenessNotifier(self._session)
required_count = sum(1 for item in checklist.items if item.required)
await notifier.notify_checklist_initialized(
    case_id=case_id,
    checklist_name=checklist.name,
    total_items=len(checklist.items),
    required_items=required_count,
)
```

### 3. В методе `update_item()` при статусе "rejected":

```python
# После обновления статуса (после строки 302, перед return):
if update.status == ChecklistItemStatus.REJECTED:
    # Получаем название документа
    checklist = self._matcher.get_checklist(db_item.checklist_id)
    checklist_item = next(
        (ci for ci in checklist.items if ci.id == db_item.checklist_item_id),
        None,
    )
    if checklist_item:
        notifier = CompletenessNotifier(self._session)
        await notifier.notify_document_rejected(
            case_id=case_id,
            document_name=checklist_item.name,
            rejection_reason=update.rejection_reason or "Не указана",
        )
```

### 4. В методе `update_item()` при статусе "uploaded":

```python
# После обновления статуса (после строки 302, перед return):
if update.status == ChecklistItemStatus.UPLOADED and update.document_id:
    # Получаем название документа и клиента
    checklist = self._matcher.get_checklist(db_item.checklist_id)
    checklist_item = next(
        (ci for ci in checklist.items if ci.id == db_item.checklist_item_id),
        None,
    )
    if checklist_item:
        notifier = CompletenessNotifier(self._session)
        client_name = await notifier._get_client_name(case_id)
        # Получаем имя документа из Document
        doc = await self._session.get(Document, update.document_id)
        document_name = doc.file_name if doc else checklist_item.name
        await notifier.notify_lawyer_document_uploaded(
            case_id=case_id,
            document_name=document_name,
            checklist_item_name=checklist_item.name,
            client_name=client_name,
        )
```

### 5. Проверка завершения комплектности после каждого обновления:

```python
# В конце метода update_item() после получения response (после строки 319):
# Проверяем, завершена ли комплектность
progress = await self.get_progress(case_id)
if progress.is_complete:
    notifier = CompletenessNotifier(self._session)
    client_name = await notifier._get_client_name(case_id)
    await notifier.notify_all_approved(case_id)
    await notifier.notify_lawyer_all_approved(case_id, client_name)
```

### 6. В методе `auto_match()` после успешного матчинга:

```python
# После успешного матчинга документа:
# Добавить проверку завершения комплектности аналогично пункту 5
```

## Запуск планировщика напоминаний

Добавьте в `main.py` или в startup hook:

```python
import asyncio
from backend.app.services.completeness.scheduler import reminder_loop
from backend.app.db.session import async_session_factory

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск фоновой задачи
    task = asyncio.create_task(reminder_loop(async_session_factory))
    
    yield
    
    # Остановка при завершении
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
```

## Требования к модели Notification

Текущая модель `Notification` в `models.py` не имеет поля `metadata`. Для полноценной работы рекомендуется добавить поле `metadata` типа `JSONB`:

```python
class Notification(Base):
    __tablename__ = "notifications"
    
    # ... существующие поля ...
    metadata = Column(JSONB)  # Добавить это поле
```

Временное решение: в `NotificationService.send()` поле `metadata` игнорируется, но логируется.

## Логирование

Все уведомления логируются с уровнем INFO. Ошибки отправки уведомлений логируются с уровнем ERROR, но не прерывают основной поток выполнения.