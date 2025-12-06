#!/usr/bin/env python
"""Test suite for pleiades.mcp.decorators module.

Tests cover:
- Basic decorator registration functionality
- Name handling (default from function name vs. override)
- Description handling (from docstring vs. override)
- Function preservation (decorated functions work identically to originals)
- Parameter descriptions
- Registry access and management
- Type information storage
- Edge cases (class methods, complex type hints, varargs, async)
"""

import asyncio
from typing import Any, Optional

import pytest


class TestMcpToolDecoratorRegistration:
    """Test basic registration functionality of @mcp_tool decorator."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_decorator_registers_function(self):
        """Decorated function should be added to registry."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def example_tool():
            """Example tool."""
            return "result"

        tools = get_registered_tools()
        assert "example_tool" in tools
        assert tools["example_tool"]["func"] is example_tool

    def test_multiple_functions_can_be_registered(self):
        """Multiple decorated functions should all be registered."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

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

        tools = get_registered_tools()
        assert len(tools) == 3
        assert "tool_one" in tools
        assert "tool_two" in tools
        assert "tool_three" in tools

    def test_registry_entry_has_function_reference(self):
        """Registry entry should contain reference to the original function."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def my_function():
            """My function."""
            return 42

        tools = get_registered_tools()
        registered_func = tools["my_function"]["func"]

        # Calling registered function should produce same result
        assert registered_func() == 42


class TestMcpToolNameHandling:
    """Test name handling for @mcp_tool decorator."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_default_name_uses_function_name(self):
        """When no name provided, should use function.__name__."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def calculate_sum():
            """Calculate sum."""
            pass

        tools = get_registered_tools()
        assert "calculate_sum" in tools
        assert tools["calculate_sum"]["name"] == "calculate_sum"

    def test_name_override_uses_provided_name(self):
        """When name provided, should use that instead of function name."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool(name="custom_name")
        def original_name():
            """Function with custom name."""
            pass

        tools = get_registered_tools()
        assert "custom_name" in tools
        assert tools["custom_name"]["name"] == "custom_name"
        # Function name should still be in metadata
        assert tools["custom_name"]["func"].__name__ == "original_name"

    def test_duplicate_names_raise_error(self):
        """Registering two functions with same name should raise error."""
        from pleiades.mcp.decorators import mcp_tool

        @mcp_tool(name="duplicate")
        def first_function():
            """First function."""
            pass

        # Second function with same name should raise
        with pytest.raises(ValueError, match="already registered|duplicate"):

            @mcp_tool(name="duplicate")
            def second_function():
                """Second function."""
                pass

    def test_duplicate_function_names_raise_error(self):
        """Registering two functions with same default name should raise error."""
        from pleiades.mcp.decorators import mcp_tool

        @mcp_tool()
        def same_name():
            """First function."""
            pass

        # Second function with same name should raise
        with pytest.raises(ValueError, match="already registered|duplicate"):

            @mcp_tool()
            def same_name():  # noqa: F811
                """Second function."""
                pass


class TestMcpToolDescriptionHandling:
    """Test description handling for @mcp_tool decorator."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_default_description_uses_docstring(self):
        """When no description provided, should extract from docstring."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def tool_with_docstring():
            """This is a helpful tool that does things.

            It has multiple lines but we should get the first line or full docstring.
            """
            pass

        tools = get_registered_tools()
        description = tools["tool_with_docstring"]["description"]
        assert description is not None
        assert "helpful tool" in description.lower()

    def test_description_override_uses_provided_description(self):
        """When description provided, should use that instead of docstring."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool(description="Custom description provided")
        def tool_with_docstring():
            """This docstring should be ignored."""
            pass

        tools = get_registered_tools()
        assert tools["tool_with_docstring"]["description"] == "Custom description provided"

    def test_no_docstring_and_no_override_returns_empty_string(self):
        """Function without docstring or description should have empty/None description."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def no_docstring():
            pass

        tools = get_registered_tools()
        description = tools["no_docstring"]["description"]
        assert description is None or description == ""

    def test_multiline_docstring_preserved(self):
        """Multiline docstrings should be preserved or properly formatted."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def multiline_doc():
            """First line of docstring.

            Second paragraph with more details.
            And even more information here.
            """
            pass

        tools = get_registered_tools()
        description = tools["multiline_doc"]["description"]
        # Should contain at least the first line
        assert "First line" in description


