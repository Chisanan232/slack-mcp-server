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
          label: 'Web APIs',
          items: [
            'server-references/web-apis/web-apis',
            'server-references/web-apis/web-api-health-check',
          ],
        },
        {
          type: 'category',
          label: 'MCP Server APIs',
          items: [
            'server-references/mcp-apis/mcp-apis',
            'server-references/mcp-apis/slack-post-message-mcp-api',
            'server-references/mcp-apis/slack-read-channel-messages-mcp-api',
            'server-references/mcp-apis/slack-read-thread-messages-mcp-api',
            'server-references/mcp-apis/slack-thread-reply-mcp-api',
            'server-references/mcp-apis/slack-read-emojis-mcp-api',
            'server-references/mcp-apis/slack-add-reactions-mcp-api',
          ],
        },
        {
          type: 'category',
          label: 'Webhook Server APIs',
          items: [
            'server-references/webhook-apis/webhook-apis',
            'server-references/webhook-apis/slack-events-endpoint',
            // 'server-references/webhook-apis/url-verification',
            // 'server-references/webhook-apis/security',
            'server-references/webhook-apis/server-configuration',
            'server-references/webhook-apis/standalone-server',
            'server-references/webhook-apis/integrated-server',
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
