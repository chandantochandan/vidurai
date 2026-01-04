import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.
 */
const sidebars: SidebarsConfig = {
  tutorialSidebar: [
    'intro',
    'installation',
    'quickstart',
    {
      type: 'category',
      label: 'Architecture',
      collapsed: false,
      items: [
        'architecture/three-kosha',
        'architecture/vismriti-engine',
        'architecture/rl-agent',
        'architecture/viveka-layer',
      ],
    },
    {
      type: 'category',
      label: 'Guides',
      collapsed: false,
      items: [
        'guides/getting-started',
        'guides/memory-management',
        'guides/compression-strategies',
        'guides/troubleshooting',
      ],
    },
    'configuration',
    'best-practices',
    {
      type: 'category',
      label: 'Integrations',
      collapsed: false,
      items: [
        'integrations/langchain',
        'integrations/llamaindex',
        'integrations/custom-integration',
      ],
    },
    'api-reference',
    'faq',
  ],
};

export default sidebars;