class TestMcpToolFunctionPreservation:
    """Test that decorated functions work identically to originals."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_decorated_function_returns_same_result(self):
        """Decorated function should return same result as undecorated."""
        from pleiades.mcp.decorators import mcp_tool

        @mcp_tool()
        def add_numbers(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        assert add_numbers(5, 3) == 8
        assert add_numbers(-1, 1) == 0

    def test_decorated_function_accepts_same_arguments(self):
        """Decorated function should accept same arguments as original."""
        from pleiades.mcp.decorators import mcp_tool

        @mcp_tool()
        def greet(name: str, greeting: str = "Hello") -> str:
            """Greet someone."""
            return f"{greeting}, {name}!"

        assert greet("Alice") == "Hello, Alice!"
        assert greet("Bob", "Hi") == "Hi, Bob!"
        assert greet(name="Charlie", greeting="Hey") == "Hey, Charlie!"

    def test_decorated_function_raises_same_exceptions(self):
        """Decorated function should raise same exceptions as original."""
        from pleiades.mcp.decorators import mcp_tool

        @mcp_tool()
        def divide(a: float, b: float) -> float:
            """Divide two numbers."""
            if b == 0:
                raise ValueError("Cannot divide by zero")
            return a / b

        assert divide(10, 2) == 5.0

        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(10, 0)

    def test_decorated_async_function_works(self):
        """Async functions should work when decorated."""
        from pleiades.mcp.decorators import mcp_tool

        @mcp_tool()
        async def async_operation(value: int) -> int:
            """Async operation."""
            await asyncio.sleep(0.001)  # Minimal delay
            return value * 2

        # Test async function
        result = asyncio.run(async_operation(5))
        assert result == 10

    def test_function_with_complex_return_type(self):
        """Functions with complex return types should work."""
        from pleiades.mcp.decorators import mcp_tool

        @mcp_tool()
        def get_data() -> dict[str, list[int]]:
            """Get some data."""
            return {"numbers": [1, 2, 3], "values": [4, 5, 6]}

        result = get_data()
        assert isinstance(result, dict)
        assert result["numbers"] == [1, 2, 3]


class TestMcpToolParameterDescriptions:
    """Test parameter descriptions handling."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_custom_parameter_descriptions_are_stored(self):
        """Custom parameter descriptions should be stored in registry."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool(
            parameter_descriptions={
                "name": "The name of the person to greet",
                "age": "The age of the person",
            }
        )
        def greet_person(name: str, age: int) -> str:
            """Greet a person."""
            return f"Hello {name}, you are {age} years old"

        tools = get_registered_tools()
        param_descriptions = tools["greet_person"]["parameter_descriptions"]

        assert param_descriptions is not None
        assert param_descriptions["name"] == "The name of the person to greet"
        assert param_descriptions["age"] == "The age of the person"

    def test_missing_parameter_descriptions_default_to_empty(self):
        """When no parameter_descriptions provided, should be None or empty dict."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def simple_function(x: int) -> int:
            """Simple function."""
            return x * 2

        tools = get_registered_tools()
        param_descriptions = tools["simple_function"].get("parameter_descriptions")
        assert param_descriptions is None or param_descriptions == {}

    def test_partial_parameter_descriptions(self):
        """Parameter descriptions can be provided for subset of parameters."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool(parameter_descriptions={"important": "This parameter is important"})
        def multi_param(important: str, other: int, another: float) -> str:
            """Function with multiple parameters."""
            return f"{important}-{other}-{another}"

        tools = get_registered_tools()
        param_descriptions = tools["multi_param"]["parameter_descriptions"]

        assert "important" in param_descriptions
        assert param_descriptions["important"] == "This parameter is important"


class TestMcpToolRegistryAccess:
    """Test registry access and management functions."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_get_registered_tools_returns_all_tools(self):
        """get_registered_tools should return all registered tools."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def tool_a():
            """Tool A."""
            pass

        @mcp_tool()
        def tool_b():
            """Tool B."""
            pass

        tools = get_registered_tools()
        assert len(tools) == 2
        assert "tool_a" in tools
        assert "tool_b" in tools

    def test_get_registered_tools_returns_empty_when_nothing_registered(self):
        """get_registered_tools should return empty dict when nothing registered."""
        from pleiades.mcp.decorators import get_registered_tools

        tools = get_registered_tools()
        assert isinstance(tools, dict)
        assert len(tools) == 0

    def test_clear_registry_empties_registry(self):
        """clear_registry should remove all registered tools."""
        from pleiades.mcp.decorators import clear_registry, get_registered_tools, mcp_tool

        @mcp_tool()
        def temporary_tool():
            """Temporary tool."""
            pass

        assert len(get_registered_tools()) == 1

        clear_registry()

        assert len(get_registered_tools()) == 0

    def test_registry_entries_have_required_fields(self):
        """Each registry entry should have required fields."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def complete_tool(param: str) -> str:
            """A complete tool."""
            return param

        tools = get_registered_tools()
        entry = tools["complete_tool"]

        # Check required fields exist
        assert "name" in entry
        assert "description" in entry
        assert "func" in entry
        assert callable(entry["func"])


