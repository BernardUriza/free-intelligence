const path = require('node:path');

const dist = path.join(__dirname, 'dist').split(path.sep).join('/');

/**
 * The Tailwind contract of fi-glass: its dist ships utility CLASS STRINGS, not
 * compiled CSS, so a consumer's Tailwind must scan these files or the UI renders unstyled.
 * @type {{ content: string[] }}
 */
module.exports = {
  content: [`${dist}/**/*.{js,mjs}`],
};
