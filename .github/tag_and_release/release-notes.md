### 🎉 New features

1. **Structured Output Models**: Added comprehensive dataclass models for all MCP tools in `slack_mcp/mcp/model/output.py` for better type safety and consistency. ([PR#276])
2. **Emoji Resource**: Added `slack://emojis` resource for workspace emoji list, replacing the deprecated `read_slack_emojis` tool. ([PR#276])
3. **Enhanced Metadata**: Added comprehensive metadata (`title` and `annotations`) for all MCP tools to improve LLM discovery and user experience. ([PR#276])
4. **Comprehensive Docstrings**: Added detailed documentation for all modules, objects, and functions throughout the codebase for better developer experience. ([PR#263])

### 🔄 Changes

1. **MCP Export Normalization**: Normalized MCP exports to clearly distinguish between tools and resources (no behavior changes). ([PR#276])
2. **Consolidated Prompts**: Merged instruction prompts into tool docstrings for better LLM discovery and reduced complexity. ([PR#276])
3. **Tool Deprecation**: Marked `read_slack_emojis` tool as deprecated in favor of the new `slack://emojis` resource. ([PR#276])
4. **Pydantic Settings Migration**: Migrated from direct environment variable access to Pydantic-based settings models for better type safety and configuration management. ([PR#281])
5. **Dependency Cleanup**: Removed `python-dotenv` dependency and replaced with Pydantic settings for secret management. ([PR#281])

### 🗑️ Removed

1. **Prompt Endpoints**: Removed explicit `@mcp.prompt` endpoints (functionality merged into tool descriptions). ([PR#276])
2. **python-dotenv**: Removed dependency in favor of Pydantic settings for environment variable management. ([PR#281])

### 🧑‍💻 Developer

1. **Code Owner Updates**: Updated code owner settings for document scope management. ([PR#290])
2. **Enhanced Type Safety**: Improved type checking and data validation through Pydantic models. ([PR#281])
3. **Better Configuration Management**: Centralized configuration through Pydantic settings with proper secret handling. ([PR#281])

### 🤖 Upgrade dependencies

1. **Major MCP Upgrade**: Bumped MCP from 1.10.1 to 1.23.0 with significant protocol improvements. ([PR#285])
2. **FastAPI Updates**: Multiple FastAPI upgrades from 0.121.0 to 0.135.3 for performance and security improvements. ([PRs#270,271,274,258,257,246,241,238,313,339])
3. **Pydantic Settings Upgrade**: Upgraded from 2.10.1 to 2.13.0 for enhanced settings management. ([PRs#286,303])
4. **Slack SDK Updates**: Upgraded slack-sdk from 3.37.0 to 3.39.0 for latest API support. ([PRs#243,237])
5. **Testing Framework Updates**: Upgraded pytest ecosystem (pytest, pytest-cov, pytest-asyncio, pytest-rerunfailures) for better testing capabilities. ([PRs#249,250,248,236])
6. **Development Tools**: Upgraded mypy, pylint, coverage, and pre-commit for enhanced code quality. ([PRs#254,252,247,267,269,244,291])
7. **Documentation Dependencies**: Updated TypeScript from 5.9.3 to 6.0.2 in documentation build. ([PR#330])
8. **Core Python Dependencies**: Multiple dependency updates including coverage, ruff, and development tools. ([PRs#291,305,313,339])

[PR#276]: https://github.com/Chisanan232/slack-mcp-server/pull/276
[PR#281]: https://github.com/Chisanan232/slack-mcp-server/pull/281
[PR#263]: https://github.com/Chisanan232/slack-mcp-server/pull/263
[PR#290]: https://github.com/Chisanan232/slack-mcp-server/pull/290
[PR#285]: https://github.com/Chisanan232/slack-mcp-server/pull/285
[PR#286]: https://github.com/Chisanan232/slack-mcp-server/pull/286
[PR#291]: https://github.com/Chisanan232/slack-mcp-server/pull/291
[PR#303]: https://github.com/Chisanan232/slack-mcp-server/pull/303
[PR#305]: https://github.com/Chisanan232/slack-mcp-server/pull/305
[PR#313]: https://github.com/Chisanan232/slack-mcp-server/pull/313
[PR#330]: https://github.com/Chisanan232/slack-mcp-server/pull/330
[PR#339]: https://github.com/Chisanan232/slack-mcp-server/pull/339
