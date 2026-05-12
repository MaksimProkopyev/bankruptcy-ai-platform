"""
RBAC permission matrix и FastAPI dependencies.
Используется во всех роутерах через Depends().
"""
from typing import Set, Dict
from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.models import User, UserRole


# Матрица прав: resource -> action -> set of allowed roles
# resource = группа эндпоинтов (совпадает с префиксом роутера)
PERMISSIONS: Dict[str, Dict[str, Set[UserRole]]] = {
    "users": {
        "read":   {UserRole.admin, UserRole.operations_director},
        "write":  {UserRole.admin},
        "delete": {UserRole.admin},
    },
    "cases": {
        "read":   {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal, UserRole.client_manager, UserRole.client},
        "write":  {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.client_manager},
        "delete": {UserRole.admin, UserRole.operations_director},
    },
    "clients": {
        "read":   {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal, UserRole.client_manager, UserRole.marketer},
        "write":  {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.client_manager},
        "delete": {UserRole.admin, UserRole.operations_director},
    },
    "documents": {
        "read":   {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal, UserRole.client_manager, UserRole.client},
        "write":  {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal, UserRole.client_manager},
        "delete": {UserRole.admin, UserRole.operations_director, UserRole.lawyer},
    },
    "payments": {
        "read":   {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.client_manager, UserRole.client},
        "write":  {UserRole.admin, UserRole.operations_director, UserRole.client_manager},
        "delete": {UserRole.admin},
    },
    "leads": {
        "read":   {UserRole.admin, UserRole.operations_director, UserRole.client_manager,
                   UserRole.marketer},
        "write":  {UserRole.admin, UserRole.operations_director, UserRole.client_manager},
        "delete": {UserRole.admin, UserRole.operations_director},
    },
    "tasks": {
        "read":   {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal, UserRole.client_manager},
        "write":  {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal, UserRole.client_manager},
        "delete": {UserRole.admin, UserRole.operations_director},
    },
    "deadlines": {
        "read":   {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal, UserRole.client_manager, UserRole.client},
        "write":  {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal},
        "delete": {UserRole.admin, UserRole.operations_director, UserRole.lawyer},
    },
    "knowledge": {
        "read":   {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal, UserRole.ai_engineer},
        "write":  {UserRole.admin, UserRole.ai_engineer},
        "delete": {UserRole.admin},
    },
    "analytics": {
        "read":   {UserRole.admin, UserRole.operations_director, UserRole.marketer},
        "write":  {UserRole.admin},
        "delete": {UserRole.admin},
    },
    "admin": {
        "read":   {UserRole.admin},
        "write":  {UserRole.admin},
        "delete": {UserRole.admin},
    },
    "messages": {
        "read":   {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal, UserRole.client_manager, UserRole.client},
        "write":  {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal, UserRole.client_manager, UserRole.client},
        "delete": {UserRole.admin, UserRole.operations_director},
    },
    "ai_tasks": {
        "read":   {UserRole.admin, UserRole.ai_engineer, UserRole.operations_director},
        "write":  {UserRole.admin, UserRole.ai_engineer},
        "delete": {UserRole.admin},
    },
    "staff": {
        "read":   {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal, UserRole.client_manager, UserRole.marketer,
                   UserRole.ai_engineer},
        "write":  {UserRole.admin, UserRole.operations_director, UserRole.lawyer,
                   UserRole.paralegal, UserRole.client_manager, UserRole.marketer,
                   UserRole.ai_engineer},
        "delete": {UserRole.admin, UserRole.operations_director},
    },
}


def require_roles(*roles: UserRole):
    """
    FastAPI dependency. Пример использования:
        @router.get("/", dependencies=[Depends(require_roles(UserRole.admin, UserRole.lawyer))])
    или:
        current_user: User = Depends(require_roles(UserRole.admin))
    """
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Account inactive")
        if current_user.role not in {r.value for r in roles}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not allowed. "
                       f"Required: {[r.value for r in roles]}"
            )
        return current_user
    return _check


def require_permission(resource: str, action: str):
    """
    Dependency по матрице прав. Пример:
        @router.delete("/{id}", dependencies=[Depends(require_permission("cases", "delete"))])
    """
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Account inactive")
        allowed = PERMISSIONS.get(resource, {}).get(action, set())
        if current_user.role not in {r.value for r in allowed}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {resource}:{action}"
            )
        return current_user
    return _check


# Shorthand helpers (наиболее частые паттерны)
require_admin = require_roles(UserRole.admin)
require_admin_or_ops = require_roles(UserRole.admin, UserRole.operations_director)
require_staff = require_roles(
    UserRole.admin, UserRole.operations_director, UserRole.lawyer,
    UserRole.paralegal, UserRole.client_manager
)
