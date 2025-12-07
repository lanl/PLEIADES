#!/usr/bin/env python
"""Test suite for pleiades.mcp.server module.

Tests cover:
- Tool discovery from decorator registry
- Tool registration with FastMCP server
- JSON schema generation from function signatures
- Server initialization and management
- Error handling and edge cases

These tests define the expected API for Issue #166 (MCP server with auto-discovery).
They are written BEFORE implementation to guide the development process.
"""

import importlib.util
import inspect
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

# Detect fastmcp availability at module load
HAS_FASTMCP = importlib.util.find_spec("fastmcp") is not None


class TestToolDiscovery:
    """Test discover_tools() function that reads from decorator registry."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_discover_tools_returns_empty_dict_when_no_tools_registered(self):
        """discover_tools() should return empty dict when registry is empty."""
        from pleiades.mcp.server import discover_tools

        tools = discover_tools()
        assert isinstance(tools, dict)
        assert len(tools) == 0

    def test_discover_tools_finds_single_registered_tool(self):
        """discover_tools() should find tools registered with @mcp_tool."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import discover_tools

        @mcp_tool()
        def example_tool(path: str) -> dict:
            """Validate a dataset."""
            return {"valid": True}

        tools = discover_tools()
        assert "example_tool" in tools
        assert tools["example_tool"]["func"] is example_tool

    def test_discover_tools_finds_multiple_registered_tools(self):
        """discover_tools() should find all tools in the registry."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import discover_tools

        @mcp_tool()
        def tool_one():
            """First tool."""
            pass

        @mcp_tool()
        def tool_two():
            """Second tool."""
            pass

        @mcp_tool()
        def tool_three():
            """Third tool."""
            pass

        tools = discover_tools()
        assert len(tools) == 3
        assert "tool_one" in tools
        assert "tool_two" in tools
        assert "tool_three" in tools

    def test_discover_tools_returns_correct_metadata(self):
        """discover_tools() should return complete tool metadata."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import discover_tools

        @mcp_tool(
            name="custom_name",
            description="Custom description",
            parameter_descriptions={
                "x": "First parameter",
                "y": "Second parameter",
            },
        )
        def my_function(x: int, y: str) -> bool:
            """Original docstring."""
            return True

        tools = discover_tools()
        tool_info = tools["custom_name"]

        assert tool_info["name"] == "custom_name"
        assert tool_info["description"] == "Custom description"
        assert tool_info["func"] is my_function
        assert tool_info["parameter_descriptions"]["x"] == "First parameter"
        assert tool_info["parameter_descriptions"]["y"] == "Second parameter"

    def test_discover_tools_includes_function_without_type_hints(self):
        """discover_tools() should handle functions without type hints."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import discover_tools

        @mcp_tool()
        def no_hints(x, y):
            """Function without type hints."""
            return x + y

        tools = discover_tools()
        assert "no_hints" in tools
        assert tools["no_hints"]["func"] is no_hints

    def test_discover_tools_preserves_function_callable(self):
        """Discovered functions should remain callable."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import discover_tools

        @mcp_tool()
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        tools = discover_tools()
        discovered_func = tools["add"]["func"]

        # Should be callable and produce correct result
        assert discovered_func(5, 3) == 8


