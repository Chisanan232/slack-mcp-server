"""Console entry-point for Slack webhook server.

Run with:

.. code-block:: bash

    python -m slack_mcp.webhook --port 3000

This delegates to `slack_mcp.webhook.entry.main()`.
"""

from slack_mcp.webhook.entry import main

if __name__ == "__main__":
    main()
