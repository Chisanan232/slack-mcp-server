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
        {
          type: 'category',
          label: 'Web Server',
          items: [
            'server-references/web-server/web-apis',
            'server-references/web-server/web-api-health-check',
          ],
        },
        {
          type: 'category',
          label: 'MCP Server',
          items: [
            'server-references/mcp-server/mcp-apis',
            'server-references/mcp-server/slack-post-message-mcp-api',
            'server-references/mcp-server/slack-read-channel-messages-mcp-api',
            'server-references/mcp-server/slack-read-thread-messages-mcp-api',
            'server-references/mcp-server/slack-thread-reply-mcp-api',
            'server-references/mcp-server/slack-read-emojis-mcp-api',
            'server-references/mcp-server/slack-add-reactions-mcp-api',
          ],
        },
        {
          type: 'category',
          label: 'Webhook Server',
          items: [
            'server-references/webhook-server/webhook-apis',
            'server-references/webhook-server/slack-events-endpoint',
            // 'server-references/webhook-server/url-verification',
            // 'server-references/webhook-server/security',
            'server-references/webhook-server/server-configuration',
            'server-references/webhook-server/standalone-server',
            'server-references/webhook-server/integrated-server',
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