class TestMcpToolEdgeCases:
    """Test edge cases and special scenarios."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_classmethod_wrong_order_raises_typeerror(self):
        """Decorating classmethod descriptor (wrong order) should raise TypeError."""
        from pleiades.mcp.decorators import mcp_tool

        # Wrong order: @mcp_tool() before @classmethod
        # This applies mcp_tool to the classmethod descriptor, which is not callable
        with pytest.raises(TypeError, match="must be callable"):

            class _WrongOrderClass:
                @mcp_tool()
                @classmethod
                def wrong_order(cls):
                    pass

            _ = _WrongOrderClass  # Suppress unused variable warning

    def test_classmethod_correct_order_works(self):
        """Decorating with correct order (classmethod first) should work."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        class MyClass:
            @classmethod
            @mcp_tool()
            def correct_order(cls):
                """Correct order."""
                return "works"

        # Should be registered and callable via class
        tools = get_registered_tools()
        assert "correct_order" in tools
        assert MyClass.correct_order() == "works"

    def test_static_method_decoration(self):
        """Static methods should be decoratable."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        class MyClass:
            @staticmethod
            @mcp_tool()
            def static_tool(value: int) -> int:
                """Static method tool."""
                return value * 2

        # Should be registered
        tools = get_registered_tools()
        assert "static_tool" in tools

        # Should still work as static method
        assert MyClass.static_tool(5) == 10

    def test_function_with_complex_type_hints(self):
        """Functions with complex type hints should be registered."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def complex_types(
            items: list[str],
            mapping: dict[str, Any],
            optional: Optional[int] = None,
        ) -> list[dict[str, Any]]:
            """Function with complex type hints."""
            return [{"items": items, "mapping": mapping, "optional": optional}]

        tools = get_registered_tools()
        assert "complex_types" in tools

        # Function should still work
        result = complex_types(["a", "b"], {"key": "value"}, 42)
        assert result[0]["items"] == ["a", "b"]

    def test_function_with_default_values(self):
        """Functions with default parameter values should work."""
        from pleiades.mcp.decorators import mcp_tool

        @mcp_tool()
        def with_defaults(
            required: str,
            optional: int = 10,
            another: str = "default",
        ) -> str:
            """Function with defaults."""
            return f"{required}-{optional}-{another}"

        # Should work with defaults
        assert with_defaults("test") == "test-10-default"
        assert with_defaults("test", 20) == "test-20-default"
        assert with_defaults("test", 20, "custom") == "test-20-custom"

    def test_function_with_varargs(self):
        """Functions with *args should work."""
        from pleiades.mcp.decorators import mcp_tool

        @mcp_tool()
        def sum_all(*numbers: int) -> int:
            """Sum all numbers."""
            return sum(numbers)

        assert sum_all(1, 2, 3, 4, 5) == 15
        assert sum_all() == 0

    def test_function_with_kwargs(self):
        """Functions with **kwargs should work."""
        from pleiades.mcp.decorators import mcp_tool

        @mcp_tool()
        def build_dict(**kwargs: Any) -> dict[str, Any]:
            """Build a dictionary."""
            return kwargs

        result = build_dict(a=1, b=2, c=3)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_function_with_no_type_hints(self):
        """Functions without type hints should still work."""
        from pleiades.mcp.decorators import mcp_tool

        @mcp_tool()
        def no_hints(x, y):
            """Function without type hints."""
            return x + y

        assert no_hints(5, 3) == 8
        assert no_hints("hello", "world") == "helloworld"


