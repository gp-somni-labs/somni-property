"""
AI Chat API Endpoints
Property Manager & Tenant interaction with Somni AI Assistant
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from datetime import datetime

from db.database import get_db

logger = logging.getLogger(__name__)
from db.models import AIConversation, AIMessage, Tenant
from core.auth import get_auth_user, AuthUser
from services.ai_assistant import ai_assistant
from services.property_manager_ai import property_manager_ai
from services.mcp_powered_ai import mcp_powered_ai

router = APIRouter()


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None
    tenant_id: Optional[str] = None
    channel: str = "web"
    context: Optional[dict] = None  # Page context for property managers


class ChatResponse(BaseModel):
    message_id: str
    conversation_id: str
    response: str
    intent: Optional[str]
    confidence: Optional[float]
    actions: list
    suggestions: list
    timestamp: datetime


class ConversationStart(BaseModel):
    tenant_id: Optional[str] = None
    unit_id: Optional[str] = None
    conversation_type: str = "general"
    channel: str = "web"


# ============================================================================
# REST API ENDPOINTS
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    user_type: str = Query("manager", description="User type: manager, tenant, admin"),
    model: str = Query("auto", description="AI model to use: auto, anthropic, openai, ollama"),
    db: AsyncSession = Depends(get_db)
):
    """
    Send message to AI assistant and get response
    Supports both property managers and tenants
    """
    try:
        # Create or get conversation
        if request.conversation_id:
            conversation_id = request.conversation_id
        else:
            # Create new conversation
            conversation = AIConversation(
                id=str(uuid4()),
                tenant_id=request.tenant_id if user_type == "tenant" else None,
                channel=request.channel,
                status="active",
                user_type=user_type,
                started_at=datetime.now()
            )
            db.add(conversation)
            await db.flush()
            conversation_id = str(conversation.id)

        # Choose appropriate AI assistant based on user type
        if user_type == "manager":
            # Use MCP-powered AI with tool execution capabilities
            context = request.context if hasattr(request, 'context') else {}
            # Pass model selection to MCP AI
            context['model'] = model
            ai_response = await mcp_powered_ai.chat_with_tools(
                message=request.message,
                conversation_id=conversation_id,
                context=context,
                db=db
            )
        else:
            # Use tenant AI
            ai_response = await ai_assistant.chat(
                message=request.message,
                conversation_id=conversation_id,
                tenant_id=request.tenant_id,
                db=db
            )

        # Generate message_id for this response
        message_id = str(uuid4())

        return ChatResponse(
            message_id=message_id,
            conversation_id=conversation_id,
            response=ai_response["response"],
            intent=ai_response.get("intent"),
            confidence=ai_response.get("confidence"),
            actions=ai_response.get("actions", []),
            suggestions=ai_response.get("suggestions", []),
            timestamp=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


@router.post("/conversations/start")
async def start_conversation(
    request: ConversationStart,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(get_auth_user)
):
    """
    Start a new AI conversation
    """
    conversation = AIConversation(
        tenant_id=request.tenant_id,
        unit_id=request.unit_id,
        conversation_type=request.conversation_type,
        channel=request.channel,
        status="active"
    )

    db.add(conversation)
    await db.flush()

    return {
        "conversation_id": str(conversation.id),
        "started_at": conversation.started_at,
        "status": conversation.status
    }


@router.get("/conversations/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(get_auth_user)
):
    """
    Get conversation history
    """
    query = select(AIMessage).where(
        AIMessage.conversation_id == conversation_id
    ).order_by(AIMessage.message_timestamp).limit(limit)

    result = await db.execute(query)
    messages = result.scalars().all()

    return {
        "conversation_id": str(conversation_id),
        "message_count": len(messages),
        "messages": [
            {
                "id": str(msg.id),
                "sender_type": msg.sender_type,
                "message_text": msg.message_text,
                "timestamp": msg.message_timestamp,
                "intent": msg.intent,
                "confidence": float(msg.confidence_score) if msg.confidence_score else None
            }
            for msg in messages
        ]
    }


@router.get("/conversations/tenant/{tenant_id}")
async def get_tenant_conversations(
    tenant_id: UUID,
    status: Optional[str] = None,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(get_auth_user)
):
    """
    Get all conversations for a tenant
    """
    query = select(AIConversation).where(AIConversation.tenant_id == tenant_id)

    if status:
        query = query.where(AIConversation.status == status)

    query = query.order_by(AIConversation.started_at.desc()).limit(limit)

    result = await db.execute(query)
    conversations = result.scalars().all()

    return {
        "tenant_id": str(tenant_id),
        "total": len(conversations),
        "conversations": [
            {
                "id": str(conv.id),
                "type": conv.conversation_type,
                "channel": conv.channel,
                "started_at": conv.started_at,
                "status": conv.status,
                "escalated": conv.escalated_to_human
            }
            for conv in conversations
        ]
    }


@router.post("/conversations/{conversation_id}/end")
async def end_conversation(
    conversation_id: UUID,
    satisfaction_rating: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    auth_user: AuthUser = Depends(get_auth_user)
):
    """
    End a conversation
    """
    query = select(AIConversation).where(AIConversation.id == conversation_id)
    result = await db.execute(query)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.status = "completed"
    conversation.ended_at = datetime.now()

    if satisfaction_rating:
        conversation.satisfaction_rating = satisfaction_rating

    await db.commit()

    return {
        "conversation_id": str(conversation_id),
        "status": "completed",
        "ended_at": conversation.ended_at
    }


@router.get("/tools/available")
async def get_available_mcp_tools():
    """
    Get list of available MCP tools with descriptions
    """
    try:
        from services.somniproperty_mcp_server import somniproperty_mcp

        tools_manifest = somniproperty_mcp.get_tools_manifest()

        # Group tools by category
        categories = {}
        for tool in tools_manifest:
            # Determine category from tool name
            name = tool['name']
            if any(x in name for x in ['property', 'properties']):
                category = 'Properties'
            elif 'client' in name:
                category = 'Clients'
            elif 'tenant' in name:
                category = 'Tenants'
            elif 'lease' in name:
                category = 'Leases'
            elif 'work_order' in name or 'workorder' in name:
                category = 'Work Orders'
            elif 'payment' in name or 'invoice' in name:
                category = 'Payments'
            elif 'device' in name or 'smart' in name:
                category = 'Smart Devices'
            elif 'utility' in name or 'utilities' in name:
                category = 'Utilities'
            elif 'document' in name:
                category = 'Documents'
            elif any(x in name for x in ['unit', 'edge', 'sync']):
                category = 'Units & Edge Nodes'
            else:
                category = 'Analytics'

            if category not in categories:
                categories[category] = []

            categories[category].append({
                'name': name,
                'description': tool['description'],
                'schema': tool['inputSchema']
            })

        return {
            "categories": categories,
            "total": len(tools_manifest)
        }
    except Exception as e:
        logger.error(f"Failed to get MCP tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggestions")
async def get_contextual_suggestions(
    page: str = Query(..., description="Current page (dashboard, properties, clients, etc.)"),
    entity_id: Optional[str] = Query(None, description="Current entity ID if on detail page")
):
    """
    Get contextual AI suggestions based on current page
    """
    suggestions_map = {
        "dashboard": [
            "Show me today's priorities",
            "Which properties need attention?",
            "Summarize this week's work orders",
            "Show overdue rent payments"
        ],
        "properties": [
            "Compare property performance",
            "Which units are vacant?",
            "Show maintenance costs by property",
            "Generate property report"
        ],
        "clients": [
            "Which clients have upcoming renewals?",
            "Show client payment history",
            "Draft client communication",
            "Generate client invoice"
        ],
        "workorders": [
            "Show high-priority work orders",
            "Which contractors are available?",
            "Estimate completion times",
            "Group similar work orders"
        ],
        "tenants": [
            "Show late rent payments",
            "Which leases expire soon?",
            "Draft lease renewal notice",
            "Show tenant satisfaction trends"
        ],
        "utilities": [
            "Compare utility costs",
            "Identify unusual usage patterns",
            "Forecast next month's costs",
            "Show energy efficiency opportunities"
        ],
        "smartdevices": [
            "Which devices are offline?",
            "Show battery levels",
            "Troubleshoot connectivity issues",
            "Recommend automation improvements"
        ]
    }

    return {
        "page": page,
        "suggestions": suggestions_map.get(page, [
            "How can I help you?",
            "Show statistics",
            "Generate report"
        ])
    }


@router.post("/feedback")
async def provide_feedback(
    conversation_id: UUID,
    message_id: Optional[UUID],
    feedback_type: str,
    feedback_text: Optional[str],
    db: AsyncSession = Depends(get_db)
):
    """
    Provide feedback on AI response for training
    """
    from db.models import AITrainingFeedback

    feedback = AITrainingFeedback(
        conversation_id=conversation_id,
        message_id=message_id,
        feedback_type=feedback_type,
        feedback_text=feedback_text
    )

    db.add(feedback)
    await db.commit()

    return {"status": "feedback_recorded", "feedback_id": str(feedback.id)}


# ============================================================================
# WEBSOCKET ENDPOINT (Real-time chat)
# ============================================================================

@router.websocket("/ws/{conversation_id}")
async def websocket_chat(
    websocket: WebSocket,
    conversation_id: str,
    tenant_id: Optional[str] = None
):
    """
    WebSocket endpoint for real-time chat
    """
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message = data.get("message")

            if not message:
                continue

            # Get database session
            async for db in get_db():
                try:
                    # Process with AI
                    ai_response = await ai_assistant.chat(
                        message=message,
                        conversation_id=conversation_id,
                        tenant_id=tenant_id,
                        db=db
                    )

                    # Send response back to client
                    await websocket.send_json({
                        "type": "message",
                        "response": ai_response["response"],
                        "intent": ai_response.get("intent"),
                        "actions": ai_response.get("actions", []),
                        "suggestions": ai_response.get("suggestions", []),
                        "timestamp": datetime.now().isoformat()
                    })

                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "error": str(e)
                    })

    except WebSocketDisconnect:
        print(f"WebSocket disconnected for conversation {conversation_id}")
