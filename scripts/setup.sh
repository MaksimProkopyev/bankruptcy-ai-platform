#!/bin/bash
# First-run setup script
# Usage: ./scripts/setup.sh
#
# Waits for services, runs migration, seeds data.

set -e

echo "🚀 Bankruptcy AI Platform — First Run Setup"
echo "============================================"

# Wait for PostgreSQL
echo ""
echo "⏳ Waiting for PostgreSQL..."
until docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; do
  sleep 1
done
echo "✅ PostgreSQL is ready"

# Wait for Redis
echo "⏳ Waiting for Redis..."
until docker compose exec -T redis redis-cli ping > /dev/null 2>&1; do
  sleep 1
done
echo "✅ Redis is ready"

# Run migration
echo ""
echo "📦 Running database migration..."
docker compose exec -T backend bash -c "cd /app && alembic upgrade head"
echo "✅ Migration complete"

# Seed data
echo ""
echo "🌱 Seeding demo data..."
docker compose exec -T backend python -m scripts.seed
echo "✅ Seed complete"

# Create MinIO bucket
echo ""
echo "📁 Setting up file storage..."
docker compose exec -T minio mc alias set local http://localhost:9000 minio minio123 > /dev/null 2>&1 || true
docker compose exec -T minio mc mb local/bankruptcy-documents > /dev/null 2>&1 || true
echo "✅ MinIO bucket ready"

# Health checks
echo ""
echo "🏥 Health checks..."
echo -n "  Backend:  "
curl -sf http://localhost:8000/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'✅ {d[\"status\"]} (v{d[\"version\"]})')" 2>/dev/null || echo "❌ not responding"

echo -n "  AI Core:  "
curl -sf http://localhost:8001/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'✅ {d[\"status\"]}')" 2>/dev/null || echo "❌ not responding"

echo -n "  Frontend: "
curl -sf -o /dev/null -w "✅ HTTP %{http_code}\n" http://localhost:3000 2>/dev/null || echo "❌ not responding"

# Done
echo ""
echo "============================================"
echo "🎉 Setup complete! Services running at:"
echo ""
echo "  🌐 Frontend:     http://localhost:3000"
echo "  🔧 Backend API:  http://localhost:8000"
echo "  📚 API Docs:     http://localhost:8000/docs"
echo "  🤖 AI Core:      http://localhost:8001"
echo "  📦 MinIO:        http://localhost:9001"
echo ""
echo "  Login credentials:"
echo "  ─────────────────────────────────────────"
echo "  Admin:   admin@bankruptcy.ai / admin123"
echo "  Lawyer:  ivanov@bankruptcy.ai / lawyer123"
echo "  Manager: smirnova@bankruptcy.ai / manager123"
echo ""
echo "  Quick test: make new-case"
echo ""