class TestMcpToolTypeInformationStorage:
    """Test that type information is stored for schema generation."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_type_hints_are_accessible(self):
        """Registry should preserve function's type hints."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def typed_function(name: str, age: int) -> str:
            """Function with type hints."""
            return f"{name} is {age}"

        tools = get_registered_tools()
        func = tools["typed_function"]["func"]

        # Type hints should be accessible via __annotations__
        assert hasattr(func, "__annotations__")
        assert func.__annotations__["name"] is str
        assert func.__annotations__["age"] is int
        assert func.__annotations__["return"] is str

    def test_functions_without_type_hints_handled_gracefully(self):
        """Functions without type hints should not cause errors."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def no_types(x, y):
            """No type hints."""
            return x + y

        tools = get_registered_tools()
        func = tools["no_types"]["func"]

        # Should have empty or minimal annotations
        annotations = getattr(func, "__annotations__", {})
        assert isinstance(annotations, dict)

    def test_optional_type_hints_preserved(self):
        """Optional type hints should be preserved correctly."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def optional_params(
            required: str,
            optional: Optional[int] = None,
        ) -> Optional[str]:
            """Function with optional types."""
            if optional is not None:
                return f"{required}-{optional}"
            return required

        tools = get_registered_tools()
        func = tools["optional_params"]["func"]

        # Check annotations are preserved
        assert "required" in func.__annotations__
        assert "optional" in func.__annotations__
        assert "return" in func.__annotations__


