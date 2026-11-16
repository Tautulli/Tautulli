// Same order and groups as the wiki _Sidebar.md. Every page is listed by
// id, so a missing page fails the build.

const separator = {type: 'html', value: '<hr>', defaultStyle: true};

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
module.exports = {
  docs: [
    'index',
    'installation',
    separator,
    'asking-for-support',
    'frequently-asked-questions',
    'notification-agents-guide',
    'custom-notification-conditions',
    'exporter-guide',
    '3rd-party-apis-guide',
    'debugging',
    separator,
    'custom-scripts',
    'api-reference',
  ],
};
