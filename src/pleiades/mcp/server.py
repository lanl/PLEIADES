"""PLEIADES MCP Server implementation.

This module provides the FastMCP server that exposes PLEIADES workflow functions
as MCP tools for AI-assisted neutron resonance analysis.

The server auto-discovers tools registered with @mcp_tool decorator and exposes
them via the MCP protocol.

Usage:
    pleiades-mcp            # Console script
    python -m pleiades.mcp  # Module invocation

Functions:
    discover_tools(): Read registered tools from decorator registry
    register_tools(server): Register discovered tools with FastMCP server
    generate_tool_schema(func): Generate JSON schema from function signature
    get_server(): Get the FastMCP server instance
    main(): Start the MCP server
"""

from __future__ import annotations

import inspect
import types
from collections.abc import Callable
from typing import Any, Union, get_args, get_origin

from pleiades.mcp import MCP_AVAILABLE, check_mcp_available
from pleiades.mcp.decorators import get_registered_tools
from pleiades.utils.logger import loguru_logger

# Module-level logger with context binding (follows codebase convention)
logger = loguru_logger.bind(name=__name__)

# NoneType constant for efficient type comparisons in union handling
NoneType: type = type(None)

# Server instance created at module load for decorator support
_server: Any = None

if MCP_AVAILABLE:
    from fastmcp import FastMCP

    _server = FastMCP("pleiades-mcp")


# Type mapping from Python types to JSON schema types
_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    NoneType: "null",
}


def discover_tools() -> dict[str, dict[str, Any]]:
    """Discover all tools registered with @mcp_tool decorator.

    Reads from the decorator registry and returns tool metadata.
    The returned dict is a deep copy (from get_registered_tools) to
    prevent external mutation of the registry.

    Returns:
        Dict mapping tool names to their metadata. Each entry contains:
        - name: The tool name
        - description: The tool description
        - func: Reference to the callable function
        - parameter_descriptions: Optional dict of parameter descriptions

    Example:
        tools = discover_tools()
        for name, info in tools.items():
            print(f"Tool: {name} - {info['description']}")
            # Call the discovered function
            result = info['func'](*args, **kwargs)
    """
    return get_registered_tools()


