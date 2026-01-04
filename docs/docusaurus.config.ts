import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Vidurai Documentation',
  tagline: 'Intelligent Memory for AI Coding Assistants',
  favicon: 'favicon.ico',

  url: 'https://docs.vidurai.ai',
  baseUrl: '/',

  organizationName: 'chandantochandan',
  projectName: 'vidurai-docs',

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/chandantochandan/vidurai-docs/tree/main/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/logo.jpg',
    navbar: {
      title: 'Vidurai',
      logo: {
        alt: 'Vidurai Logo',
        src: 'img/logo.jpg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'tutorialSidebar',
          position: 'left',
          label: 'SDK Docs',
        },
        {
          href: 'https://pypi.org/project/vidurai/',
          label: 'PyPI',
          position: 'left',
        },
        {
          href: 'https://marketplace.visualstudio.com/items?itemName=vidurai.vidurai',
          label: 'VS Code Extension',
          position: 'left',
        },
        {
          href: 'https://vidurai.ai',
          label: 'Main Site',
          position: 'right',
        },
        {
          href: 'https://github.com/chandantochandan/vidurai',
          label: 'GitHub',
          position: 'right',
        },
        {
          href: 'https://discord.gg/DHdgS8eA',
          label: 'Discord',
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
              label: 'Introduction',
              to: '/docs/intro',
            },
            {
              label: 'Quick Start',
              to: '/docs/quickstart',
            },
          ],
        },
        {
          title: 'Community',
          items: [
            {
              label: 'Discord',
              href: 'https://discord.gg/DHdgS8eA',
            },
            {
              label: 'GitHub SDK',
              href: 'https://github.com/chandantochandan/vidurai',
            },
            {
              label: 'GitHub Extension',
              href: 'https://github.com/chandantochandan/vidurai-vscode-extension',
            },
          ],
        },
        {
          title: 'More',
          items: [
            {
              label: 'Main Website',
              href: 'https://vidurai.ai',
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} Vidurai. Built with Docusaurus.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;