class TestMcpToolIntegrationScenarios:
    """Test realistic integration scenarios."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_multiple_tools_with_mixed_configurations(self):
        """Multiple tools with different configurations should coexist."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def simple_tool():
            """Simple tool with defaults."""
            return "simple"

        @mcp_tool(name="custom", description="Custom description")
        def another_tool():
            """This docstring is overridden."""
            return "custom"

        @mcp_tool(
            parameter_descriptions={
                "x": "First number",
                "y": "Second number",
            }
        )
        def math_tool(x: int, y: int) -> int:
            """Perform math."""
            return x + y

        tools = get_registered_tools()
        assert len(tools) == 3

        # Verify each tool's configuration
        assert tools["simple_tool"]["name"] == "simple_tool"
        assert "Simple tool" in tools["simple_tool"]["description"]

        assert tools["custom"]["name"] == "custom"
        assert tools["custom"]["description"] == "Custom description"

        assert tools["math_tool"]["name"] == "math_tool"
        assert tools["math_tool"]["parameter_descriptions"]["x"] == "First number"

    def test_tool_can_be_called_after_registration(self):
        """Registered tools should remain callable."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def calculate(x: int, y: int) -> int:
            """Calculate something."""
            return x * y + x - y

        # Direct call
        assert calculate(5, 3) == 17

        # Call via registry
        tools = get_registered_tools()
        registered_func = tools["calculate"]["func"]
        assert registered_func(5, 3) == 17


class TestMcpToolInputValidation:
    """Test input validation for decorator arguments."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_non_callable_argument_raises_typeerror(self):
        """Passing a non-callable as func argument should raise TypeError."""
        from pleiades.mcp.decorators import mcp_tool

        # Using mcp_tool(func=...) with non-callable should fail
        with pytest.raises(TypeError, match="must be callable"):
            mcp_tool(func=123)

    def test_non_callable_string_raises_typeerror(self):
        """Passing a string as func argument should raise TypeError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(TypeError, match="must be callable"):
            mcp_tool(func="not_a_function")

    def test_name_with_newline_raises_valueerror(self):
        """Tool name with newline should raise ValueError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(ValueError, match="invalid character|alphanumeric"):

            @mcp_tool(name="tool\nname")
            def tool():
                pass

    def test_name_with_null_byte_raises_valueerror(self):
        """Tool name with null byte should raise ValueError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(ValueError, match="invalid character|alphanumeric"):

            @mcp_tool(name="tool\x00name")
            def tool():
                pass

    def test_name_with_space_raises_valueerror(self):
        """Tool name with space should raise ValueError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(ValueError, match="invalid character|alphanumeric"):

            @mcp_tool(name="tool name")
            def tool():
                pass

    def test_valid_name_with_underscore_and_hyphen(self):
        """Tool name with underscore and hyphen should be valid."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool(name="my_tool-v2")
        def tool():
            pass

        tools = get_registered_tools()
        assert "my_tool-v2" in tools

    def test_empty_parameter_descriptions_key_raises_valueerror(self):
        """Empty string key in parameter_descriptions should raise ValueError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(ValueError, match="empty|invalid"):

            @mcp_tool(parameter_descriptions={"": "description"})
            def tool():
                pass

    def test_whitespace_parameter_descriptions_key_raises_valueerror(self):
        """Whitespace-only key in parameter_descriptions should raise ValueError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(ValueError, match="empty|invalid"):

            @mcp_tool(parameter_descriptions={"   ": "description"})
            def tool():
                pass

    def test_invalid_name_type_raises_typeerror(self):
        """Non-string name should raise TypeError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(TypeError, match="name must be str"):

            @mcp_tool(name=123)
            def tool():
                pass

    def test_empty_name_raises_valueerror(self):
        """Empty string name should raise ValueError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(ValueError, match="cannot be empty"):

            @mcp_tool(name="")
            def tool():
                pass

    def test_whitespace_name_raises_valueerror(self):
        """Whitespace-only name should raise ValueError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(ValueError, match="cannot be empty"):

            @mcp_tool(name="   ")
            def tool():
                pass

    def test_invalid_description_type_raises_typeerror(self):
        """Non-string description should raise TypeError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(TypeError, match="description must be str"):

            @mcp_tool(description=["list"])
            def tool():
                pass

    def test_invalid_parameter_descriptions_type_raises_typeerror(self):
        """Non-dict parameter_descriptions should raise TypeError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(TypeError, match="parameter_descriptions must be dict"):

            @mcp_tool(parameter_descriptions="string")
            def tool():
                pass

    def test_invalid_parameter_descriptions_key_type_raises_typeerror(self):
        """Non-string keys in parameter_descriptions should raise TypeError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(TypeError, match="keys must be str"):

            @mcp_tool(parameter_descriptions={123: "value"})
            def tool():
                pass

    def test_invalid_parameter_descriptions_value_type_raises_typeerror(self):
        """Non-string values in parameter_descriptions should raise TypeError."""
        from pleiades.mcp.decorators import mcp_tool

        with pytest.raises(TypeError, match="values must be str"):

            @mcp_tool(parameter_descriptions={"key": 123})
            def tool():
                pass


class TestMcpToolRegistryMutationProtection:
    """Test that registry is protected from external mutation."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_registry_mutation_does_not_affect_internal_state(self):
        """Mutating returned registry should not affect internal registry."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def original_tool():
            """Original description."""
            return 42

        # Get registry and mutate it
        tools = get_registered_tools()
        tools["original_tool"]["description"] = "HACKED"
        tools["original_tool"]["name"] = "HACKED_NAME"

        # Get registry again - should be unchanged
        fresh_tools = get_registered_tools()
        assert fresh_tools["original_tool"]["description"] == "Original description."
        assert fresh_tools["original_tool"]["name"] == "original_tool"

    def test_adding_to_returned_registry_does_not_affect_internal(self):
        """Adding entries to returned registry should not affect internal registry."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def real_tool():
            """Real tool."""
            pass

        # Get registry and add fake entry
        tools = get_registered_tools()
        tools["fake_tool"] = {"name": "fake", "description": "fake", "func": lambda: None}

        # Get registry again - should not have fake tool
        fresh_tools = get_registered_tools()
        assert "fake_tool" not in fresh_tools
        assert len(fresh_tools) == 1

    def test_deleting_from_returned_registry_does_not_affect_internal(self):
        """Deleting entries from returned registry should not affect internal registry."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool()
        def tool_to_keep():
            """Keep me."""
            pass

        # Get registry and delete
        tools = get_registered_tools()
        del tools["tool_to_keep"]

        # Get registry again - should still have tool
        fresh_tools = get_registered_tools()
        assert "tool_to_keep" in fresh_tools


class TestMcpToolDecoratorWithoutParentheses:
    """Test decorator behavior when used without parentheses."""

    def setup_method(self):
        """Clear registry before each test."""
        from pleiades.mcp.decorators import clear_registry

        clear_registry()

    def test_decorator_without_parentheses_works(self):
        """@mcp_tool without () should work and register the tool."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool
        def tool_without_parens():
            """Tool without parentheses."""
            return "works"

        # Should be registered
        tools = get_registered_tools()
        assert "tool_without_parens" in tools

        # Should be callable
        assert tool_without_parens() == "works"

    def test_decorator_without_parentheses_uses_defaults(self):
        """@mcp_tool without () should use function name and docstring."""
        from pleiades.mcp.decorators import get_registered_tools, mcp_tool

        @mcp_tool
        def my_function():
            """My docstring."""
            pass

        tools = get_registered_tools()
        assert tools["my_function"]["name"] == "my_function"
        assert "My docstring" in tools["my_function"]["description"]


if __name__ == "__main__":
    pytest.main(["-v", __file__])
