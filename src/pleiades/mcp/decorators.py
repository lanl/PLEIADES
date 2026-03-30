"""MCP tool decorator for PLEIADES.

This module provides a decorator to register functions as MCP tools.
It creates a thin abstraction layer that decouples PLEIADES from
specific MCP implementations (like FastMCP).

Architecture:
    - The decorator registers functions in a global registry at import time
    - The registry is read-only from external code (get_registered_tools returns a deep copy)
    - The MCP server (pleiades.mcp.server) reads the registry and exposes tools
    - This separation allows switching MCP backends without changing decorated functions

Thread Safety:
    - Dictionary operations are atomic (protected by GIL in CPython)
    - get_registered_tools() returns a deep copy, so mutations don't affect registry
    - Note: Duplicate name detection between concurrent registrations is not atomic

Performance:
    - get_registered_tools() performs a deep copy of the entire registry
    - Performance scales linearly with the number of registered tools
    - For ~1000 tools: ~2-3ms per call; for ~10000 tools: ~20-30ms per call
    - Consider caching the result if called frequently in hot paths

Decorator Ordering:
    - When combining with @classmethod or @staticmethod, @mcp_tool must come LAST
    - Correct: @classmethod @mcp_tool() - the function is registered
    - Wrong: @mcp_tool() @classmethod - raises TypeError (descriptor not callable)

Limitations:
    - Instance methods can be registered but cannot be called from the registry
      without an instance (missing self argument)
    - Lambda functions are registered with name '<lambda>' which may cause conflicts

Example:
    from pleiades.mcp.decorators import mcp_tool, get_registered_tools

    @mcp_tool(description="Validate a dataset")
    def validate_dataset(path: str) -> dict:
        return {"valid": True}

    tools = get_registered_tools()
    assert "validate_dataset" in tools
"""

from __future__ import annotations

import copy
import re
from typing import Any, Callable, TypeVar, overload

# Valid tool name pattern: alphanumeric, underscore, hyphen only
_VALID_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

__all__ = ["mcp_tool", "get_registered_tools", "clear_registry"]

# Global registry for MCP tools
_mcp_registry: dict[str, dict[str, Any]] = {}

# Type variable for decorated function
F = TypeVar("F", bound=Callable[..., Any])


@overload
def mcp_tool(func: F) -> F:
    """Decorator without parentheses - registers function with defaults."""
    ...


@overload
def mcp_tool(
    func: None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    parameter_descriptions: dict[str, str] | None = None,
) -> Callable[[F], F]:
    """Decorator with parentheses."""
    ...


def mcp_tool(
    func: F | None = None,
    *,
    name: str | None = None,
    description: str | None = None,
    parameter_descriptions: dict[str, str] | None = None,
) -> F | Callable[[F], F]:
    """Decorator to register a function as an MCP tool.

    This decorator registers the function in a global registry that can
    be discovered by the MCP server. The function itself is not modified
    and can still be called directly.

    Args:
        func: The function to decorate (when used without parentheses).
        name: Custom name for the tool. Defaults to function.__name__.
        description: Custom description. Defaults to function docstring.
        parameter_descriptions: Dict mapping parameter names to descriptions.

    Returns:
        The decorated function, unchanged.

    Raises:
        ValueError: If a tool with the same name is already registered.
        TypeError: If arguments have incorrect types or decorator is misused.

    Example:
        @mcp_tool()
        def add(a: int, b: int) -> int:
            '''Add two numbers.'''
            return a + b

        @mcp_tool(name="custom_name", description="Custom description")
        def another_tool():
            pass
    """
    # Handle @mcp_tool without parentheses
    if func is not None:
        # Called as @mcp_tool (without parens) - func is the decorated function
        if callable(func):
            return _register_tool(func, None, None, None)
        else:
            raise TypeError(f"mcp_tool() argument must be callable or None, not {type(func).__name__}")

    # Validate inputs
    if name is not None:
        if not isinstance(name, str):
            raise TypeError(f"name must be str or None, not {type(name).__name__}")
        if not name.strip():
            raise ValueError("name cannot be empty or whitespace")
        if not _VALID_NAME_PATTERN.match(name):
            raise ValueError(
                f"name contains invalid characters: '{name}'. "
                "Tool names must be alphanumeric with underscores or hyphens only."
            )

    if description is not None and not isinstance(description, str):
        raise TypeError(f"description must be str or None, not {type(description).__name__}")

    if parameter_descriptions is not None:
        if not isinstance(parameter_descriptions, dict):
            raise TypeError(f"parameter_descriptions must be dict or None, not {type(parameter_descriptions).__name__}")
        # Validate dict contents
        for key, value in parameter_descriptions.items():
            if not isinstance(key, str):
                raise TypeError(f"parameter_descriptions keys must be str, not {type(key).__name__}")
            if not key.strip():
                raise ValueError("parameter_descriptions keys cannot be empty or whitespace")
            if not isinstance(value, str):
                raise TypeError(f"parameter_descriptions values must be str, not {type(value).__name__}")

    # Return decorator that will register the function
    def decorator(fn: F) -> F:
        return _register_tool(fn, name, description, parameter_descriptions)

    return decorator


def _register_tool(
    func: F,
    name: str | None,
    description: str | None,
    parameter_descriptions: dict[str, str] | None,
) -> F:
    """Internal function to register a tool in the registry.

    Args:
        func: The function to register.
        name: Custom tool name or None to use func.__name__.
        description: Custom description or None to use docstring.
        parameter_descriptions: Parameter descriptions dict or None.

    Returns:
        The original function, unchanged.

    Raises:
        ValueError: If tool name is already registered.
        TypeError: If func is not callable.
    """
    if not callable(func):
        raise TypeError(f"Decorated object must be callable, not {type(func).__name__}")

    # Determine tool name
    tool_name = name if name is not None else func.__name__

    # Check for duplicate registration
    if tool_name in _mcp_registry:
        raise ValueError(f"Tool '{tool_name}' is already registered. Use a different name or remove the duplicate.")

    # Extract description from docstring if not provided
    tool_description: str
    if description is not None:
        tool_description = description
    elif func.__doc__:
        tool_description = func.__doc__
    else:
        tool_description = ""

    # Register the tool (store original function directly, no wrapper)
    _mcp_registry[tool_name] = {
        "name": tool_name,
        "description": tool_description,
        "func": func,
        "parameter_descriptions": parameter_descriptions,
    }

    # Return original function unchanged (no wrapper overhead)
    return func


def get_registered_tools() -> dict[str, dict[str, Any]]:
    """Get all registered MCP tools.

    Returns a deep copy of the registry to prevent external mutation
    of internal state.

    Note:
        This function performs a deep copy of the entire registry, which
        has O(n) time complexity. For ~1000 tools this takes ~2-3ms.
        Consider caching the result if called frequently.

    Returns:
        Dict mapping tool names to their metadata. Each entry contains:
        - name: The tool name
        - description: The tool description
        - func: Reference to the callable function
        - parameter_descriptions: Optional dict of parameter descriptions

    Example:
        tools = get_registered_tools()
        for name, info in tools.items():
            print(f"{name}: {info['description']}")
    """
    return copy.deepcopy(_mcp_registry)


def clear_registry() -> None:
    """Clear all registered tools from the registry.

    WARNING: This removes ALL registered tools, including those from
    other modules. Use with caution in production code.

    This is primarily useful for testing to ensure a clean state
    between test cases.

    Example:
        clear_registry()
        assert len(get_registered_tools()) == 0
    """
    _mcp_registry.clear()
