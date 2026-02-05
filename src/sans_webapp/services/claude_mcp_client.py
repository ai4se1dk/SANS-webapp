"""
Claude MCP Client for SANS-webapp AI Assistant.

Provides Anthropic Claude integration with MCP tool-use capability.
Handles tool invocation round-trips between Claude and the embedded MCP server.
"""

import json
import os
from typing import Any

from anthropic import Anthropic

from sans_webapp.mcp_server import mcp


# Tool name to function mapping - built from MCP server
_tool_handlers: dict[str, callable] = {}


def _build_tool_handlers() -> dict[str, callable]:
    """Build mapping from tool names to handler functions."""
    global _tool_handlers
    if _tool_handlers:
        return _tool_handlers

    # Import the tool functions from mcp_server
    from sans_webapp.mcp_server import (
        enable_polydispersity,
        get_current_state,
        get_fit_results,
        get_model_parameters,
        list_sans_models,
        remove_structure_factor,
        run_fit,
        set_model,
        set_multiple_parameters,
        set_parameter,
        set_structure_factor,
    )

    _tool_handlers = {
        "list-sans-models": list_sans_models,
        "get-model-parameters": get_model_parameters,
        "get-current-state": get_current_state,
        "get-fit-results": get_fit_results,
        "set-model": set_model,
        "set-parameter": set_parameter,
        "set-multiple-parameters": set_multiple_parameters,
        "enable-polydispersity": enable_polydispersity,
        "set-structure-factor": set_structure_factor,
        "remove-structure-factor": remove_structure_factor,
        "run-fit": run_fit,
    }
    return _tool_handlers


