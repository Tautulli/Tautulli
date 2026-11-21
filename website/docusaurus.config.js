// @ts-check

const repo = 'https://github.com/Tautulli/Tautulli';
const releasedUrl = 'https://docs.tautulli.com';
const nightlyUrl = 'https://nightly.docs.tautulli.com';

// Cloudflare Pages sets CF_PAGES_BRANCH and CF_PAGES_URL in its builds.
// master is the released site. Every other branch is a preview with noindex.
// nightly uses nightlyUrl. The other branches use their own pages.dev URL.
const branch = process.env.CF_PAGES_BRANCH;
const nightly = branch === 'nightly';
const preview = Boolean(branch) && branch !== 'master';

// generate-docs.py writes these pages. Their edit links open the source file.
const editSources = {
  'api-reference.md': 'plexpy/webserve.py',
  'exporter-guide.md': 'website/docs/_exporter-guide.md',
};

/** @type {import('@docusaurus/types').Config} */
module.exports = {
  title: 'Tautulli',
  tagline: 'Tautulli documentation',
  favicon: 'img/favicon.ico',
  url:
    process.env.DOCS_URL ||
    (nightly ? nightlyUrl : preview ? process.env.CF_PAGES_URL : releasedUrl),
  baseUrl: process.env.DOCS_BASE_URL || '/',
  noIndex: preview,
  // Pages build to installation.html. Cloudflare Pages serves it at
  // /installation and redirects /installation.html there.
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
          // Pull requests target nightly, and nightly holds everything on master.
          editUrl: ({docPath}) =>
            `${repo}/edit/nightly/${editSources[docPath] ?? `website/docs/${docPath}`}`,
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
    ...(nightly && {
      announcementBar: {
        content: `These docs follow the nightly branch and may describe unreleased changes. <a href="${releasedUrl}">Read the released docs</a>.`,
        isCloseable: false,
      },
    }),
    navbar: {
      title: 'Tautulli',
      logo: {alt: 'Tautulli logo', src: 'img/logo.svg'},
      items: [
        ...(preview ? [] : [{href: nightlyUrl, label: 'Nightly docs', position: 'right'}]),
        {href: repo, label: 'GitHub', position: 'right'},
      ],
    },
  },
};
