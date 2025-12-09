"""Console entry-point for Slack MCP server.

Run with:

.. code-block:: bash

    python -m slack_mcp.mcp --transport sse --port 8000

This delegates to `slack_mcp.mcp.entry.main()`.
"""
from slack_mcp.mcp.entry import main

if __name__ == "__main__":
    main()