def get_mcp_tool_schemas() -> list[dict[str, Any]]:
    """
    Extract tool schemas from the MCP server for Claude's tool-use API.

    Returns:
        List of tool definitions in Anthropic's tool schema format.
    """
    tools = [
        {
            "name": "list-sans-models",
            "description": "List all available SANS models from sasmodels library. Returns a formatted list of model names that can be used with set-model.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get-model-parameters",
            "description": "Get parameter details for a specific SANS model. Shows parameter names, default values, units, and descriptions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Name of the model (e.g., 'sphere', 'cylinder')",
                    }
                },
                "required": ["model_name"],
            },
        },
        {
            "name": "get-current-state",
            "description": "Get the current state of the SANS fitter. Shows loaded data info, current model, and parameter values.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "get-fit-results",
            "description": "Get the results from the most recent fit. Shows optimized parameter values, uncertainties, and fit statistics.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "set-model",
            "description": "Load a SANS model for fitting.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "model_name": {
                        "type": "string",
                        "description": "Name of the model to load (e.g., 'sphere', 'cylinder', 'ellipsoid')",
                    }
                },
                "required": ["model_name"],
            },
        },
        {
            "name": "set-parameter",
            "description": "Set a parameter's value and/or fitting options.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Parameter name (e.g., 'radius', 'sld')",
                    },
                    "value": {
                        "type": "number",
                        "description": "New value for the parameter (optional)",
                    },
                    "min_bound": {
                        "type": "number",
                        "description": "Minimum bound for fitting (optional)",
                    },
                    "max_bound": {
                        "type": "number",
                        "description": "Maximum bound for fitting (optional)",
                    },
                    "vary": {
                        "type": "boolean",
                        "description": "Whether parameter should vary during fitting (optional)",
                    },
                },
                "required": ["name"],
            },
        },
        {
            "name": "set-multiple-parameters",
            "description": "Set multiple parameters at once.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "parameters": {
                        "type": "object",
                        "description": "Dictionary mapping parameter names to their settings. Each value is a dict with optional keys: 'value', 'min', 'max', 'vary'. Example: {\"radius\": {\"value\": 50, \"vary\": true}}",
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "number"},
                                "min": {"type": "number"},
                                "max": {"type": "number"},
                                "vary": {"type": "boolean"},
                            },
                        },
                    }
                },
                "required": ["parameters"],
            },
        },
        {
            "name": "enable-polydispersity",
            "description": "Enable polydispersity for a size parameter.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "parameter_name": {
                        "type": "string",
                        "description": "Name of the parameter to make polydisperse (e.g., 'radius')",
                    },
                    "pd_type": {
                        "type": "string",
                        "description": "Distribution type ('gaussian', 'lognormal', 'schulz')",
                        "default": "gaussian",
                    },
                    "pd_value": {
                        "type": "number",
                        "description": "Width of the distribution (relative, typically 0.01-0.5)",
                        "default": 0.1,
                    },
                },
                "required": ["parameter_name"],
            },
        },
        {
            "name": "set-structure-factor",
            "description": "Add a structure factor to account for interparticle interactions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "sf_name": {
                        "type": "string",
                        "description": "Structure factor name (e.g., 'hardsphere', 'stickyhardsphere', 'squarewell')",
                    }
                },
                "required": ["sf_name"],
            },
        },
        {
            "name": "remove-structure-factor",
            "description": "Remove any structure factor from the current model.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "run-fit",
            "description": "Run the curve fitting optimization. Uses the currently loaded model and parameter settings to fit the data. Returns fit quality metrics and optimized parameter values.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    ]
    return tools


def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """
    Execute an MCP tool by name with the given input.

    Args:
        tool_name: Name of the tool to execute
        tool_input: Dictionary of input parameters

    Returns:
        Tool execution result as a string
    """
    handlers = _build_tool_handlers()

    if tool_name not in handlers:
        return f"Unknown tool: {tool_name}"

    handler = handlers[tool_name]

    try:
        # Call the handler with the input parameters
        result = handler(**tool_input)
        return result
    except TypeError as e:
        # Handle parameter mismatch
        return f"Tool parameter error: {str(e)}"
    except Exception as e:
        return f"Tool execution error: {str(e)}"


class ClaudeMCPClient:
    """
    Claude client with MCP tool-use capability for SANS fitting.

    Handles the conversation loop including tool invocations.
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize the Claude MCP client.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY or pass api_key parameter."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"
        self.tools = get_mcp_tool_schemas()

        # System prompt for SANS fitting context
        self.system_prompt = """You are a SANS (Small-Angle Neutron Scattering) data analysis assistant integrated into a web application for curve fitting.

You have access to tools that can:
- List and inspect available scattering models (sphere, cylinder, ellipsoid, etc.)
- Load models and configure their parameters
- Run curve fitting optimization
- Enable advanced features like polydispersity and structure factors

When helping users:
1. First understand their sample and experimental setup
2. Suggest appropriate models based on the sample description
3. Guide parameter setup with physically reasonable initial values
4. Run fits and interpret results
5. Suggest refinements if fit quality is poor

Always explain your actions clearly. Use the tools to perform actions rather than just describing what could be done.

The application shows plots and parameter tables that update when you use tools - the user can see changes immediately."""

    def chat(
        self,
        user_message: str,
        conversation_history: list[dict[str, str]] | None = None,
        context: str | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        """
        Send a message to Claude and handle any tool invocations.

        Args:
            user_message: The user's message
            conversation_history: Previous messages in the conversation
            context: Additional context about current fitter state

        Returns:
            Tuple of (assistant_response, tool_invocations)
            where tool_invocations is a list of {tool_name, input, result} dicts
        """
        # Build messages list
        messages = []

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        # Add context to user message if provided
        full_user_message = user_message
        if context:
            full_user_message = f"[Current State]\n{context}\n\n[User Message]\n{user_message}"

        messages.append({
            "role": "user",
            "content": full_user_message,
        })

        tool_invocations = []

        # Conversation loop - handle tool use
        while True:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.system_prompt,
                tools=self.tools,
                messages=messages,
            )

            # Check if we need to handle tool use
            if response.stop_reason == "tool_use":
                # Process each tool use block
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id

                        # Execute the tool
                        result = execute_tool(tool_name, tool_input)

                        tool_invocations.append({
                            "tool_name": tool_name,
                            "input": tool_input,
                            "result": result,
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result,
                        })

                # Add assistant's response (with tool use) to messages
                messages.append({
                    "role": "assistant",
                    "content": response.content,
                })

                # Add tool results
                messages.append({
                    "role": "user",
                    "content": tool_results,
                })

            else:
                # No more tool use, extract final text response
                final_response = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_response += block.text

                return final_response, tool_invocations

    def simple_chat(self, user_message: str, context: str | None = None) -> str:
        """
        Simple chat interface that returns just the response text.

        Args:
            user_message: The user's message
            context: Additional context about current fitter state

        Returns:
            The assistant's response text
        """
        response, _ = self.chat(user_message, context=context)
        return response


# Singleton client instance
_client: ClaudeMCPClient | None = None


def get_claude_client(api_key: str | None = None) -> ClaudeMCPClient:
    """
    Get or create the Claude MCP client singleton.

    Args:
        api_key: Anthropic API key (only used on first call)

    Returns:
        ClaudeMCPClient instance
    """
    global _client
    if _client is None:
        _client = ClaudeMCPClient(api_key=api_key)
    return _client


def reset_client() -> None:
    """Reset the client singleton (e.g., when API key changes)."""
    global _client
    _client = None
