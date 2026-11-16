// @ts-check

const repo = 'https://github.com/Tautulli/Tautulli';

/** @type {import('@docusaurus/types').Config} */
module.exports = {
  title: 'Tautulli',
  tagline: 'Tautulli documentation',
  favicon: 'img/favicon.ico',
  url: process.env.DOCS_URL || 'https://docs.tautulli.com',
  baseUrl: process.env.DOCS_BASE_URL || '/',
  // Docusaurus asks for an explicit value on GitHub Pages. Pages build to
  // installation.html, and GitHub Pages serves it at /installation.
  trailingSlash: false,

  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',
  markdown: {
    // .md files are CommonMark. Only .mdx files get MDX parsing.
    format: 'detect',
    hooks: {onBrokenMarkdownLinks: 'throw'},
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          routeBasePath: '/',
          sidebarPath: './sidebars.js',
          // api-reference.md is generated, so its edit link opens the docstrings.
          editUrl: ({docPath}) =>
            docPath === 'api-reference.md'
              ? `${repo}/edit/master/plexpy/webserve.py`
              : `${repo}/edit/master/website/docs/${docPath}`,
        },
        blog: false,
        pages: false,
        theme: {customCss: './src/css/custom.css'},
      }),
    ],
  ],

  themes: [
    [
      '@easyops-cn/docusaurus-search-local',
      {
        hashed: 'filename',
        docsRouteBasePath: '/',
        indexBlog: false,
        indexPages: false,
      },
    ],
  ],

  themeConfig: {
    colorMode: {defaultMode: 'dark'},
    navbar: {
      title: 'Tautulli',
      logo: {alt: 'Tautulli logo', src: 'img/logo.svg'},
      items: [{href: repo, label: 'GitHub', position: 'right'}],
    },
  },
};
