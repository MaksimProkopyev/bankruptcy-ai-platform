"""Seed script — populates DB with demo data for development.

Usage: python -m scripts.seed
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.models import (
    Case,
    CaseEvent,
    CaseStatus,
    Client,
    Creditor,
    Deadline,
    Payment,
    ProcedureType,
    User,
    UserRole,
)

LAWYERS = [
    {"first_name": "Алексей", "last_name": "Иванов", "email": "ivanov@bankruptcy.ai"},
    {"first_name": "Мария", "last_name": "Петрова", "email": "petrova@bankruptcy.ai"},
    {"first_name": "Дмитрий", "last_name": "Козлов", "email": "kozlov@bankruptcy.ai"},
]

MANAGERS = [
    {"first_name": "Елена", "last_name": "Смирнова", "email": "smirnova@bankruptcy.ai"},
]

CLIENTS_DATA = [
    {"first_name": "Иван", "last_name": "Сидоров", "phone": "+79001234501", "region": "Москва", "debt": 1_250_000},
    {
        "first_name": "Ольга",
        "last_name": "Новикова",
        "phone": "+79001234502",
        "region": "Санкт-Петербург",
        "debt": 780_000,
    },
    {
        "first_name": "Андрей",
        "last_name": "Морозов",
        "phone": "+79001234503",
        "region": "Новосибирск",
        "debt": 2_400_000,
    },
    {
        "first_name": "Наталья",
        "last_name": "Волкова",
        "phone": "+79001234504",
        "region": "Екатеринбург",
        "debt": 560_000,
    },
    {"first_name": "Сергей", "last_name": "Лебедев", "phone": "+79001234505", "region": "Казань", "debt": 3_100_000},
    {"first_name": "Татьяна", "last_name": "Кузнецова", "phone": "+79001234506", "region": "Москва", "debt": 920_000},
    {"first_name": "Павел", "last_name": "Соколов", "phone": "+79001234507", "region": "Краснодар", "debt": 450_000},
    {"first_name": "Анна", "last_name": "Попова", "phone": "+79001234508", "region": "Москва", "debt": 1_800_000},
    {"first_name": "Виктор", "last_name": "Егоров", "phone": "+79001234509", "region": "Воронеж", "debt": 670_000},
    {"first_name": "Людмила", "last_name": "Козлова", "phone": "+79001234510", "region": "Самара", "debt": 1_050_000},
    {"first_name": "Михаил", "last_name": "Степанов", "phone": "+79001234511", "region": "Москва", "debt": 5_200_000},
    {
        "first_name": "Екатерина",
        "last_name": "Фёдорова",
        "phone": "+79001234512",
        "region": "Ростов-на-Дону",
        "debt": 340_000,
    },
]

BANK_NAMES = ["Сбербанк", "ВТБ", "Альфа-Банк", "Тинькофф", "Газпромбанк", "Россельхозбанк", "Райффайзен"]
MFO_NAMES = ["Займер", "MoneyMan", "Вивус", "Е-Капуста", "МигКредит"]

STATUSES_DISTRIBUTION = [
    (CaseStatus.lead, 2),
    (CaseStatus.qualification, 1),
    (CaseStatus.consultation, 1),
    (CaseStatus.document_collection, 2),
    (CaseStatus.application_preparation, 1),
    (CaseStatus.application_filed, 1),
    (CaseStatus.procedure_started, 1),
    (CaseStatus.asset_realization, 1),
    (CaseStatus.debt_discharged, 2),
]


async def seed():
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        from sqlalchemy import func, select

        count = await db.execute(select(func.count(User.id)))
        if count.scalar_one() > 0:
            print("Database already has data. Skipping seed.")
            return

        print("Seeding database...")

        # 1. Admin user
        admin = User(
            email="admin@bankruptcy.ai",
            password_hash=hash_password("admin123"),
            first_name="Администратор",
            last_name="Системы",
            role=UserRole.admin,
            is_active=True,
        )
        db.add(admin)

        # 2. Lawyers
        lawyer_users = []
        for data in LAWYERS:
            u = User(
                email=data["email"],
                password_hash=hash_password("lawyer123"),
                first_name=data["first_name"],
                last_name=data["last_name"],
                role=UserRole.lawyer,
                is_active=True,
                max_cases=25,
            )
            db.add(u)
            lawyer_users.append(u)

        # 3. Managers
        for data in MANAGERS:
            u = User(
                email=data["email"],
                password_hash=hash_password("manager123"),
                first_name=data["first_name"],
                last_name=data["last_name"],
                role=UserRole.client_manager,
                is_active=True,
            )
            db.add(u)

        # 4. AI Engineer
        ai_eng = User(
            email="ai@bankruptcy.ai",
            password_hash=hash_password("engineer123"),
            first_name="AI",
            last_name="Инженер",
            role=UserRole.ai_engineer,
            is_active=True,
        )
        db.add(ai_eng)

        await db.flush()

        # 5. Clients & Cases
        status_pool = []
        for status, count in STATUSES_DISTRIBUTION:
            status_pool.extend([status] * count)
        random.shuffle(status_pool)

        now = datetime.now(timezone.utc)

        for i, cdata in enumerate(CLIENTS_DATA):
            client = Client(
                first_name=cdata["first_name"],
                last_name=cdata["last_name"],
                phone=cdata["phone"],
                email=f"{cdata['last_name'].lower()}@mail.ru",
                region=cdata["region"],
                marital_status=random.choice(["single", "married", "divorced"]),
                is_employed=random.choice([True, False, False]),
                monthly_income=Decimal(random.randint(15000, 80000)) if random.random() > 0.3 else None,
                lead_source=random.choice(["website", "telegram", "whatsapp", "phone", "referral"]),
                utm_source=random.choice(["yandex", "google", "vk", None]),
                created_at=now - timedelta(days=random.randint(5, 120)),
            )
            db.add(client)
            await db.flush()

            status = status_pool[i % len(status_pool)]
            lawyer = random.choice(lawyer_users)

            procedure = ProcedureType.undetermined
            if status.value in ("asset_realization", "debt_discharged", "fu_report", "completion"):
                procedure = ProcedureType.asset_realization
            elif status.value == "restructuring":
                procedure = ProcedureType.restructuring

            ai_score = round(random.uniform(60, 98), 1) if status != CaseStatus.lead else None
            risk_level = random.choice(["low", "medium", "high"]) if ai_score else None

            case = Case(
                case_number=f"BK-2025-{10001 + i}",
                client_id=client.id,
                assigned_lawyer_id=lawyer.id if status != CaseStatus.lead else None,
                status=status,
                procedure_type=procedure,
                total_debt=Decimal(cdata["debt"]),
                ai_score=Decimal(str(ai_score)) if ai_score else None,
                ai_risk_level=risk_level,
                service_fee=Decimal(random.choice([80000, 90000, 100000, 110000, 120000])),
                court_name=f"Арбитражный суд {cdata['region']}"
                if status.value not in ("lead", "qualification", "consultation")
                else None,
                filing_date=(now - timedelta(days=random.randint(30, 90))).date()
                if status.value
                in ("application_filed", "court_accepted", "procedure_started", "asset_realization", "debt_discharged")
                else None,
                created_at=client.created_at,
            )
            db.add(case)
            await db.flush()

            # Creditors (2-5 per case)
            num_creditors = random.randint(2, 5)
            for j in range(num_creditors):
                is_bank = random.random() > 0.3
                creditor = Creditor(
                    case_id=case.id,
                    name=random.choice(BANK_NAMES) if is_bank else random.choice(MFO_NAMES),
                    creditor_type="bank" if is_bank else "mfo",
                    total_amount=Decimal(random.randint(50000, cdata["debt"] // 2)),
                    principal_amount=Decimal(random.randint(40000, cdata["debt"] // 3)),
                    is_secured=(j == 0 and random.random() > 0.7),
                    included_in_registry=status.value
                    in ("creditors_registry", "creditors_meeting", "asset_realization", "debt_discharged"),
                )
                db.add(creditor)

            # Events
            event = CaseEvent(
                case_id=case.id,
                event_type="status_change",
                title="Дело создано",
                description=f"Клиент {client.last_name} {client.first_name}, долг: {cdata['debt']:,} ₽",
                is_system_event=True,
                is_visible_to_client=True,
                created_at=case.created_at,
            )
            db.add(event)

            if ai_score:
                event2 = CaseEvent(
                    case_id=case.id,
                    event_type="ai_scoring",
                    title=f"AI-скоринг: {ai_score}%",
                    description=f"Рекомендуемая процедура: {procedure.value}. Риск: {risk_level}",
                    is_system_event=True,
                    is_visible_to_client=False,
                    created_at=case.created_at + timedelta(minutes=5),
                )
                db.add(event2)

            # Deadlines for active cases
            if status.value in (
                "document_collection",
                "application_preparation",
                "application_filed",
                "procedure_started",
                "asset_realization",
            ):
                deadline = Deadline(
                    case_id=case.id,
                    title=random.choice(
                        [
                            "Подать заявление в суд",
                            "Собрать недостающие документы",
                            "Подготовить отзыв на требования",
                            "Публикация в ЕФРСБ",
                            "Подготовка к заседанию",
                        ]
                    ),
                    due_date=now + timedelta(days=random.randint(3, 30)),
                    priority=random.choice(["medium", "high", "critical"]),
                    status="pending",
                    assigned_to=lawyer.id,
                )
                db.add(deadline)

            # Payments
            if status.value not in ("lead", "qualification", "rejected"):
                payment = Payment(
                    case_id=case.id,
                    payment_type="service_fee",
                    amount=case.service_fee or Decimal(100000),
                    status=random.choice(["paid", "paid", "pending"]),
                    paid_date=(now - timedelta(days=random.randint(5, 60))).date() if random.random() > 0.3 else None,
                )
                db.add(payment)

        await db.commit()
        print(f"Seeded: 1 admin, {len(LAWYERS)} lawyers, {len(MANAGERS)} managers, 1 AI engineer")
        print(f"Seeded: {len(CLIENTS_DATA)} clients with cases, creditors, events, deadlines, payments")
        print("\nLogin credentials:")
        print("  Admin:   admin@bankruptcy.ai / admin123")
        print("  Lawyer:  ivanov@bankruptcy.ai / lawyer123")
        print("  Manager: smirnova@bankruptcy.ai / manager123")


if __name__ == "__main__":
    asyncio.run(seed())
