"""RBAC: RLS policies on core tables

Revision ID: 010_rbac_rls
Revises: 009_clients_user_id
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = '010_rbac_rls'
down_revision = '009_clients_user_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Создать роль приложения если не существует
    conn.execute(sa.text("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
                CREATE ROLE app_user;
            END IF;
        END
        $$;
    """))

    # 2. Включить RLS на ключевых таблицах
    for table in ["cases", "documents", "payments", "messages",
                  "notifications", "deadlines", "case_events",
                  "case_checklist_items", "creditors"]:
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))

    # 3. Политики для таблицы cases
    conn.execute(sa.text("""
        CREATE POLICY cases_admin_all ON cases
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'operations_director')
            );
    """))
    conn.execute(sa.text("""
        CREATE POLICY cases_lawyer_own ON cases
            USING (
                current_setting('app.current_user_role', true) = 'lawyer'
                AND assigned_lawyer_id = current_setting('app.current_user_id', true)::uuid
            );
    """))
    conn.execute(sa.text("""
        CREATE POLICY cases_paralegal_own ON cases
            USING (
                current_setting('app.current_user_role', true) = 'paralegal'
                AND assigned_paralegal_id = current_setting('app.current_user_id', true)::uuid
            );
    """))
    conn.execute(sa.text("""
        CREATE POLICY cases_manager_own ON cases
            USING (
                current_setting('app.current_user_role', true) = 'client_manager'
                AND assigned_manager_id = current_setting('app.current_user_id', true)::uuid
            );
    """))
    conn.execute(sa.text("""
        CREATE POLICY cases_client_own ON cases
            USING (
                current_setting('app.current_user_role', true) = 'client'
                AND client_id IN (
                    SELECT id FROM clients
                    WHERE user_id = current_setting('app.current_user_id', true)::uuid
                )
            );
    """))

    # 4. Политики documents
    conn.execute(sa.text("""
        CREATE POLICY documents_by_case ON documents
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'operations_director')
                OR (
                    current_setting('app.current_user_role', true) = 'lawyer'
                    AND case_id IN (
                        SELECT id FROM cases
                        WHERE assigned_lawyer_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
                OR (
                    current_setting('app.current_user_role', true) = 'paralegal'
                    AND case_id IN (
                        SELECT id FROM cases
                        WHERE assigned_paralegal_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
                OR (
                    current_setting('app.current_user_role', true) = 'client_manager'
                    AND case_id IN (
                        SELECT id FROM cases
                        WHERE assigned_manager_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
                OR (
                    current_setting('app.current_user_role', true) = 'client'
                    AND case_id IN (
                        SELECT c.id FROM cases c
                        JOIN clients cl ON cl.id = c.client_id
                        WHERE cl.user_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
            );
    """))

    # 5. notifications
    conn.execute(sa.text("""
        CREATE POLICY notifications_own ON notifications
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'operations_director')
                OR (
                    current_setting('app.current_user_role', true) != 'client'
                    AND user_id = current_setting('app.current_user_id', true)::uuid
                )
                OR (
                    current_setting('app.current_user_role', true) = 'client'
                    AND client_id IN (
                        SELECT id FROM clients
                        WHERE user_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
            );
    """))

    # 6. payments
    conn.execute(sa.text("""
        CREATE POLICY payments_by_case ON payments
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'operations_director', 'client_manager')
                OR (
                    current_setting('app.current_user_role', true) = 'lawyer'
                    AND case_id IN (
                        SELECT id FROM cases
                        WHERE assigned_lawyer_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
                OR (
                    current_setting('app.current_user_role', true) = 'client'
                    AND case_id IN (
                        SELECT id FROM cases
                        WHERE client_id IN (
                            SELECT id FROM clients
                            WHERE user_id = current_setting('app.current_user_id', true)::uuid
                        )
                    )
                )
            );
    """))

    # 7. messages — messages.case_id confirmed present in model
    conn.execute(sa.text("""
        CREATE POLICY messages_by_case ON messages
            USING (
                current_setting('app.current_user_role', true) IN ('admin', 'operations_director')
                OR sent_by = current_setting('app.current_user_id', true)::uuid
                OR (
                    current_setting('app.current_user_role', true) IN ('lawyer', 'paralegal', 'client_manager')
                    AND case_id IN (
                        SELECT id FROM cases
                        WHERE assigned_lawyer_id = current_setting('app.current_user_id', true)::uuid
                           OR assigned_paralegal_id = current_setting('app.current_user_id', true)::uuid
                           OR assigned_manager_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
                OR (
                    current_setting('app.current_user_role', true) = 'client'
                    AND client_id IN (
                        SELECT id FROM clients
                        WHERE user_id = current_setting('app.current_user_id', true)::uuid
                    )
                )
            );
    """))

    # 8. deadlines, case_events, case_checklist_items, creditors
    for table in ["deadlines", "case_events", "case_checklist_items", "creditors"]:
        conn.execute(sa.text(f"""
            CREATE POLICY {table}_by_case ON {table}
                USING (
                    current_setting('app.current_user_role', true) IN ('admin', 'operations_director')
                    OR (
                        current_setting('app.current_user_role', true) IN ('lawyer', 'paralegal', 'client_manager')
                        AND case_id IN (
                            SELECT id FROM cases
                            WHERE assigned_lawyer_id = current_setting('app.current_user_id', true)::uuid
                               OR assigned_paralegal_id = current_setting('app.current_user_id', true)::uuid
                               OR assigned_manager_id = current_setting('app.current_user_id', true)::uuid
                        )
                    )
                    OR (
                        current_setting('app.current_user_role', true) = 'client'
                        AND case_id IN (
                            SELECT id FROM cases
                            WHERE client_id IN (
                                SELECT id FROM clients
                                WHERE user_id = current_setting('app.current_user_id', true)::uuid
                            )
                        )
                    )
                );
        """))


def downgrade() -> None:
    conn = op.get_bind()

    for table in ["cases", "documents", "payments", "messages",
                  "notifications", "deadlines", "case_events",
                  "case_checklist_items", "creditors"]:
        conn.execute(sa.text(f"""
            DO $$ DECLARE r RECORD;
            BEGIN
                FOR r IN SELECT policyname FROM pg_policies WHERE tablename = '{table}'
                LOOP
                    EXECUTE 'DROP POLICY IF EXISTS ' || r.policyname || ' ON {table}';
                END LOOP;
            END $$;
        """))
        conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))
