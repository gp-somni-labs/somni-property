"""
MCP-Powered AI Assistant
Multi-provider AI with MCP tool execution capabilities.
Supports OpenAI, Anthropic (Claude), and Ollama.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from services.llm_providers import (
    LLMFactory, LLMConfig, LLMMessage, LLMProvider,
    BaseLLMProvider
)
from services.somniproperty_mcp_server import somniproperty_mcp

logger = logging.getLogger(__name__)


class MCPPoweredAI:
    """
    AI Assistant with MCP tool execution capabilities
    Multi-provider support: OpenAI, Anthropic (Claude), Ollama

    This AI can:
    1. Understand natural language requests
    2. Determine which tools to use
    3. Execute tools via MCP
    4. Format results into natural language responses

    Example interactions:
    - "Show me all vacant units" → list_units(status="vacant")
    - "Create a work order for unit 101 leaking faucet" → create_work_order(...)
    - "Which properties have high vacancy rates?" → list_properties() + analytics
    - "Turn off the lights in unit 203" → control_device(...)

    Provider Selection:
    - Anthropic Claude: BEST for tool calling and reasoning (recommended for production)
    - OpenAI GPT-4: Excellent tool calling, widely available
    - Ollama (local): Privacy-focused, no API costs, good for development
    """

    def __init__(
        self,
        provider: LLMProvider = "auto",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        config: Optional[LLMConfig] = None
    ):
        # Use provided config or create from parameters
        if config:
            self.config = config
        else:
            self.config = LLMConfig(
                provider=provider,
                model=model,
                api_key=api_key
            )

        # Create LLM provider (will be set by async init)
        self.llm: Optional[BaseLLMProvider] = None
        self.mcp_server = somniproperty_mcp
        self._initialized = False

        logger.info(f"MCPPoweredAI initializing with provider preference: {self.config.provider}")

    async def _ensure_initialized(self):
        """Lazy initialization of LLM provider with fallback"""
        if self._initialized and self.llm:
            return

        try:
            if self.config.provider == "auto":
                # Use fallback cascade
                logger.info("Using automatic provider selection with fallback cascade")
                self.llm = await LLMFactory.create_with_fallback(
                    primary_provider=None,
                    api_key=self.config.api_key,
                    model=self.config.model
                )
            else:
                # Use specific provider
                self.llm = LLMFactory.create_provider(
                    provider=self.config.provider,
                    api_key=self.config.api_key,
                    model=self.config.model
                )

            self._initialized = True
            logger.info(f"✅ MCPPoweredAI initialized with {self.llm.model}")

        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
            raise

    async def chat_with_tools(
        self,
        message: str,
        conversation_id: str,
        context: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Main chat interface with MCP tool execution

        Flow:
        1. Detect intent
        2. Determine which MCP tools to use
        3. Execute tools
        4. Format results
        5. Generate natural language response
        """
        # Allow model override from context (frontend selection)
        model_override = context.get('model', 'auto')
        if model_override and model_override != 'auto' and model_override != self.config.provider:
            logger.info(f"🎛️ Model override requested: {model_override} (current: {self.config.provider})")
            # Temporarily switch provider if different from current
            from services.llm_providers import LLMConfig, LLMFactory
            temp_config = LLMConfig(provider=model_override)
            try:
                temp_llm = await LLMFactory.create_with_fallback(primary_provider=model_override)
                # Use temporary LLM for this request
                original_llm = self.llm
                self.llm = temp_llm
            except Exception as e:
                logger.warning(f"Failed to switch to {model_override}, using fallback: {e}")

        # Ensure LLM provider is initialized
        await self._ensure_initialized()

        start_time = datetime.now()

        try:
            # Build context
            manager_context = await self._build_manager_context(context, db)

            # Skip tool planning for simple conversational messages
            simple_greetings = ['hi', 'hello', 'hey', 'thanks', 'thank you', 'bye', 'goodbye']
            normalized_message = message.lower().strip()
            is_simple = any(normalized_message == greeting for greeting in simple_greetings)

            logger.info(f"🔍 Message: '{message}' | Normalized: '{normalized_message}' | Is Simple: {is_simple}")

            if is_simple:
                logger.info(f"✅ Using greeting bypass for message: '{message}'")
                # Direct simple response without tool planning
                simple_responses = {
                    'hi': "Hello! I'm your property management AI assistant. How can I help you today?",
                    'hello': "Hello! I'm here to help with your property management needs. What can I do for you?",
                    'hey': "Hey there! Ready to assist with your property management tasks. What do you need?",
                    'thanks': "You're welcome! Let me know if you need anything else.",
                    'thank you': "You're very welcome! I'm here if you need more help.",
                    'bye': "Goodbye! Feel free to reach out anytime you need assistance.",
                    'goodbye': "Take care! I'll be here whenever you need property management support."
                }
                response_text = simple_responses.get(message.lower().strip(), "Hello! How can I help you?")
                return {
                    "response": response_text,
                    "intent": "greeting",
                    "confidence": 100,
                    "tools_used": [],
                    "tool_results": [],
                    "suggestions": []
                }

            # Get enabled tools from context (frontend selection)
            enabled_tools = context.get('enabled_tools', None)

            # Use pattern matching for common queries (faster and more reliable than LLM planning)
            tool_plan = await self._simple_intent_detection(message, manager_context, enabled_tools)

            # Execute MCP tools
            tool_results = []
            if tool_plan.get("tools"):
                logger.info(f"⚙️ Executing {len(tool_plan['tools'])} MCP tools...")
                for tool_call in tool_plan["tools"]:
                    logger.info(f"📞 Calling MCP tool: {tool_call['name']} with args: {tool_call['arguments']}")
                    result = await self.mcp_server.call_tool(
                        tool_name=tool_call["name"],
                        arguments=tool_call["arguments"]
                    )
                    logger.info(f"✅ Tool {tool_call['name']} returned result (length: {len(str(result))})")
                    tool_results.append({
                        "tool": tool_call["name"],
                        "result": result
                    })

            # Generate response incorporating tool results (or simple chat if no tools)
            if tool_results or tool_plan.get("intent") != "general_query":
                logger.info(f"🤖 Generating response with {len(tool_results)} tool results...")
                response = await self._generate_response_with_tools(
                    message=message,
                    context=manager_context,
                    tool_plan=tool_plan,
                    tool_results=tool_results
                )
            else:
                # No tools needed - provide a helpful general response
                response = {
                    "text": "I'm your property management AI assistant. I can help you with:\n\n" +
                           "• Viewing clients, properties, and leases\n" +
                           "• Checking work orders and maintenance tickets\n" +
                           "• Reviewing payments and invoices\n" +
                           "• Finding upcoming lease renewals\n\n" +
                           "Try asking me something like: 'Show me all active leases' or 'Which clients have upcoming renewals?'",
                    "suggestions": [
                        "Show me all clients",
                        "List active leases",
                        "Which clients have upcoming renewals?",
                        "Show open work orders"
                    ]
                }

            return {
                "response": response["text"],
                "intent": tool_plan.get("intent"),
                "confidence": tool_plan.get("confidence"),
                "tools_used": [t["tool"] for t in tool_results],
                "tool_results": tool_results,
                "suggestions": response.get("suggestions", [])
            }

        except ConnectionError as e:
            logger.error(f"LLM connection error: {str(e)}")
            return {
                "response": "🔌 The AI service is currently unavailable. The administrator has been notified. You can still use the manual features in the application.",
                "error": str(e),
                "error_type": "connection_error"
            }
        except ValueError as e:
            logger.error(f"LLM value error: {str(e)}")
            return {
                "response": "⚠️ The AI service encountered a configuration issue. Please check that the AI model is properly loaded.",
                "error": str(e),
                "error_type": "configuration_error"
            }
        except Exception as e:
            logger.error(f"MCP-powered AI error: {str(e)}", exc_info=True)
            return {
                "response": "I encountered an unexpected issue processing your request. Could you rephrase that or try a different question?",
                "error": str(e),
                "error_type": "general_error"
            }

    def _is_tool_enabled(self, tool_name: str, enabled_tools: Optional[List[str]]) -> bool:
        """Check if a tool is enabled (None means all tools are enabled)"""
        if enabled_tools is None:
            return True
        return tool_name in enabled_tools

    async def _simple_intent_detection(
        self,
        message: str,
        context: Dict,
        enabled_tools: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Simple pattern-matching intent detection (faster and more reliable than LLM-based planning)

        Detects common queries and maps them to MCP tool calls without using an LLM.
        Respects the enabled_tools filter from the frontend.
        """
        message_lower = message.lower()

        # Helper to filter tools based on enabled list
        def make_plan(intent: str, confidence: int, tool_name: str, arguments: dict = None):
            if arguments is None:
                arguments = {}
            if self._is_tool_enabled(tool_name, enabled_tools):
                return {
                    "intent": intent,
                    "confidence": confidence,
                    "tools": [{"name": tool_name, "arguments": arguments}]
                }
            else:
                logger.info(f"🚫 Tool '{tool_name}' is disabled by user - skipping")
                return {
                    "intent": intent,
                    "confidence": confidence,
                    "tools": [],
                    "tool_disabled": tool_name
                }

        # Client queries
        if any(keyword in message_lower for keyword in ['client', 'customer', 'tenant']):
            if any(keyword in message_lower for keyword in ['list', 'all', 'show', 'how many', 'count']):
                return make_plan("list_clients", 90, "list_clients")
            if any(keyword in message_lower for keyword in ['renewal', 'expiring', 'upcoming', 'renew']):
                logger.info("🎯 Detected renewal query - calling list_leases with status=expiring")
                return make_plan("upcoming_renewals", 85, "list_leases", {"status": "expiring"})

        # Property queries
        if any(keyword in message_lower for keyword in ['property', 'properties', 'building']):
            if any(keyword in message_lower for keyword in ['list', 'all', 'show']):
                return make_plan("list_properties", 90, "list_properties")

        # Lease queries
        if any(keyword in message_lower for keyword in ['lease', 'contract', 'agreement']):
            if any(keyword in message_lower for keyword in ['active', 'current']):
                return make_plan("active_leases", 90, "list_leases", {"status": "active"})

        # Work order queries
        if any(keyword in message_lower for keyword in ['work order', 'ticket', 'maintenance', 'repair']):
            if any(keyword in message_lower for keyword in ['open', 'pending', 'outstanding']):
                return make_plan("open_work_orders", 90, "list_work_orders", {"status": "open"})

        # Payment queries
        if any(keyword in message_lower for keyword in ['payment', 'invoice', 'bill']):
            if any(keyword in message_lower for keyword in ['overdue', 'late', 'outstanding']):
                return make_plan("overdue_payments", 85, "list_payments", {"status": "overdue"})

        # No pattern matched - return empty plan (will use general chat response)
        logger.info(f"No pattern matched for message: '{message}' - using general chat")
        return {
            "intent": "general_query",
            "confidence": 50,
            "tools": []
        }

    async def _plan_tool_execution(
        self,
        message: str,
        context: Dict
    ) -> Dict[str, Any]:
        """
        Analyze the message and determine which MCP tools to execute

        This is the "agent reasoning" step where the AI decides:
        - What is the user asking for?
        - Which tools are needed?
        - What parameters should be passed?

        For Claude/OpenAI: Uses native tool calling
        For Ollama: Uses prompt engineering for tool selection
        """

        # Get list of available tools
        available_tools = self.mcp_server.get_tools_manifest()

        # Check if provider supports native tool calling
        supports_native_tools = self.config.provider in ["anthropic", "openai"]

        if supports_native_tools:
            # Use native tool calling (Claude/OpenAI)
            return await self._plan_with_native_tools(message, context, available_tools)
        else:
            # Use prompt engineering (Ollama)
            return await self._plan_with_prompt_engineering(message, context, available_tools)

    async def _plan_with_native_tools(
        self,
        message: str,
        context: Dict,
        available_tools: List[Dict]
    ) -> Dict[str, Any]:
        """Plan tool execution using native tool calling (Claude/OpenAI)"""

        system_message = f"""
You are a property management AI assistant with access to tools.
Analyze the user's message and determine which tools to use.

Current context:
{json.dumps(context, indent=2)}

Guidelines:
- Use tools to get accurate, real-time data
- Be efficient - don't call unnecessary tools
- Chain tools logically when needed
"""

        messages = [
            LLMMessage(role="system", content=system_message),
            LLMMessage(role="user", content=message)
        ]

        try:
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                tools=available_tools
            )

            # If Claude/OpenAI returned tool calls, use them
            if response.tool_calls:
                return {
                    "intent": "tool_execution",
                    "confidence": 0.95,
                    "reasoning": "Using native tool calling",
                    "tools": response.tool_calls
                }
            else:
                # No tools needed, just respond
                return {
                    "intent": "general_response",
                    "confidence": 0.9,
                    "reasoning": response.content,
                    "tools": []
                }

        except Exception as e:
            logger.error(f"Native tool planning error: {e}")
            return {"intent": "error", "confidence": 0.5, "tools": []}

    async def _plan_with_prompt_engineering(
        self,
        message: str,
        context: Dict,
        available_tools: List[Dict]
    ) -> Dict[str, Any]:
        """Plan tool execution using prompt engineering (Ollama)"""

        # Simplified tool descriptions for Ollama
        tool_descriptions = "\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in available_tools[:20]  # Limit to prevent context overflow
        ])

        system_message = f"""
You are a property management AI assistant with access to tools.
Analyze the user's message and determine which tools to use.

Available tools:
{tool_descriptions}

Current context:
{json.dumps(context, indent=2)}

Respond with valid JSON:
{{
    "intent": "the user's intent",
    "confidence": 0.95,
    "reasoning": "why these tools are needed",
    "tools": [
        {{
            "name": "list_properties",
            "arguments": {{"property_type": "residential"}}
        }}
    ]
}}

If no tools are needed, return empty tools array.
"""

        messages = [
            LLMMessage(role="system", content=system_message),
            LLMMessage(role="user", content=f"User message: {message}\n\nDetermine which tools to use:")
        ]

        try:
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=0.3,  # Lower temperature for structured output
                max_tokens=1000
            )

            # Extract JSON from response
            content = response.content
            if '{' in content:
                json_start = content.index('{')
                json_end = content.rindex('}') + 1
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                logger.warning(f"No JSON in tool planning response: {content}")
                return {"intent": "query", "confidence": 0.5, "tools": []}

        except Exception as e:
            logger.error(f"Prompt engineering tool planning error: {e}")
            return {"intent": "query", "confidence": 0.5, "tools": []}

    async def _generate_response_with_tools(
        self,
        message: str,
        context: Dict,
        tool_plan: Dict,
        tool_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate natural language response incorporating tool execution results
        """

        system_message = f"""
You are Somni, an AI assistant for property managers.
You just executed some tools to answer the user's question.

Original question: {message}

Tool results:
{json.dumps(tool_results, indent=2)}

Context:
{json.dumps(context, indent=2)}

Generate a natural language response that:
1. Directly answers the user's question
2. Incorporates the tool results
3. Provides specific data points
4. Suggests next steps

Be concise, professional, and actionable.
"""

        messages = [
            LLMMessage(role="system", content=system_message),
            LLMMessage(role="user", content="Generate response:")
        ]

        try:
            response = await self.llm.chat_completion(
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )

            suggestions = self._generate_suggestions_from_results(tool_plan, tool_results)

            return {
                "text": response.content,
                "suggestions": suggestions
            }

        except Exception as e:
            logger.error(f"Response generation error: {e}")
            # Fallback: use template-based formatting for common queries
            formatted_response = self._format_tool_results_fallback(
                message=message,
                tool_plan=tool_plan,
                tool_results=tool_results
            )
            return formatted_response

    async def _build_manager_context(
        self,
        page_context: Dict,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Build comprehensive context for property management tasks
        """
        context = {
            "page": page_context.get("page", "unknown"),
            "user_type": page_context.get("user_type", "manager"),
            "current_date": datetime.now().isoformat()
        }

        # Note: Simplified version - full implementation would query database
        # for property, client, tenant context as in property_manager_ai.py

        return context

    async def close(self):
        """Close LLM provider connection"""
        await self.llm.close()

    def _generate_suggestions_from_results(
        self,
        tool_plan: Dict,
        tool_results: List[Dict]
    ) -> List[str]:
        """
        Generate contextual suggestions based on tool results
        """
        intent = tool_plan.get("intent", "")
        tools_used = [t["tool"] for t in tool_results]

        # Contextual suggestions based on what was just queried
        if "list_properties" in tools_used:
            return ["Show property details", "Compare performance", "View vacant units"]
        elif "list_work_orders" in tools_used:
            return ["Create new work order", "Assign contractor", "View high priority"]
        elif "list_tenants" in tools_used:
            return ["View lease details", "Check payment history", "Send communication"]
        elif "create_work_order" in tools_used:
            return ["Assign contractor", "Set priority", "View all work orders"]
        elif "list_smart_devices" in tools_used:
            return ["Control device", "Run diagnostics", "View device history"]
        else:
            return ["Show more", "Export data", "Ask another question"]

    def _format_tool_results_fallback(
        self,
        message: str,
        tool_plan: Dict,
        tool_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        Template-based formatting for common queries when LLM is unavailable
        Creates human-friendly responses without requiring an LLM
        """
        if not tool_results:
            return {
                "text": "I couldn't find any data for that query. Could you try rephrasing your question?",
                "suggestions": self._generate_suggestions_from_results(tool_plan, tool_results)
            }

        intent = tool_plan.get("intent", "")
        tool_name = tool_results[0]["tool"] if tool_results else ""
        result_data = tool_results[0]["result"] if tool_results else {}

        # Extract count from result
        total = 0
        items = []
        if isinstance(result_data, dict):
            total = result_data.get("total", 0)
            items = result_data.get("items", [])

        # Format based on intent/tool
        response_text = ""

        if "list_clients" in intent or tool_name == "list_clients":
            if total == 0:
                response_text = "You currently don't have any clients in the system. Would you like to add your first client?"
            elif total == 1:
                client = items[0] if items else {}
                name = client.get("name", "Unknown")
                response_text = f"You have **1 client**: {name}."
            else:
                response_text = f"You have **{total} clients** in your system."
                if items:
                    # Show first few clients
                    client_names = [item.get("name", "Unknown") for item in items[:3]]
                    response_text += f"\n\nRecent clients: {', '.join(client_names)}"
                    if total > 3:
                        response_text += f", and {total - 3} more."

        elif "renewal" in intent or "expiring" in intent:
            if total == 0:
                response_text = "Great news! No lease renewals are coming up soon."
            elif total == 1:
                response_text = f"You have **1 lease** coming up for renewal soon."
            else:
                response_text = f"You have **{total} leases** coming up for renewal soon."

            if items:
                response_text += "\n\nUpcoming renewals:"
                for item in items[:5]:
                    tenant = item.get("tenant_name", "Unknown")
                    unit = item.get("unit_number", "N/A")
                    end_date = item.get("end_date", "")
                    response_text += f"\n• Unit {unit} - {tenant} (expires {end_date})"

        elif "list_properties" in intent or tool_name == "list_properties":
            if total == 0:
                response_text = "No properties found. Would you like to add a property to get started?"
            else:
                response_text = f"You have **{total} properties** in your portfolio."

        elif "list_leases" in intent or tool_name == "list_leases":
            status = "active" if "active" in message.lower() else ""
            if total == 0:
                response_text = f"No {status} leases found."
            else:
                response_text = f"You have **{total} {status} leases**."

        elif "work_order" in intent or tool_name == "list_work_orders":
            status = "open" if "open" in message.lower() else ""
            if total == 0:
                response_text = f"Good news! No {status} work orders at the moment."
            else:
                response_text = f"You have **{total} {status} work orders** that need attention."

        else:
            # Generic fallback
            if total == 0:
                response_text = "I didn't find any matching records for that query."
            else:
                response_text = f"I found **{total} results** for your query."

        return {
            "text": response_text,
            "suggestions": self._generate_suggestions_from_results(tool_plan, tool_results)
        }

    # ===================================================================
    # SPECIALIZED ACTION METHODS
    # ===================================================================

    async def execute_action(
        self,
        action_type: str,
        action_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a specific action via MCP tools

        This allows programmatic execution of actions without full NL processing
        """
        action_map = {
            "create_work_order": "create_work_order",
            "create_lease": "create_lease",
            "send_invoice": "create_invoice",
            "control_device": "control_device",
            "sync_edge_node": "sync_components_to_edge_node",
        }

        tool_name = action_map.get(action_type)
        if not tool_name:
            return {"error": f"Unknown action type: {action_type}"}

        try:
            result = await self.mcp_server.call_tool(tool_name, action_data)
            return {
                "success": True,
                "action": action_type,
                "result": result
            }
        except Exception as e:
            logger.error(f"Action execution error: {action_type} - {str(e)}")
            return {
                "success": False,
                "action": action_type,
                "error": str(e)
            }


# Create instance based on environment configuration
# Uses lazy initialization with automatic fallback cascade
_config = LLMConfig.from_env()
mcp_powered_ai = MCPPoweredAI(config=_config)

logger.info(
    f"MCP-Powered AI ready with provider preference: {_config.provider}"
    f"{' (will use auto-fallback)' if _config.provider == 'auto' else ''}"
)
