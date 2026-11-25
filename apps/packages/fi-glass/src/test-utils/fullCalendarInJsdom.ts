// FullCalendar injects an @font-face whose data URI jsdom's CSS parser rejects at import time.
const insertRule = CSSStyleSheet.prototype.insertRule;
CSSStyleSheet.prototype.insertRule = function replaceFontFaces(rule, index) {
  return insertRule.call(this, rule.startsWith('@font-face') ? '.fc-icon-font{}' : rule, index);
};
