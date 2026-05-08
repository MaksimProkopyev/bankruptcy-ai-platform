-- ============================================================
-- Bankruptcy AI Platform — Database Schema v1
-- PostgreSQL 16 + pgvector
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================
-- 1. USERS & AUTH (RBAC)
-- ============================================================

CREATE TYPE user_role AS ENUM (
    'admin',
    'operations_director',
    'lawyer',
    'paralegal',
    'client_manager',
    'marketer',
    'ai_engineer'
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    patronymic VARCHAR(100),
    role user_role NOT NULL,
    is_active BOOLEAN DEFAULT true,
    max_cases INT, -- лимит дел для юриста
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_email ON users(email);

-- ============================================================
-- 2. CLIENTS (клиенты — физлица)
-- ============================================================

CREATE TYPE marital_status AS ENUM (
    'single', 'married', 'divorced', 'widowed'
);

CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Персональные данные
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    patronymic VARCHAR(100),
    birth_date DATE,
    passport_series VARCHAR(4),
    passport_number VARCHAR(6),
    passport_issued_by TEXT,
    passport_issued_date DATE,
    inn VARCHAR(12),
    snils VARCHAR(14),
    
    -- Контакты
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    telegram_id VARCHAR(100),
    whatsapp_phone VARCHAR(20),
    preferred_channel VARCHAR(20) DEFAULT 'phone', -- phone, email, telegram, whatsapp
    
    -- Семья
    marital_status marital_status,
    has_dependents BOOLEAN DEFAULT false,
    dependents_count INT DEFAULT 0,
    
    -- Адрес
    registration_address TEXT,
    actual_address TEXT,
    region VARCHAR(100), -- регион для маршрутизации
    
    -- Занятость
    is_employed BOOLEAN,
    employer_name VARCHAR(255),
    monthly_income DECIMAL(12,2),
    employment_type VARCHAR(50), -- employed, self_employed, unemployed, pension, disability
    
    -- Источник
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(100),
    lead_source VARCHAR(50), -- website, telegram, whatsapp, phone, referral
    
    -- Метаданные
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_clients_phone ON clients(phone);
CREATE INDEX idx_clients_region ON clients(region);

-- ============================================================
-- 3. CASES (дела — центральная сущность)
-- ============================================================

CREATE TYPE case_status AS ENUM (
    -- Воронка до суда
    'lead',                    -- Лид (первичное обращение)
    'qualification',           -- Квалификация (AI-скоринг)
    'consultation',            -- Консультация с юристом
    'contract_signing',        -- Подписание договора
    'document_collection',     -- Сбор документов
    'document_review',         -- Проверка документов
    'application_preparation', -- Подготовка заявления
    'application_filed',       -- Заявление подано в суд
    
    -- В суде
    'court_accepted',          -- Суд принял заявление
    'hearing_scheduled',       -- Назначено заседание
    'procedure_started',       -- Процедура введена
    'creditors_registry',      -- Формирование реестра кредиторов
    'creditors_meeting',       -- Собрание кредиторов
    'asset_realization',       -- Реализация имущества
    'restructuring',           -- Реструктуризация
    
    -- Завершение
    'fu_report',               -- Отчёт финансового управляющего
    'completion',              -- Завершение процедуры
    'debt_discharged',         -- Долги списаны
    
    -- Особые статусы
    'on_hold',                 -- Приостановлено
    'rejected',                -- Отказ (не подходит)
    'cancelled',               -- Отменено клиентом
    'settlement'               -- Мировое соглашение
);

CREATE TYPE procedure_type AS ENUM (
    'asset_realization',  -- Реализация имущества
    'restructuring',      -- Реструктуризация долгов
    'settlement',         -- Мировое соглашение
    'extrajudicial',      -- Внесудебное (через МФЦ)
    'undetermined'        -- Ещё не определено
);

CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_number VARCHAR(50) UNIQUE, -- Внутренний номер дела
    court_case_number VARCHAR(100), -- Номер дела в суде (A56-12345/2025)
    
    -- Связи
    client_id UUID NOT NULL REFERENCES clients(id),
    assigned_lawyer_id UUID REFERENCES users(id),
    assigned_paralegal_id UUID REFERENCES users(id),
    assigned_manager_id UUID REFERENCES users(id),
    financial_manager_name VARCHAR(255), -- ФУ (внешний, не в системе)
    financial_manager_sro VARCHAR(255),  -- СРО финансового управляющего
    
    -- Статус и тип
    status case_status NOT NULL DEFAULT 'lead',
    procedure_type procedure_type DEFAULT 'undetermined',
    
    -- Финансовые данные
    total_debt DECIMAL(14,2),         -- Общая сумма долга
    secured_debt DECIMAL(14,2),       -- Обеспеченный долг
    unsecured_debt DECIMAL(14,2),     -- Необеспеченный долг
    alimony_debt DECIMAL(14,2),       -- Алименты (не списываются)
    
    -- AI-скоринг
    ai_score DECIMAL(5,2),            -- Оценка перспектив (0-100)
    ai_recommended_procedure procedure_type,
    ai_risk_level VARCHAR(20),        -- low, medium, high
    ai_scoring_date TIMESTAMPTZ,
    ai_scoring_details JSONB,         -- Полный отчёт AI
    
    -- Суд
    court_name VARCHAR(255),          -- Арбитражный суд
    court_region VARCHAR(100),
    filing_date DATE,                 -- Дата подачи
    acceptance_date DATE,             -- Дата принятия
    first_hearing_date DATE,          -- Первое заседание
    procedure_start_date DATE,        -- Дата введения процедуры
    completion_date DATE,             -- Дата завершения
    
    -- Стоимость
    service_fee DECIMAL(12,2),        -- Стоимость услуг
    court_fee DECIMAL(12,2),          -- Госпошлина
    fu_fee DECIMAL(12,2),             -- Вознаграждение ФУ
    publication_fee DECIMAL(12,2),    -- Публикации (ЕФРСБ, Коммерсантъ)
    total_cost DECIMAL(12,2),         -- Итого расходы
    
    -- Метаданные
    notes TEXT,
    tags VARCHAR(50)[],
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_cases_status ON cases(status);
CREATE INDEX idx_cases_client ON cases(client_id);
CREATE INDEX idx_cases_lawyer ON cases(assigned_lawyer_id);
CREATE INDEX idx_cases_court_number ON cases(court_case_number);
CREATE INDEX idx_cases_created ON cases(created_at DESC);

-- Автогенерация номера дела
CREATE SEQUENCE case_number_seq START 1;

CREATE OR REPLACE FUNCTION generate_case_number()
RETURNS TRIGGER AS $$
BEGIN
    NEW.case_number := 'BK-' || TO_CHAR(now(), 'YYYY') || '-' || LPAD(nextval('case_number_seq')::text, 5, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_case_number
    BEFORE INSERT ON cases
    FOR EACH ROW
    WHEN (NEW.case_number IS NULL)
    EXECUTE FUNCTION generate_case_number();

-- ============================================================
-- 4. CREDITORS (кредиторы)
-- ============================================================

CREATE TYPE creditor_type AS ENUM (
    'bank', 'mfo', 'individual', 'tax_authority', 'utility', 'other'
);

CREATE TABLE creditors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    
    name VARCHAR(255) NOT NULL,       -- Наименование кредитора
    creditor_type creditor_type NOT NULL,
    inn VARCHAR(12),
    
    -- Суммы
    principal_amount DECIMAL(14,2),   -- Основной долг
    interest_amount DECIMAL(14,2),    -- Проценты
    penalty_amount DECIMAL(14,2),     -- Штрафы/пени
    total_amount DECIMAL(14,2) NOT NULL,
    
    -- Документы
    contract_number VARCHAR(100),
    contract_date DATE,
    court_decision_number VARCHAR(100),  -- Если есть судебное решение
    enforcement_proceedings VARCHAR(100), -- Исполнительное производство
    
    -- Статус в реестре
    included_in_registry BOOLEAN DEFAULT false,
    registry_inclusion_date DATE,
    registry_queue INT, -- Очередь (1, 2, 3)
    
    is_secured BOOLEAN DEFAULT false,  -- Залоговый кредитор
    security_description TEXT,         -- Описание залога
    
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_creditors_case ON creditors(case_id);

-- ============================================================
-- 5. DOCUMENTS (документы)
-- ============================================================

CREATE TYPE document_type AS ENUM (
    -- Личные документы
    'passport', 'snils', 'inn_cert', 'marriage_cert', 'divorce_cert',
    'birth_cert', 'prenuptial_agreement',
    
    -- Финансовые
    'income_2ndfl', 'income_cert', 'bank_statement', 'credit_report',
    'credit_contract', 'payment_schedule',
    
    -- Имущество
    'egrn_extract', 'vehicle_title', 'property_valuation',
    
    -- Судебные
    'court_decision', 'enforcement_order', 'bankruptcy_application',
    'court_ruling', 'petition', 'objection',
    
    -- Процедура
    'creditors_registry', 'fu_report', 'asset_inventory',
    'efrsb_publication', 'kommersant_publication',
    
    -- Прочее
    'employment_cert', 'unemployment_cert', 'family_composition',
    'power_of_attorney', 'contract_with_client', 'invoice', 'other'
);

CREATE TYPE document_status AS ENUM (
    'pending',      -- Ожидает загрузки
    'uploaded',     -- Загружен
    'processing',   -- Обрабатывается AI (OCR)
    'extracted',    -- Данные извлечены
    'validated',    -- Проверен
    'rejected',     -- Отклонён (плохое качество, не тот документ)
    'archived'      -- В архиве
);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    
    document_type document_type NOT NULL,
    status document_status DEFAULT 'pending',
    
    -- Файл
    file_name VARCHAR(255),
    file_path VARCHAR(500),           -- S3/MinIO path
    file_size INT,
    mime_type VARCHAR(100),
    file_hash VARCHAR(64),            -- SHA-256 для дедупликации
    
    -- AI-обработка
    ocr_text TEXT,                    -- Распознанный текст
    extracted_data JSONB,             -- Структурированные данные
    ai_confidence DECIMAL(5,2),       -- Уверенность AI (0-100)
    ai_document_type document_type,   -- Тип, определённый AI
    ai_validation_notes TEXT,         -- Замечания AI
    
    -- Метаданные
    uploaded_by UUID REFERENCES users(id),
    uploaded_by_client BOOLEAN DEFAULT false,
    version INT DEFAULT 1,
    parent_document_id UUID REFERENCES documents(id), -- Для версионирования
    
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_documents_case ON documents(case_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_status ON documents(status);

-- Чек-лист документов по делу
CREATE TABLE document_checklist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    document_type document_type NOT NULL,
    is_required BOOLEAN DEFAULT true,
    is_collected BOOLEAN DEFAULT false,
    document_id UUID REFERENCES documents(id),
    requested_at TIMESTAMPTZ,          -- Когда запросили у клиента
    reminder_count INT DEFAULT 0,
    notes TEXT,
    
    UNIQUE(case_id, document_type)
);

-- ============================================================
-- 6. CASE EVENTS (события по делу — timeline)
-- ============================================================

CREATE TYPE event_type AS ENUM (
    'status_change', 'document_uploaded', 'document_requested',
    'court_hearing', 'court_ruling', 'deadline_set', 'deadline_reminder',
    'payment_received', 'payment_due', 'ai_scoring', 'ai_document_processed',
    'client_message', 'lawyer_note', 'fu_interaction',
    'efrsb_publication', 'kommersant_publication',
    'assignment_change', 'escalation', 'system_event'
);

CREATE TABLE case_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    
    event_type event_type NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    metadata JSONB,                    -- Дополнительные данные
    
    -- Кто создал
    created_by UUID REFERENCES users(id),
    is_system_event BOOLEAN DEFAULT false,
    is_visible_to_client BOOLEAN DEFAULT false, -- Показывать ли клиенту
    
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_events_case ON case_events(case_id);
CREATE INDEX idx_events_type ON case_events(event_type);
CREATE INDEX idx_events_created ON case_events(created_at DESC);

-- ============================================================
-- 7. DEADLINES (процессуальные сроки)
-- ============================================================

CREATE TYPE deadline_priority AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE deadline_status AS ENUM ('pending', 'completed', 'overdue', 'cancelled');

CREATE TABLE deadlines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    
    title VARCHAR(255) NOT NULL,
    description TEXT,
    due_date TIMESTAMPTZ NOT NULL,
    priority deadline_priority DEFAULT 'medium',
    status deadline_status DEFAULT 'pending',
    
    -- Напоминания
    remind_days_before INT[] DEFAULT '{7, 3, 1}',
    last_reminded_at TIMESTAMPTZ,
    
    assigned_to UUID REFERENCES users(id),
    completed_at TIMESTAMPTZ,
    completed_by UUID REFERENCES users(id),
    
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_deadlines_case ON deadlines(case_id);
CREATE INDEX idx_deadlines_due ON deadlines(due_date);
CREATE INDEX idx_deadlines_status ON deadlines(status);

-- ============================================================
-- 8. PAYMENTS (оплаты)
-- ============================================================

CREATE TYPE payment_type AS ENUM (
    'service_fee', 'court_fee', 'fu_deposit', 'publication_fee', 'other'
);

CREATE TYPE payment_status AS ENUM (
    'pending', 'paid', 'overdue', 'cancelled', 'refunded'
);

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    
    payment_type payment_type NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    status payment_status DEFAULT 'pending',
    
    due_date DATE,
    paid_date DATE,
    payment_method VARCHAR(50),        -- card, bank_transfer, cash
    transaction_id VARCHAR(255),
    
    invoice_number VARCHAR(50),
    invoice_file_path VARCHAR(500),
    
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_payments_case ON payments(case_id);
CREATE INDEX idx_payments_status ON payments(status);

-- ============================================================
-- 9. MESSAGES (коммуникации с клиентом)
-- ============================================================

CREATE TYPE message_channel AS ENUM (
    'chat', 'telegram', 'whatsapp', 'email', 'sms', 'phone_call'
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id),
    client_id UUID REFERENCES clients(id),
    
    channel message_channel NOT NULL,
    direction VARCHAR(10) NOT NULL,    -- 'inbound' | 'outbound'
    
    content TEXT NOT NULL,
    metadata JSONB,                    -- Канал-специфичные данные
    
    -- AI
    is_ai_generated BOOLEAN DEFAULT false,
    ai_agent_name VARCHAR(100),        -- Какой агент сгенерировал
    is_ai_handled BOOLEAN DEFAULT false, -- AI ответил без человека
    
    sent_by UUID REFERENCES users(id), -- NULL для AI/клиента
    read_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_messages_case ON messages(case_id);
CREATE INDEX idx_messages_client ON messages(client_id);
CREATE INDEX idx_messages_created ON messages(created_at DESC);

-- ============================================================
-- 10. AI TASKS (задачи для AI-ядра)
-- ============================================================

CREATE TYPE ai_task_status AS ENUM (
    'queued', 'processing', 'completed', 'failed', 'escalated'
);

CREATE TABLE ai_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id),
    
    agent_name VARCHAR(100) NOT NULL,  -- qualification, ocr, document_gen, scoring, etc.
    task_type VARCHAR(100) NOT NULL,   -- Конкретная задача
    
    status ai_task_status DEFAULT 'queued',
    priority INT DEFAULT 5,            -- 1=highest, 10=lowest
    
    -- Входные/выходные данные
    input_data JSONB NOT NULL,
    output_data JSONB,
    
    -- Метрики
    confidence_score DECIMAL(5,2),
    processing_time_ms INT,
    llm_tokens_used INT,
    llm_cost DECIMAL(8,4),
    
    -- Ошибки и эскалация
    error_message TEXT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    escalated_to UUID REFERENCES users(id),
    escalation_reason TEXT,
    
    created_at TIMESTAMPTZ DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_ai_tasks_status ON ai_tasks(status);
CREATE INDEX idx_ai_tasks_case ON ai_tasks(case_id);
CREATE INDEX idx_ai_tasks_agent ON ai_tasks(agent_name);

-- ============================================================
-- 11. RAG — Embeddings для базы знаний
-- ============================================================

CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    source_type VARCHAR(50) NOT NULL,  -- law, court_decision, template, faq, internal
    source_name VARCHAR(255) NOT NULL, -- ФЗ-127, Постановление Пленума ВС и т.д.
    source_url TEXT,
    
    chunk_text TEXT NOT NULL,
    chunk_index INT,
    
    embedding vector(1536),            -- OpenAI/Claude embedding dimension
    
    metadata JSONB,                    -- Статья, глава, дата и т.д.
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_kb_embedding ON knowledge_base 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_kb_source ON knowledge_base(source_type);

-- ============================================================
-- 12. AUDIT LOG
-- ============================================================

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,      -- create, update, delete, view, export
    entity_type VARCHAR(50) NOT NULL,  -- case, client, document, etc.
    entity_id UUID,
    
    changes JSONB,                     -- {field: {old: x, new: y}}
    ip_address INET,
    user_agent TEXT,
    
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audit_user ON audit_log(user_id);
CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);