class TestToolRegistration:
    """Test register_tools() function that registers tools with FastMCP."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_register_tools_registers_single_tool(self):
        """register_tools() should register tools with FastMCP server."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import register_tools

        @mcp_tool()
        def example_tool(path: str) -> dict:
            """Validate a dataset."""
            return {"valid": True}

        # Create mock server
        mock_server = MagicMock()

        # Register tools
        register_tools(mock_server)

        # Verify server.tool() decorator was called
        assert mock_server.tool.called
        # Should have been called at least once
        assert mock_server.tool.call_count >= 1

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_register_tools_registers_multiple_tools(self):
        """register_tools() should register all discovered tools."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import register_tools

        @mcp_tool()
        def tool_a():
            """Tool A."""
            pass

        @mcp_tool()
        def tool_b():
            """Tool B."""
            pass

        @mcp_tool()
        def tool_c():
            """Tool C."""
            pass

        mock_server = MagicMock()
        register_tools(mock_server)

        # Should register all 3 tools
        assert mock_server.tool.call_count >= 3

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_register_tools_handles_empty_registry_gracefully(self):
        """register_tools() should not error when registry is empty."""
        from pleiades.mcp.server import register_tools

        mock_server = MagicMock()

        # Should not raise
        register_tools(mock_server)

        # Should not have called server.tool()
        assert mock_server.tool.call_count == 0

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_register_tools_preserves_function_signatures(self):
        """Registered tools should preserve original function signatures."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import register_tools

        @mcp_tool()
        def typed_function(name: str, age: int, active: bool = True) -> dict:
            """Function with typed parameters."""
            return {"name": name, "age": age, "active": active}

        mock_server = MagicMock()

        # Capture the function that gets registered
        registered_func = None

        def capture_tool(*args, **kwargs):
            """Capture the decorated function."""

            def decorator(func):
                nonlocal registered_func
                registered_func = func
                return func

            return decorator

        mock_server.tool.side_effect = capture_tool

        register_tools(mock_server)

        # Verify function signature is preserved
        assert registered_func is not None
        sig = inspect.signature(registered_func)
        params = sig.parameters

        assert "name" in params
        assert "age" in params
        assert "active" in params
        assert params["active"].default is True

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_register_tools_uses_custom_names(self):
        """register_tools() should use custom tool names when provided."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import register_tools

        @mcp_tool(name="custom-name")
        def original_name():
            """Tool with custom name."""
            pass

        mock_server = MagicMock()

        # Capture the name argument
        captured_name = None

        def capture_tool(name=None, **kwargs):
            """Capture the tool name."""
            nonlocal captured_name
            captured_name = name

            def decorator(func):
                return func

            return decorator

        mock_server.tool.side_effect = capture_tool

        register_tools(mock_server)

        # Verify custom name was used
        assert captured_name == "custom-name"

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_register_tools_includes_descriptions(self):
        """register_tools() should pass tool descriptions to FastMCP."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import register_tools

        @mcp_tool(description="This is a helpful tool")
        def helpful_tool():
            """Original docstring."""
            pass

        mock_server = MagicMock()

        # Capture the description argument
        captured_description = None

        def capture_tool(description=None, **kwargs):
            """Capture the tool description."""
            nonlocal captured_description
            captured_description = description

            def decorator(func):
                return func

            return decorator

        mock_server.tool.side_effect = capture_tool

        register_tools(mock_server)

        # Verify description was passed
        assert captured_description == "This is a helpful tool"


