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
      label: '🧑‍💻 API References',
      items: [
        'api-references/api-references',
        {
          type: 'category',
          label: 'Web APIs',
          items: [
            'api-references/web-apis/web-apis',
            'api-references/web-apis/web-api-health-check',
          ],
        },
        {
          type: 'category',
          label: 'MCP Server APIs',
          items: [
            'api-references/mcp-apis/mcp-apis',
            'api-references/mcp-apis/slack-post-message-mcp-api',
            'api-references/mcp-apis/slack-read-channel-messages-mcp-api',
            'api-references/mcp-apis/slack-read-thread-messages-mcp-api',
            'api-references/mcp-apis/slack-thread-reply-mcp-api',
            'api-references/mcp-apis/slack-read-emojis-mcp-api',
            'api-references/mcp-apis/slack-add-reactions-mcp-api',
          ],
        },
        {
          type: 'category',
          label: 'Webhook Server APIs',
          items: [
            'api-references/webhook-apis/webhook-apis',
            'api-references/webhook-apis/slack-events-endpoint',
            // 'api-references/webhook-apis/url-verification',
            // 'api-references/webhook-apis/security',
            'api-references/webhook-apis/server-configuration',
            'api-references/webhook-apis/standalone-server',
            'api-references/webhook-apis/integrated-server',
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