-- ============================================================
-- 13. NOTIFICATIONS
-- ============================================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    user_id UUID REFERENCES users(id),  -- Для сотрудников
    client_id UUID REFERENCES clients(id), -- Для клиентов
    case_id UUID REFERENCES cases(id),
    
    title VARCHAR(255) NOT NULL,
    body TEXT,
    channel VARCHAR(20) DEFAULT 'in_app', -- in_app, push, email, sms
    
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_client ON notifications(client_id, is_read);

-- ============================================================
-- VIEWS для аналитики
-- ============================================================

-- Сводка по делам юриста
CREATE VIEW v_lawyer_workload AS
SELECT 
    u.id AS lawyer_id,
    u.first_name || ' ' || u.last_name AS lawyer_name,
    COUNT(c.id) AS total_cases,
    COUNT(c.id) FILTER (WHERE c.status IN ('lead','qualification','consultation')) AS pipeline_cases,
    COUNT(c.id) FILTER (WHERE c.status IN ('document_collection','document_review','application_preparation')) AS preparation_cases,
    COUNT(c.id) FILTER (WHERE c.status IN ('court_accepted','hearing_scheduled','procedure_started','creditors_registry','creditors_meeting','asset_realization','restructuring')) AS active_court_cases,
    COUNT(c.id) FILTER (WHERE c.status = 'debt_discharged') AS completed_cases
