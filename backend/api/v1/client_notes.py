"""
Client Notes API Endpoints (Temporary Stub)
TODO: Implement full notes system with database models
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from db.database import get_db
from core.auth import AuthUser, require_manager

router = APIRouter()


@router.get("/{client_id}/notes")
async def list_client_notes(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """List notes for a client (STUB - returns empty array)"""
    return []


@router.post("/{client_id}/notes")
async def create_client_note(
    client_id: UUID,
    note_data: dict,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Create a note for a client (STUB)"""
    return {
        "id": "stub-note-id",
        "client_id": str(client_id),
        "content": note_data.get("content", ""),
        "created_by": auth_user.username,
        "created_at": "2025-01-01T00:00:00Z"
    }


@router.put("/{client_id}/notes/{note_id}")
async def update_client_note(
    client_id: UUID,
    note_id: str,
    note_data: dict,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Update a client note (STUB)"""
    return {
        "id": note_id,
        "client_id": str(client_id),
        "content": note_data.get("content", ""),
        "updated_by": auth_user.username,
        "updated_at": "2025-01-01T00:00:00Z"
    }


@router.delete("/{client_id}/notes/{note_id}", status_code=204)
async def delete_client_note(
    client_id: UUID,
    note_id: str,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(require_manager)
):
    """Delete a client note (STUB)"""
    return None
