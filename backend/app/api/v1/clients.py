"""Clients API — manage bankruptcy clients."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.models import Client
from app.schemas.schemas import ClientCreate, ClientResponse
from app.core.permissions import require_permission

router = APIRouter()


@router.get("/", response_model=list[ClientResponse],
            dependencies=[Depends(require_permission("clients", "read"))])
async def list_clients(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Client).order_by(Client.created_at.desc())
    if search:
        query = query.where(
            Client.last_name.ilike(f"%{search}%")
            | Client.phone.ilike(f"%{search}%")
        )
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=ClientResponse, status_code=201,
             dependencies=[Depends(require_permission("clients", "write"))])
async def create_client(data: ClientCreate, db: AsyncSession = Depends(get_db)):
    client = Client(**data.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientResponse,
            dependencies=[Depends(require_permission("clients", "read"))])
async def get_client(client_id: UUID, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client
