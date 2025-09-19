import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

/**
 * Sidebar for the Docs section
 */
const sidebars: SidebarsConfig = {
  docs: [
    'introduction',
    {
      type: 'category',
      label: '🤟 Quickly Start',
      collapsed: false,
      items: [
        'quick-start/quick-start',
        'quick-start/requirements',
        'quick-start/installation',
        'quick-start/how-to-run',
      ],
    },
    {
      type: 'category',
      label: '🧑‍💻 Server References',
      items: [
        'server-references/server-references',
        'server-references/environment-configuration',
        'server-references/cli-execution-methods',
        'server-references/deployment-guide',
        {
          type: 'category',
          label: 'Web Server',
          items: [
            'server-references/web-server/web-apis',
            {
              type: 'category',
              label: 'End-points',
              items: [
                'server-references/web-server/end-points/web-api-health-check',
              ],
            },
          ],
        },
        {
          type: 'category',
          label: 'MCP Server',
          items: [
            'server-references/mcp-server/mcp-apis',
            'server-references/mcp-server/mcp-server-cli-reference',
            {
              type: 'category',
              label: 'Tools (End-points)',
              items: [
                'server-references/mcp-server/end-points/slack-post-message-mcp-api',
                'server-references/mcp-server/end-points/slack-read-channel-messages-mcp-api',
                'server-references/mcp-server/end-points/slack-read-thread-messages-mcp-api',
                'server-references/mcp-server/end-points/slack-thread-reply-mcp-api',
                'server-references/mcp-server/end-points/slack-read-emojis-mcp-api',
                'server-references/mcp-server/end-points/slack-add-reactions-mcp-api',
              ],
            },
          ],
        },
        {
          type: 'category',
          label: 'Webhook Server',
          items: [
            'server-references/webhook-server/webhook-apis',
            'server-references/webhook-server/webhook-server-cli-reference',
            {
              type: 'category',
              label: 'End-points',
              items: [
                'server-references/webhook-server/end-points/slack-events-endpoint',
              ],
            },
            'server-references/webhook-server/server-modes',
          ],
        },
      ],
    },
    {
      type: 'category',
      label: '👋 Welcome to contribute',
      items: [
        'contribute/contribute',
        'contribute/report-bug',
        'contribute/request-changes',
        'contribute/discuss',
      ],
    },
    'changelog',
  ],
};

export default sidebars;
