# Type Checking Examples

This directory contains examples demonstrating type checking features and best practices for the Slack MCP Server project.

## Examples

### `type_checking_example.py`

Comprehensive example demonstrating:
- Using type annotations with Slack events
- Protocol types for structural subtyping
- Type guards for runtime validation
- Queue backend implementations with type safety
- Transport configuration with literal types
- Event handler function types

## Running the Examples

### Type Check the Example

```bash
# Run MyPy on the example
uv run mypy examples/type_checking/type_checking_example.py
```

### Execute the Example

```bash
# Run the example code
uv run python examples/type_checking/type_checking_example.py
```

## Expected Output

When you run the example, you should see:

```
=== Type Checking Examples ===

Registered handler: TypedSlackHandler
Registered handler: CustomEventHandler

=== Type Guard Validation ===
Channel valid: True
User valid: True
Timestamp valid: True
Invalid channel: True
Invalid user: True
Invalid timestamp: True

=== Transport Configuration ===
stdio: {'transport': 'stdio', 'stdio': True}
sse: {'transport': 'sse', 'host': '0.0.0.0', 'port': 8000}
streamable-http: {'transport': 'streamable-http', 'host': '0.0.0.0', 'port': 8000}

=== SlackEvent Enum ===
Total events: 99
Message event: message
Reaction added: reaction_added

=== Event Handler Registration ===
Registered handler: async_message_handler
Registered handler: sync_message_handler

✓ All type checking examples completed successfully!
```

## Related Documentation

- [Type Checking with MyPy](../../docs/contents/development/type-checking.mdx)
- [Type Checking Workflow](../../docs/contents/development/ci-cd/type-checking-workflow.mdx)
- [Quick Reference Guide](../../TYPE_CHECKING_GUIDE.md)
- [Types Module README](../../slack_mcp/types.README.md)

## Adding New Examples

When adding new type checking examples:

1. Create a new Python file in this directory
2. Add comprehensive docstrings explaining the example
3. Include type annotations for all functions and variables
4. Ensure the example passes MyPy type checking
5. Update this README with the new example
6. Add the example to the CI workflow if appropriate