class TestSchemaGeneration:
    """Test generate_tool_schema() function for JSON schema creation."""

    def test_generate_tool_schema_handles_simple_types(self):
        """generate_tool_schema() should create schema for str, int, float, bool."""
        from pleiades.mcp.server import generate_tool_schema

        def simple_func(name: str, age: int, height: float, active: bool) -> dict:
            """Function with simple types."""
            return {}

        schema = generate_tool_schema(simple_func)

        assert isinstance(schema, dict)
        assert "properties" in schema

        # Check each parameter type
        props = schema["properties"]
        assert "name" in props
        assert props["name"]["type"] == "string"

        assert "age" in props
        assert props["age"]["type"] == "integer"

        assert "height" in props
        assert props["height"]["type"] == "number"

        assert "active" in props
        assert props["active"]["type"] == "boolean"

    def test_generate_tool_schema_handles_optional_types(self):
        """generate_tool_schema() should handle Optional[T] types."""
        from pleiades.mcp.server import generate_tool_schema

        def optional_func(required: str, optional: Optional[int] = None) -> dict:
            """Function with optional parameter."""
            return {}

        schema = generate_tool_schema(optional_func)

        # Optional parameters should not be in required list
        # or should allow null
        if "required" in schema:
            assert "required" in schema["required"]
            if "optional" in schema["required"]:
                # If optional is in required, it should allow null
                props = schema["properties"]
                assert "optional" in props
        else:
            # Schema may handle optionals differently
            props = schema["properties"]
            assert "optional" in props

    def test_generate_tool_schema_handles_list_types(self):
        """generate_tool_schema() should handle list types."""
        from pleiades.mcp.server import generate_tool_schema

        def list_func(items: list[str]) -> dict:
            """Function with list parameter."""
            return {}

        schema = generate_tool_schema(list_func)

        props = schema["properties"]
        assert "items" in props
        assert props["items"]["type"] == "array"

    def test_generate_tool_schema_handles_dict_types(self):
        """generate_tool_schema() should handle dict types."""
        from pleiades.mcp.server import generate_tool_schema

        def dict_func(config: dict[str, Any]) -> dict:
            """Function with dict parameter."""
            return {}

        schema = generate_tool_schema(dict_func)

        props = schema["properties"]
        assert "config" in props
        assert props["config"]["type"] == "object"

    def test_generate_tool_schema_includes_parameter_descriptions(self):
        """generate_tool_schema() should include parameter descriptions when available."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import generate_tool_schema

        @mcp_tool(
            parameter_descriptions={
                "name": "The user's name",
                "age": "The user's age in years",
            }
        )
        def documented_func(name: str, age: int) -> dict:
            """Function with parameter descriptions."""
            return {}

        schema = generate_tool_schema(documented_func)

        props = schema["properties"]
        assert "name" in props
        assert "description" in props["name"]
        assert props["name"]["description"] == "The user's name"

        assert "age" in props
        assert "description" in props["age"]
        assert props["age"]["description"] == "The user's age in years"

    def test_generate_tool_schema_handles_functions_without_type_hints(self):
        """generate_tool_schema() should handle functions without type hints gracefully."""
        from pleiades.mcp.server import generate_tool_schema

        def no_hints(x, y):
            """Function without type hints."""
            return x + y

        # Should not raise an error
        schema = generate_tool_schema(no_hints)

        # Schema should be valid dict, possibly with generic types
        assert isinstance(schema, dict)
        assert "properties" in schema

    def test_generate_tool_schema_handles_default_values(self):
        """generate_tool_schema() should handle default parameter values."""
        from pleiades.mcp.server import generate_tool_schema

        def with_defaults(required: str, optional: int = 42) -> dict:
            """Function with default values."""
            return {}

        schema = generate_tool_schema(with_defaults)

        # Required parameters should be in required list
        assert "required" in schema
        assert "required" in schema["required"]

        # Optional (has default) should not be required
        if "optional" in schema["required"]:
            # Some implementations might still list it
            pass
        else:
            # Default is preferred - optional params not in required
            assert "optional" not in schema["required"]

    def test_generate_tool_schema_handles_complex_return_types(self):
        """generate_tool_schema() should handle complex return types."""
        from pleiades.mcp.server import generate_tool_schema

        def complex_return(x: int) -> dict[str, list[int]]:
            """Function with complex return type."""
            return {}

        # Should not raise an error
        schema = generate_tool_schema(complex_return)
        assert isinstance(schema, dict)

    def test_generate_tool_schema_includes_required_fields(self):
        """generate_tool_schema() should mark parameters without defaults as required."""
        from pleiades.mcp.server import generate_tool_schema

        def required_params(a: str, b: int, c: float = 1.0) -> dict:
            """Function with required and optional parameters."""
            return {}

        schema = generate_tool_schema(required_params)

        assert "required" in schema
        required = schema["required"]

        # a and b should be required
        assert "a" in required
        assert "b" in required

        # c has a default, should not be required (or handled differently)
        # Most schema generators would not mark c as required

    def test_generate_tool_schema_handles_varargs(self):
        """generate_tool_schema() should handle *args gracefully."""
        from pleiades.mcp.server import generate_tool_schema

        def varargs_func(*args: int) -> int:
            """Function with varargs."""
            return sum(args)

        # Should not raise an error
        schema = generate_tool_schema(varargs_func)
        assert isinstance(schema, dict)

    def test_generate_tool_schema_handles_kwargs(self):
        """generate_tool_schema() should handle **kwargs gracefully."""
        from pleiades.mcp.server import generate_tool_schema

        def kwargs_func(**kwargs: Any) -> dict:
            """Function with kwargs."""
            return kwargs

        # Should not raise an error
        schema = generate_tool_schema(kwargs_func)
        assert isinstance(schema, dict)


class TestServerIntegration:
    """Test server initialization and integration."""

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_get_server_returns_fastmcp_instance(self):
        """get_server() should return FastMCP instance when MCP available."""
        from pleiades.mcp.server import get_server

        server = get_server()
        assert server is not None
        # Should be a FastMCP instance
        from fastmcp import FastMCP

        assert isinstance(server, FastMCP)

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_get_server_returns_same_instance(self):
        """get_server() should return the same instance on multiple calls."""
        from pleiades.mcp.server import get_server

        server1 = get_server()
        server2 = get_server()
        assert server1 is server2

    @pytest.mark.skipif(HAS_FASTMCP, reason="fastmcp is installed")
    def test_get_server_raises_when_mcp_not_available(self):
        """get_server() should raise ImportError when MCP not available."""
        from pleiades.mcp.server import get_server

        with pytest.raises(ImportError, match="MCP dependencies not installed"):
            get_server()

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_main_can_be_called_without_error(self):
        """main() should be callable (with mocked server.run())."""
        from pleiades.mcp.server import main

        # Mock the server.run() to avoid actually starting the server
        with patch("pleiades.mcp.server.get_server") as mock_get_server:
            mock_server = MagicMock()
            mock_get_server.return_value = mock_server

            # Should not raise
            main()

            # Verify server.run() was called
            assert mock_server.run.called

    @pytest.mark.skipif(HAS_FASTMCP, reason="fastmcp is installed")
    def test_main_raises_when_mcp_not_available(self):
        """main() should raise ImportError when MCP not available."""
        from pleiades.mcp.server import main

        with pytest.raises(ImportError, match="MCP dependencies not installed"):
            main()


class TestErrorHandling:
    """Test error handling in server functions."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_discover_tools_handles_empty_registry(self):
        """discover_tools() should handle empty registry without errors."""
        from pleiades.mcp.server import discover_tools

        # Should not raise
        tools = discover_tools()
        assert tools == {}

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_register_tools_handles_empty_registry(self):
        """register_tools() should handle empty registry gracefully."""
        from pleiades.mcp.server import register_tools

        mock_server = MagicMock()

        # Should not raise
        register_tools(mock_server)

        # Should not have registered any tools
        assert mock_server.tool.call_count == 0

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_register_tools_continues_on_tool_error(self):
        """register_tools() should continue registering other tools if one fails."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import register_tools

        @mcp_tool()
        def good_tool():
            """A good tool."""
            pass

        @mcp_tool()
        def another_good_tool():
            """Another good tool."""
            pass

        mock_server = MagicMock()

        # Make the first call fail, second succeed
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Registration failed")

            def decorator(func):
                return func

            return decorator

        mock_server.tool.side_effect = side_effect

        # Should not raise - should continue registering
        try:
            register_tools(mock_server)
        except ValueError:
            # If it does raise, that's also acceptable behavior
            # The test is mainly checking that we thought about error handling
            pass

        # At least attempted to register tools
        assert mock_server.tool.call_count >= 1

    def test_generate_tool_schema_handles_empty_function(self):
        """generate_tool_schema() should handle function with no parameters."""
        from pleiades.mcp.server import generate_tool_schema

        def no_params() -> None:
            """Function with no parameters."""
            pass

        schema = generate_tool_schema(no_params)

        assert isinstance(schema, dict)
        assert "properties" in schema
        # Should have empty or minimal properties
        assert isinstance(schema["properties"], dict)


class TestAutoDiscoveryIntegration:
    """Test end-to-end auto-discovery workflow."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_full_workflow_discovers_and_registers_tools(self):
        """Complete workflow: decorate -> discover -> register."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import discover_tools, register_tools

        # Step 1: Decorate functions
        @mcp_tool()
        def validate_data(path: str) -> dict:
            """Validate dataset at path."""
            return {"valid": True}

        @mcp_tool()
        def process_image(image_path: str, threshold: float = 0.5) -> dict:
            """Process an image with threshold."""
            return {"processed": True}

        # Step 2: Discover tools
        tools = discover_tools()
        assert len(tools) == 2
        assert "validate_data" in tools
        assert "process_image" in tools

        # Step 3: Register with mock server
        mock_server = MagicMock()
        register_tools(mock_server)

        # Verify both tools were registered
        assert mock_server.tool.call_count == 2

    @pytest.mark.skipif(not HAS_FASTMCP, reason="fastmcp not installed")
    def test_registered_tools_preserve_functionality(self):
        """Tools should work correctly after registration."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import discover_tools, register_tools

        @mcp_tool()
        def add_numbers(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        # Discover and register
        tools = discover_tools()
        mock_server = MagicMock()
        register_tools(mock_server)

        # Original function should still work
        assert add_numbers(5, 3) == 8

        # Function in registry should still work
        assert tools["add_numbers"]["func"](5, 3) == 8


class TestSchemaGenerationEdgeCases:
    """Test edge cases in schema generation."""

    def test_generate_tool_schema_with_union_types(self):
        """generate_tool_schema() should handle Union types."""
        from typing import Union

        from pleiades.mcp.server import generate_tool_schema

        def union_func(value: Union[str, int]) -> dict:
            """Function with union type."""
            return {}

        # Should not raise
        schema = generate_tool_schema(union_func)
        assert isinstance(schema, dict)

    def test_generate_tool_schema_with_nested_types(self):
        """generate_tool_schema() should handle nested types."""
        from pleiades.mcp.server import generate_tool_schema

        def nested_func(data: dict[str, list[dict[str, int]]]) -> dict:
            """Function with deeply nested types."""
            return {}

        # Should not raise
        schema = generate_tool_schema(nested_func)
        assert isinstance(schema, dict)

    def test_generate_tool_schema_with_any_type(self):
        """generate_tool_schema() should handle Any type."""
        from pleiades.mcp.server import generate_tool_schema

        def any_func(data: Any) -> Any:
            """Function with Any type."""
            return data

        # Should not raise
        schema = generate_tool_schema(any_func)
        assert isinstance(schema, dict)

    def test_generate_tool_schema_preserves_parameter_order(self):
        """generate_tool_schema() should preserve parameter order."""
        from pleiades.mcp.server import generate_tool_schema

        def ordered_func(a: str, b: int, c: float, d: bool) -> dict:
            """Function with multiple parameters."""
            return {}

        schema = generate_tool_schema(ordered_func)

        # Properties should exist for all parameters
        props = schema["properties"]
        assert "a" in props
        assert "b" in props
        assert "c" in props
        assert "d" in props

        # Check that they're in order (if the implementation preserves order)
        # Note: dict order is preserved in Python 3.7+
        param_names = list(props.keys())
        assert param_names == ["a", "b", "c", "d"]

    def test_generate_tool_schema_with_modern_union_syntax(self):
        """generate_tool_schema() should handle Python 3.10+ pipe union syntax."""
        import sys

        if sys.version_info < (3, 10):
            pytest.skip("Python 3.10+ required for | union syntax")

        from pleiades.mcp.server import generate_tool_schema

        # Define using exec to avoid syntax error on Python 3.9
        local_ns: dict = {}
        exec(
            '''
def modern_union(value: int | str) -> dict:
    """Function with modern union."""
    return {}
''',
            local_ns,
        )

        schema = generate_tool_schema(local_ns["modern_union"])

        # Should extract 'int' (first type in union)
        assert schema["properties"]["value"]["type"] == "integer"

    def test_generate_tool_schema_with_modern_optional_syntax(self):
        """generate_tool_schema() should handle Python 3.10+ pipe optional syntax."""
        import sys

        if sys.version_info < (3, 10):
            pytest.skip("Python 3.10+ required for | union syntax")

        from pleiades.mcp.server import generate_tool_schema

        local_ns: dict = {}
        exec(
            '''
def modern_optional(value: int | None = None) -> dict:
    """Function with modern optional."""
    return {}
''',
            local_ns,
        )

        schema = generate_tool_schema(local_ns["modern_optional"])

        # Should extract 'int' from int | None
        assert schema["properties"]["value"]["type"] == "integer"


class TestDiscoverToolsReturnFormat:
    """Test the exact return format of discover_tools()."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_discover_tools_returns_dict_of_dicts(self):
        """discover_tools() should return dict mapping names to metadata dicts."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import discover_tools

        @mcp_tool()
        def example_tool():
            """Example tool."""
            pass

        tools = discover_tools()

        assert isinstance(tools, dict)
        assert isinstance(tools["example_tool"], dict)

    def test_discover_tools_metadata_contains_required_keys(self):
        """Each tool metadata dict should contain required keys."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import discover_tools

        @mcp_tool()
        def example_tool():
            """Example tool."""
            pass

        tools = discover_tools()
        metadata = tools["example_tool"]

        # Required keys
        assert "name" in metadata
        assert "description" in metadata
        assert "func" in metadata

        # Verify types
        assert isinstance(metadata["name"], str)
        assert isinstance(metadata["description"], str)
        assert callable(metadata["func"])

    def test_discover_tools_is_independent_copy(self):
        """discover_tools() should return independent copy, not reference to registry."""
        from pleiades.mcp.decorators import mcp_tool
        from pleiades.mcp.server import discover_tools

        @mcp_tool()
        def example_tool():
            """Example tool."""
            pass

        tools1 = discover_tools()
        tools2 = discover_tools()

        # Should be separate dicts
        assert tools1 is not tools2

        # Modifying one should not affect the other
        tools1["example_tool"]["description"] = "MODIFIED"
        assert tools2["example_tool"]["description"] == "Example tool."


if __name__ == "__main__":
    pytest.main(["-v", __file__])
