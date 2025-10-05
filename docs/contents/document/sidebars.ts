import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

/**
 * Sidebar for the Docs section
 */
const sidebars: SidebarsConfig = {
  docs: [
    {
      type: 'doc',
      id: 'introduction',
      label: '📖 Introduction',
    },
    {
      type: 'category',
      label: '🤟 Quickly Start',
      collapsed: false,
      items: [
        {
          type: 'doc',
          id: 'quick-start/quick-start',
          label: '⚡ Quick Start',
        },
        {
          type: 'doc',
          id: 'quick-start/requirements',
          label: '📋 Requirements',
        },
        {
          type: 'doc',
          id: 'quick-start/installation',
          label: '💾 Installation',
        },
        {
          type: 'doc',
          id: 'quick-start/how-to-run',
          label: '▶️ How to Run',
        },
      ],
    },
    {
      type: 'category',
      label: '🧑‍💻 Server References',
      items: [
        {
          type: 'doc',
          id: 'server-references/server-references',
          label: '📚 Server References',
        },
        {
          type: 'doc',
          id: 'server-references/environment-configuration',
          label: '🌍 Environment Configuration',
        },
        {
          type: 'doc',
          id: 'server-references/cli-execution-methods',
          label: '⌨️ CLI Execution Methods',
        },
        {
          type: 'doc',
          id: 'server-references/deployment-guide',
          label: '🚀 Deployment Guide',
        },
        {
          type: 'category',
          label: '🌐 Web Server',
          items: [
            {
              type: 'doc',
              id: 'server-references/web-server/web-apis',
              label: '🌐 Web APIs',
            },
            {
              type: 'category',
              label: '🔌 End-points',
              items: [
                {
                  type: 'doc',
                  id: 'server-references/web-server/end-points/web-api-health-check',
                  label: '💓 Health Check',
                },
              ],
            },
          ],
        },
        {
          type: 'category',
          label: '🤖 MCP Server',
          items: [
            {
              type: 'doc',
              id: 'server-references/mcp-server/mcp-apis',
              label: '🔧 MCP APIs',
            },
            {
              type: 'doc',
              id: 'server-references/mcp-server/mcp-server-cli-reference',
              label: '⌨️ CLI Reference',
            },
            {
              type: 'doc',
              id: 'server-references/mcp-server/mcp-server-modes',
              label: '🔄 Server Modes',
            },
            {
              type: 'doc',
              id: 'server-references/mcp-server/mcp-client-examples',
              label: '📱 Client Examples',
            },
            {
              type: 'category',
              label: '🛠️ Tools (End-points)',
              items: [
                {
                  type: 'doc',
                  id: 'server-references/mcp-server/end-points/slack-post-message-mcp-api',
                  label: '💬 Post Message',
                },
                {
                  type: 'doc',
                  id: 'server-references/mcp-server/end-points/slack-read-channel-messages-mcp-api',
                  label: '📖 Read Channel Messages',
                },
                {
                  type: 'doc',
                  id: 'server-references/mcp-server/end-points/slack-read-thread-messages-mcp-api',
                  label: '🧵 Read Thread Messages',
                },
                {
                  type: 'doc',
                  id: 'server-references/mcp-server/end-points/slack-thread-reply-mcp-api',
                  label: '↩️ Thread Reply',
                },
                {
                  type: 'doc',
                  id: 'server-references/mcp-server/end-points/slack-read-emojis-mcp-api',
                  label: '😀 Read Emojis',
                },
                {
                  type: 'doc',
                  id: 'server-references/mcp-server/end-points/slack-add-reactions-mcp-api',
                  label: '👍 Add Reactions',
                },
              ],
            },
          ],
        },
        {
          type: 'category',
          label: '🪝 Webhook Server',
          items: [
            {
              type: 'doc',
              id: 'server-references/webhook-server/webhook-apis',
              label: '🪝 Webhook APIs',
            },
            {
              type: 'doc',
              id: 'server-references/webhook-server/webhook-server-cli-reference',
              label: '⌨️ CLI Reference',
            },
            {
              type: 'doc',
              id: 'server-references/webhook-server/server-modes',
              label: '🔄 Server Modes',
            },
            {
              type: 'doc',
              id: 'server-references/webhook-server/event-handlers',
              label: '⚡ Event Handlers & Queue Architecture',
            },
            {
              type: 'category',
              label: '🔌 End-points',
              items: [
                {
                  type: 'doc',
                  id: 'server-references/webhook-server/end-points/slack-events-endpoint',
                  label: '📡 Slack Events Endpoint',
                },
              ],
            },
          ],
        },
      ],
    },
    {
      type: 'category',
      label: '👋 Welcome to contribute',
      items: [
        {
          type: 'doc',
          id: 'contribute/contribute',
          label: '🤝 Contribute',
        },
        {
          type: 'doc',
          id: 'contribute/report-bug',
          label: '🐛 Report Bug',
        },
        {
          type: 'doc',
          id: 'contribute/request-changes',
          label: '💡 Request Changes',
        },
        {
          type: 'doc',
          id: 'contribute/discuss',
          label: '💬 Discuss',
        },
      ],
    },
    {
      type: 'doc',
      id: 'changelog',
      label: '📝 Changelog',
    },
  ],
};

export default sidebars;
