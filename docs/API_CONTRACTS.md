# API Contracts

## Backend ↔ AI Core

AI Core runs on port 8001. Backend calls it for all AI operations.

### POST /qualify
Qualification scoring — determines bankruptcy eligibility.

**Request:**
```json
{
  "total_debt": 850000,
  "creditors_count": 4,
  "creditor_types": ["bank", "mfo"],
  "monthly_income": 35000,
  "is_employed": true,
  "has_property": false,
  "property_types": [],
  "has_transactions_3y": false,
  "marital_status": "married",
  "has_enforcement_proceedings": false,
  "region": "Москва"
}
```

**Response (200):**
```json
{
  "is_eligible": true,
  "recommended_procedure": "judicial",
  "procedure_type": "asset_realization",
  "estimated_cost_min": 95000,
  "estimated_cost_max": 120000,
  "estimated_duration_months_min": 8,
  "estimated_duration_months_max": 12,
  "risk_level": "low",
  "risk_factors": [],
  "confidence": 0.92,
  "explanation": "Клиент подходит под судебное банкротство...",
  "needs_lawyer_review": false
}
```

### POST /chat
Conversational chatbot — multi-turn qualification dialog.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "У меня долг 500 тысяч"}
  ],
  "session_id": "abc-123",
  "context": {"channel": "website"}
}
```

**Response (200):**
```json
{
  "reply": "Понял. Перед кем у вас долги?",
  "action": null,
  "action_data": null,
  "session_id": "abc-123"
}
```

When qualification data is collected:
```json
{
  "reply": "Спасибо! Подготовлю оценку...",
  "action": "qualify",
  "action_data": { /* QualificationInput */ },
  "session_id": "abc-123"
}
```

### POST /ocr (Sprint 3)
Document OCR + data extraction.

**Request:**
```json
{
  "file_path": "s3://documents/passport_123.jpg",
  "document_type_hint": "passport"
}
```

**Response (200):**
```json
{
  "detected_type": "passport",
  "confidence": 0.97,
  "extracted_text": "...",
  "structured_data": {
    "full_name": "Иванов Иван Иванович",
    "series": "4510",
    "number": "123456",
    "issued_by": "ОВД...",
    "issued_date": "2015-03-15",
    "birth_date": "1990-05-20"
  },
  "processing_time_ms": 2300
}
```

### POST /generate-document (Sprint 6)
Legal document generation from template + case data.

**Request:**
```json
{
  "template": "bankruptcy_application",
  "case_data": { /* case fields */ },
  "client_data": { /* client fields */ },
  "creditors_data": [ /* creditor list */ ]
}
```

---

## Backend → Frontend

### Auth
- `POST /api/v1/auth/login` → `{access_token}`
- `POST /api/v1/auth/seed-admin` → creates first admin
- `GET /api/v1/auth/me` → current user (requires Bearer token)

### Cases
- `GET /api/v1/cases/?status=X&page=1` → list
- `GET /api/v1/cases/{id}` → detail with client, creditors, docs, deadlines
- `GET /api/v1/cases/{id}/transitions` → available status transitions
- `GET /api/v1/cases/{id}/checklist` → document checklist with progress
- `POST /api/v1/cases/` → create
- `PATCH /api/v1/cases/{id}` → update (status validated by state machine)
- `POST /api/v1/cases/{id}/creditors` → add creditor
- `POST /api/v1/cases/{id}/deadlines` → add deadline
- `GET /api/v1/cases/{id}/timeline` → events

### Clients
- `GET /api/v1/clients/?search=X` → list with search
- `POST /api/v1/clients/` → create
- `GET /api/v1/clients/{id}` → detail

### Users
- `GET /api/v1/users/` → list (admin)
- `GET /api/v1/users/lawyers` → lawyers with case load
- `PATCH /api/v1/users/{id}` → activate/deactivate (admin)

### Analytics
- `GET /api/v1/analytics/summary` → total/active cases, revenue
- `GET /api/v1/analytics/funnel` → monthly conversion funnel
- `GET /api/v1/analytics/lawyer-workload` → cases per lawyer
- `GET /api/v1/analytics/unit-economics` → per-case margin

---

## Case Status Transitions (State Machine)

```
lead → qualification → consultation → contract_signing → document_collection
                                                              ↓
                                          document_review ↔ application_preparation
                                                              ↓
                                                        application_filed
                                                              ↓
                                                        court_accepted
                                                              ↓
                                                       hearing_scheduled
                                                              ↓
                                                       procedure_started
                                                        ↙          ↘
                                            asset_realization   restructuring
                                                        ↘          ↙
                                                         fu_report
                                                              ↓
                                                         completion
                                                              ↓
                                                       debt_discharged ✓
```

Special states: `on_hold` (can pause most active states), `rejected`, `cancelled`, `settlement`.
