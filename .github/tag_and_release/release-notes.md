### 🎉 New feature

1. Newborn of Slack MCP server project.
    * The entry point for the MCP server
    ```shell
    >>> slack-mcp-server --help                                                                                                                                                        ─╯
        usage: slack-mcp-server [-h] [--host HOST] [--port PORT] [--transport {stdio,sse,streamable-http}] [--mount-path MOUNT_PATH] [--env-file ENV_FILE] [--no-env-file]
                                [--slack-token SLACK_TOKEN] [--integrated] [--retry RETRY] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--log-file LOG_FILE] [--log-dir LOG_DIR]
                                [--log-format LOG_FORMAT]
        
        Run the Slack MCP server
        
        options:
          -h, --help            show this help message and exit
          --host HOST           Host to bind to when using HTTP transport (default: 127.0.0.1)
          --port PORT           Port to bind to when using HTTP transport (default: 8000)
          --transport {stdio,sse,streamable-http}
                                Transport protocol to use for MCP (studio, sse or streamable-http)
          --mount-path MOUNT_PATH
                                Mount path for HTTP transports (unused for streamable-http transport)
          --env-file ENV_FILE   Path to .env file (default: .env in current directory)
          --no-env-file         Disable loading from .env file
          --slack-token SLACK_TOKEN
                                Slack bot token (overrides SLACK_BOT_TOKEN environment variable)
          --integrated          Run MCP server integrated with webhook server in a single FastAPI application
          --retry RETRY         Number of retry attempts for network operations (default: 3)
        
        Logging Options:
          --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                                Set the logging level (default: INFO)
          --log-file LOG_FILE   Path to log file. If not set, logs to console only.
          --log-dir LOG_DIR     Directory to store log files (default: logs)
          --log-format LOG_FORMAT
                                Log message format (default: '%(asctime)s [%(levelname)8s] %(name)s: %(message)s') 
    ```
   
    * The entry point for the webhook server
    ```shell
    >>> slack-webhook-server --help                                                                                                                                                    ─╯
        usage: slack-webhook-server [-h] [--host HOST] [--port PORT] [--slack-token SLACK_TOKEN] [--env-file ENV_FILE] [--no-env-file] [--integrated] [--mcp-transport {sse,streamable-http}]
                                    [--mcp-mount-path MCP_MOUNT_PATH] [--retry RETRY] [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--log-file LOG_FILE] [--log-dir LOG_DIR]
                                    [--log-format LOG_FORMAT]
        
        Run the Slack events server
        
        options:
          -h, --help            show this help message and exit
          --host HOST           Host to listen on (default: 0.0.0.0)
          --port PORT           Port to listen on (default: 3000)
          --slack-token SLACK_TOKEN
                                Slack bot token to use (overrides SLACK_BOT_TOKEN environment variable)
          --env-file ENV_FILE   Path to .env file (default: .env in current directory)
          --no-env-file         Disable loading from .env file
          --integrated          Run the integrated server with both MCP and webhook functionalities
          --mcp-transport {sse,streamable-http}
                                Transport to use for MCP server when running in integrated mode (default: sse)
          --mcp-mount-path MCP_MOUNT_PATH
                                Mount path for MCP server when using sse transport (default: /mcp)
          --retry RETRY         Number of retry attempts for network operations (default: 3)
        
        Logging Options:
          --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                                Set the logging level (default: INFO)
          --log-file LOG_FILE   Path to log file. If not set, logs to console only.
          --log-dir LOG_DIR     Directory to store log files (default: logs)
          --log-format LOG_FORMAT
                                Log message format (default: '%(asctime)s [%(levelname)8s] %(name)s: %(message)s')
    ```
2. Support MCP functions:
    * `send_slack_message`
    * `read_slack_channel_messages`
    * `read_thread_messages`
    * `send_slack_thread_reply`
    * `read_slack_emojis`
    * `add_slack_reactions`
3. Support handle the Slack event via handler as object-oriented or decorator


### 📑 Docs

1. Provide the [details] in [documentation].

[details]: https://chisanan232.github.io/slack-mcp-server/docs/next/introduction
[documentation]: https://chisanan232.github.io/slack-mcp-server/


### 🤖 Upgrade dependencies

1. Upgrade the Python dependencies.
2. Upgrade pre-commit dependencies.
3. Upgrade the CI reusable workflows.
