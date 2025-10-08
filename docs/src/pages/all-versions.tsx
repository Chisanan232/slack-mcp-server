import React from 'react';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

// This is a simplified version page that doesn't depend on specific client imports
function Version({name, label, path, isLast}) {
  return (
    <tr>
      <th>{label}</th>
      <td>
        <Link to={path}>Documentation</Link>
      </td>
    </tr>
  );
}

export default function VersionsPage() {
  const {siteConfig} = useDocusaurusContext();
  const {baseUrl} = siteConfig;
  
  // Paths reflect the routing structure for docs and dev plugins
  const docVersions = [
    {
      name: 'current',
      label: 'Next',
      path: `${baseUrl}docs/next/introduction`,
      isLast: false,
    },
    {
      name: '0.0.1',
      label: '0.0.1',
      path: `${baseUrl}docs/0.0.1/introduction`,
      isLast: true,
    },
  ];

  const devVersions = [
    {
      name: 'current',
      label: 'Next',
      path: `${baseUrl}dev/next`,
      isLast: false,
    },
    {
      name: '0.0.1',
      label: '0.0.1',
      path: `${baseUrl}dev/0.0.1`,
      isLast: true,
    },
  ];

  return (
    <Layout
      title="Versions"
      description="Slack MCP Server Documentation Versions">
      <main className="container margin-vert--lg">
        <Heading as="h1">
          Slack MCP Server Documentation Versions
        </Heading>

        <div className="margin-bottom--lg">
          <Heading as="h2" id="docs">
            User Documentation
          </Heading>
          <p>
            Complete user guide, tutorials, and API references.
          </p>
          <table>
            <tbody>
              {docVersions.map((version) => (
                <Version key={`docs-${version.name}`} {...version} />
              ))}
            </tbody>
          </table>
        </div>

        <div className="margin-bottom--lg">
          <Heading as="h2" id="dev">
            Developer Documentation
          </Heading>
          <p>
            Development guides, architecture, and contribution information.
          </p>
          <table>
            <tbody>
              {devVersions.map((version) => (
                <Version key={`dev-${version.name}`} {...version} />
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </Layout>
  );
}
