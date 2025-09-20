import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';
import remarkGfm from 'remark-gfm';
import remarkMdxCodeMeta from 'remark-mdx-code-meta';

const config: Config = {
  title: 'Slack-MCP-Server',
  tagline: '🦾 A strong MCP server for Slack.',
  favicon: 'img/Slack_icon_2019.svg.png',

  // Set the production url of your site here
  url: 'https://chisanan232.github.io',
  // Set the /<baseUrl>/ pathname under which your site is served
  baseUrl: '/slack-mcp-server/',
  projectName: 'chisanan232.github.io',
  organizationName: 'chisanan232',
  trailingSlash: false,

  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',
  onDuplicateRoutes: 'warn',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  markdown: {
    mermaid: true,
    format: 'detect',
    mdx1Compat: {
      comments: true,
      admonitions: true,
      headingIds: true,
    },
  },

  presets: [
    [
      'classic',
      {
        docs: false,
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  plugins: [
    [
      '@docusaurus/plugin-content-docs',
      {
        id: 'docs',
        path: 'contents/document',
        routeBasePath: 'docs',
        sidebarPath: './contents/document/sidebars.ts',
        sidebarCollapsible: true,
        showLastUpdateTime: true,
        showLastUpdateAuthor: true,
        editUrl:
          'https://github.com/Chisanan232/slack-mcp-server/tree/master/docs/',
        versions: {
          current: {
            label: 'Next',
            path: 'next',
            banner: 'unreleased',
            badge: true,
          },
        },
        includeCurrentVersion: true,
        lastVersion: 'current',
      },
    ],
    [
      '@docusaurus/plugin-content-docs',
      {
        id: 'dev',
        path: 'contents/development',
        routeBasePath: 'dev',
        sidebarPath: './contents/development/sidebars.ts',
        sidebarCollapsible: true,
        showLastUpdateTime: true,
        showLastUpdateAuthor: true,
        editUrl:
          'https://github.com/Chisanan232/slack-mcp-server/tree/master/docs/',
        versions: {
          current: {
            label: 'Next',
            path: 'next',
            banner: 'unreleased',
            badge: true,
          },
        },
        includeCurrentVersion: true,
        lastVersion: 'current',
      },
    ],
    [
      '@docusaurus/plugin-content-blog',
      {
        id: 'blog',
        path: 'contents/blog',
        routeBasePath: 'blog',
        showReadingTime: true,
        editUrl:
          'https://github.com/Chisanan232/slack-mcp-server/tree/master/docs/',
      },
    ],
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {
        // Options for docusaurus-search-local
        hashed: true,
        language: ['en'],
        docsRouteBasePath: ['/slack-mcp-server'],
        docsDir: ['./contents/document', './contents/development'],
        blogDir: ['./contents/blog'],
        highlightSearchTermsOnTargetPage: true,
        explicitSearchResultPath: true,
        docsPluginIdForPreferredVersion: 'docs',
        indexDocs: true,
        indexBlog: true,
        indexPages: true,
      },
    ],
  ],

  themes: [
    '@docusaurus/theme-mermaid',
  ],

  themeConfig: {
    // Replace with your project's social card
    image: 'img/Slack_icon_2019.svg.png',
    navbar: {
      title: 'Slack-MCP-Server',
      logo: {
        alt: 'My Site Logo',
        src: 'img/Slack_icon_2019.svg.png',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docs',
          position: 'left',
          label: 'Docs',
          docsPluginId: 'docs',
        },
        {
          type: 'docSidebar',
          sidebarId: 'dev',
          position: 'left',
          label: 'Dev',
          docsPluginId: 'dev',
        },
        {
          to: '/blog',
          label: 'Blog',
          position: 'left',
        },
        {
          type: 'custom-unifiedVersions',
          position: 'right',
          pluginIds: ['docs', 'dev'],
          pluginTitles: {
            docs: 'User Guide',
            dev: 'Developer Guide',
          },
          showBadges: true,
          showDividers: true,
          showNextLabel: true,
          showUnmaintainedLabel: true,
          dropdownItemsBefore: [],
          dropdownItemsAfter: [],
        },
        {
          href: 'https://github.com/Chisanan232/slack-mcp-server',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {
              label: 'Docs',
              to: '/docs/next/introduction',
            },
            {
              label: 'Dev',
              to: '/dev/next',
            },
            {
              label: 'Blog',
              to: '/blog',
            },
          ],
        },
        {
          title: 'Community',
          items: [
            {
              label: 'GitHub Issues',
              href: 'https://github.com/Chisanan232/slack-mcp-server/issues',
            },
            {
              label: 'GitHub Discussions',
              href: 'https://github.com/Chisanan232/slack-mcp-server/discussions',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'GitHub Repository',
              href: 'https://github.com/Chisanan232/slack-mcp-server',
            },
          ],
        },
      ],
      copyright: `Copyright ${new Date().getFullYear()} - PRESENT, Slack MCP Server is owned by <a href="https://github.com/Chisanan232">@Chisanan232</a>.<br />Built with <a href="https://docusaurus.io/">Docusaurus</a>.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  },

  // Add redirect for homepage
  staticDirectories: ['static'],
  // Homepage redirects to documentation
  headTags: [
    {
      tagName: 'link',
      attributes: {
        rel: 'canonical',
        href: 'https://chisanan232.github.io/slack-mcp-server/docs/introduction',
      },
    },
  ],
};

export default config;
