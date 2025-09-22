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
  
  // Paths reflect the routing structure with routeBasePath: '/'
  const versions = [
    {
      name: 'current',
      label: 'Next',
      // Current version is at root with document subfolder
      path: `${baseUrl}next/document/intro`,
      isLast: false,
    },
    {
      name: '0.1.0',
      label: '0.1.0',
      // In Docusaurus, versions are accessible by just their version name followed by document path
      path: `${baseUrl}document/intro`,
      isLast: true,
    },
  ];

  const currentVersion = versions.find(version => version.name === 'current');
  const pastVersions = versions.filter(version => version.name !== 'current');

  return (
    <Layout
      title="Versions"
      description="GearMeshing-AI Documentation Versions">
      <main className="container margin-vert--lg">
        <Heading as="h1">
          GearMeshing-AI Documentation Versions
        </Heading>

        <div className="margin-bottom--lg">
          <Heading as="h2" id="next">
            Current Development Version
          </Heading>
          <p>
            Here you can find the documentation for current development work.
          </p>
          <table>
            <tbody>
              <Version {...currentVersion} />
            </tbody>
          </table>
        </div>

        {pastVersions.length > 0 && (
          <div className="margin-bottom--lg">
            <Heading as="h2" id="archive">
              Past Versions
            </Heading>
            <p>
              Here you can find previous versions of the documentation.
            </p>
            <table>
              <tbody>
                {pastVersions.map((version) => (
                  <Version key={version.name} {...version} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </Layout>
  );
}