def generate_tool_schema(
    func: Callable[..., Any],
    parameter_descriptions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Generate JSON schema from function signature and type hints.

    Inspects the function's parameters and type annotations to create
    a JSON schema suitable for MCP tool registration.

    If the function is registered with @mcp_tool decorator and has parameter
    descriptions, those will be included automatically (unless overridden by
    the parameter_descriptions argument).

    Args:
        func: The function to generate schema for.
        parameter_descriptions: Optional dict mapping parameter names to descriptions.
            If not provided, will look up from decorator registry.

    Returns:
        Dict containing JSON schema with 'properties' and 'required' fields.

    Example:
        def add(a: int, b: int) -> int:
            return a + b

        schema = generate_tool_schema(add)
        # {'properties': {'a': {'type': 'integer'}, 'b': {'type': 'integer'}},
        #  'required': ['a', 'b']}
    """
    sig = inspect.signature(func)
    annotations = getattr(func, "__annotations__", {})

    # If parameter_descriptions not provided, try to get from registry.
    # Note: This performs a linear search O(n) through all registered tools.
    # For large numbers of tools (>1000), consider passing parameter_descriptions
    # explicitly for better performance.
    param_descs = parameter_descriptions
    if param_descs is None:
        tools = get_registered_tools()
        for tool_info in tools.values():
            if tool_info.get("func") is func:
                param_descs = tool_info.get("parameter_descriptions")
                break
    param_descs = param_descs or {}

    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        # Skip *args and **kwargs
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue

        # Get type annotation
        param_type = annotations.get(param_name)
        json_type = _python_type_to_json_type(param_type)

        # Build property schema
        prop_schema: dict[str, Any] = {"type": json_type}

        # Add description if available
        if param_name in param_descs:
            prop_schema["description"] = param_descs[param_name]

        properties[param_name] = prop_schema

        # Mark as required if no default value
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "properties": properties,
        "required": required,
    }


def _python_type_to_json_type(python_type: type | None) -> str:
    """Convert Python type annotation to JSON schema type.

    Args:
        python_type: Python type annotation or None.

    Returns:
        JSON schema type string (e.g., 'string', 'integer', 'array').

    Note:
        Unrecognized types default to 'string' with a debug log message.
    """
    if python_type is None:
        return "string"  # Default for untyped parameters

    # Handle direct type matches
    if python_type in _TYPE_MAP:
        return _TYPE_MAP[python_type]

    # Handle generic types (list[str], dict[str, int], Optional[int], etc.)
    origin = get_origin(python_type)

    if origin is not None:
        # Handle Union types (including Optional which is Union[T, None])
        # Also handle Python 3.10+ union syntax (X | Y) via types.UnionType
        is_union = origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)
        if is_union:
            args = get_args(python_type)
            # Filter out NoneType for Optional
            non_none_args = [a for a in args if a is not NoneType]
            if non_none_args:
                # Return type of first non-None arg
                return _python_type_to_json_type(non_none_args[0])
            # Defensive fallback: typing module normalizes Union[None] to NoneType,
            # which is caught by direct type match, so this is theoretically unreachable
            return "string"

        # Handle list, dict, etc.
        if origin in _TYPE_MAP:
            return _TYPE_MAP[origin]

        # Handle typing.List, typing.Dict (older style)
        origin_name = getattr(origin, "__name__", str(origin))
        if origin_name.lower() == "list":
            return "array"
        if origin_name.lower() == "dict":
            return "object"

    # Handle Any type
    type_name = getattr(python_type, "__name__", str(python_type))
    if type_name == "Any":
        return "string"

    # Fallback: try to match by name
    if hasattr(python_type, "__name__"):
        name = python_type.__name__.lower()
        if name in ("list", "tuple", "set", "frozenset"):
            return "array"
        if name in ("dict", "mapping"):
            return "object"

    # Log unrecognized type and fall back to string
    logger.debug(f"Unrecognized type '{python_type}' defaulting to 'string' in JSON schema")
    return "string"


def register_tools(server: Any) -> None:
    """Register all discovered tools with the FastMCP server.

    Reads tools from the decorator registry and registers each one
    with the provided FastMCP server instance. Continues registering
    remaining tools even if one fails.

    Args:
        server: FastMCP server instance to register tools with.

    Example:
        from fastmcp import FastMCP
        server = FastMCP("my-server")
        register_tools(server)
    """
    tools = discover_tools()

    if not tools:
        logger.debug("No tools found in registry")
        return

    for tool_name, tool_info in tools.items():
        func = tool_info["func"]
        description = tool_info.get("description", "")

        try:
            # Register with FastMCP using its decorator
            server.tool(name=tool_name, description=description)(func)
            logger.debug(f"Registered tool: {tool_name}")
        except (TypeError, ValueError, AttributeError, RuntimeError) as e:
            logger.warning(f"Failed to register tool '{tool_name}': {e}")
            # Continue registering other tools


def get_server() -> Any:
    """Get the MCP server instance.

    Returns:
        The FastMCP server instance.

    Raises:
        ImportError: If MCP dependencies are not installed.
    """
    check_mcp_available()
    # After check_mcp_available() passes, _server is guaranteed to be initialized
    return _server


def main() -> None:
    """Start the PLEIADES MCP server.

    Discovers and registers all @mcp_tool decorated functions,
    then starts the server.

    Raises:
        ImportError: If MCP dependencies are not installed.
    """
    # Import tools module to trigger @mcp_tool decorator registration
    import pleiades.mcp.tools  # noqa: F401

    server = get_server()

    # Register all discovered tools
    register_tools(server)

    logger.info("Starting PLEIADES MCP server...")
    server.run()


__all__ = [
    "discover_tools",
    "generate_tool_schema",
    "get_server",
    "main",
    "register_tools",
]
