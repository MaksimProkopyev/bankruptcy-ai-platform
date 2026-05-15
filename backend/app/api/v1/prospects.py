"""Prospects API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_permission
from app.db.session import get_db
from app.schemas.prospect import (
    BulkConvertRequest,
    BulkConvertResponse,
    InboundProspectRequest,
    ProspectDetailResponse,
    ProspectFilters,
    ProspectListResponse,
    ProspectResponse,
    ProspectStatsResponse,
    RunParserResponse,
    SourceConfigResponse,
    SourceConfigUpdate,
)
from app.services.prospecting.service import ProspectingService

router = APIRouter()
service = ProspectingService()


@router.get("/", response_model=ProspectListResponse, dependencies=[Depends(require_permission("leads", "read"))])
async def list_prospects(
    status: Optional[str] = None,
    source_category: Optional[str] = None,
    source_type: Optional[str] = None,
    temperature: Optional[str] = None,
    region: Optional[str] = None,
    min_score: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    has_phone: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Список prospects с фильтрами и пагинацией."""
    filters = ProspectFilters(
        status=status,
        source_category=source_category,
        source_type=source_type,
        temperature=temperature,
        region=region,
        min_score=min_score,
        date_from=date_from,
        date_to=date_to,
        has_phone=has_phone,
        search=search,
    )
    prospects, total = await service.get_prospects(filters, page, per_page, db)
    pages = (total + per_page - 1) // per_page if total > 0 else 1
    return ProspectListResponse(
        items=prospects,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get(
    "/{prospect_id}", response_model=ProspectDetailResponse, dependencies=[Depends(require_permission("leads", "read"))]
)
async def get_prospect(
    prospect_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Детали prospect."""
    try:
        prospect = await service.get_prospect(str(prospect_id), db)
        return prospect
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/inbound", response_model=ProspectResponse)
async def create_inbound_prospect(
    request: InboundProspectRequest,
    db: AsyncSession = Depends(get_db),
):
    """Принять inbound prospect (универсальный — сайт, бот, реклама, ручной ввод)."""
    try:
        data = request.dict(exclude_none=True)
        prospect = await service.receive_inbound(request.source_type, data, db)
        return prospect
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/run/{source_type}", response_model=RunParserResponse, dependencies=[Depends(require_permission("leads", "write"))]
)
async def run_parser(
    source_type: str,
    db: AsyncSession = Depends(get_db),
):
    """Запустить автоматический парсер."""
    try:
        result = await service.run_parser(source_type, db)
        return RunParserResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-all", dependencies=[Depends(require_permission("leads", "write"))])
async def run_all_parsers(
    db: AsyncSession = Depends(get_db),
):
    """Запустить все автоматические парсеры."""
    try:
        result = await service.run_all_automated(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{prospect_id}/convert",
    response_model=ProspectResponse,
    dependencies=[Depends(require_permission("leads", "write"))],
)
async def convert_prospect(
    prospect_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Конвертировать в lead."""
    try:
        await service.convert_to_lead(str(prospect_id), db)
        # Возвращаем обновлённый prospect
        prospect = await service.get_prospect(str(prospect_id), db)
        return prospect
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/bulk-convert", response_model=BulkConvertResponse, dependencies=[Depends(require_permission("leads", "write"))]
)
async def bulk_convert_prospects(
    request: BulkConvertRequest,
    db: AsyncSession = Depends(get_db),
):
    """Массовая конвертация."""
    try:
        result = await service.bulk_convert([str(id) for id in request.prospect_ids], db)
        return BulkConvertResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{prospect_id}/reject",
    response_model=ProspectResponse,
    dependencies=[Depends(require_permission("leads", "write"))],
)
async def reject_prospect(
    prospect_id: UUID,
    reason: str = Query(..., description="Причина отказа"),
    db: AsyncSession = Depends(get_db),
):
    """Отклонить."""
    try:
        await service.reject(str(prospect_id), reason, db)
        prospect = await service.get_prospect(str(prospect_id), db)
        return prospect
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ProspectStatsResponse, dependencies=[Depends(require_permission("leads", "read"))])
async def get_stats(
    db: AsyncSession = Depends(get_db),
):
    """Статистика."""
    stats = await service.get_stats(db)
    return ProspectStatsResponse(**stats)


@router.get(
    "/sources", response_model=list[SourceConfigResponse], dependencies=[Depends(require_permission("leads", "read"))]
)
async def list_sources(
    db: AsyncSession = Depends(get_db),
):
    """Конфигурация источников."""
    sources = await service.get_sources(db)
    return sources


@router.patch(
    "/sources/{source_type}",
    response_model=SourceConfigResponse,
    dependencies=[Depends(require_permission("leads", "write"))],
)
async def update_source(
    source_type: str,
    updates: SourceConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Обновить конфигурацию источника."""
    try:
        source = await service.update_source(source_type, updates.dict(exclude_none=True), db)
        return source
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