FROM users u
LEFT JOIN cases c ON c.assigned_lawyer_id = u.id
WHERE u.role = 'lawyer'
GROUP BY u.id, u.first_name, u.last_name;

-- Юнит-экономика по делам
CREATE VIEW v_case_economics AS
SELECT
    c.id,
    c.case_number,
    c.status,
    c.service_fee,
    COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'paid'), 0) AS total_paid,
    c.service_fee - COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'paid'), 0) AS outstanding,
    c.total_cost,
    c.service_fee - COALESCE(c.total_cost, 0) AS margin,
    c.created_at,
    c.completion_date,
    EXTRACT(DAY FROM COALESCE(c.completion_date, now()) - c.created_at) AS days_in_progress
FROM cases c
LEFT JOIN payments p ON p.case_id = c.id
GROUP BY c.id;

-- Воронка конверсий
CREATE VIEW v_funnel AS
SELECT
    DATE_TRUNC('month', created_at) AS month,
    COUNT(*) AS total_leads,
    COUNT(*) FILTER (WHERE status != 'lead') AS qualified,
    COUNT(*) FILTER (WHERE status NOT IN ('lead','qualification','rejected')) AS consultations,
    COUNT(*) FILTER (WHERE status NOT IN ('lead','qualification','consultation','rejected','cancelled')) AS contracts,
    COUNT(*) FILTER (WHERE status IN ('application_filed','court_accepted','hearing_scheduled','procedure_started','creditors_registry','creditors_meeting','asset_realization','restructuring','fu_report','completion','debt_discharged')) AS filed,
    COUNT(*) FILTER (WHERE status = 'debt_discharged') AS completed
FROM cases
GROUP BY DATE_TRUNC('month', created_at)
ORDER BY month DESC;
