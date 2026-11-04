export interface FlatRule {
  condition: string | null;
  selector: string;
  style: CSSStyleDeclaration;
}

function conditionOf(rule: CSSRule): string | null {
  const media = (rule as CSSMediaRule).media;
  if (media) return media.mediaText;
  const text = (rule as CSSRule & { conditionText?: string }).conditionText;
  return text ?? null;
}

function flatten(rules: CSSRuleList, condition: string | null, acc: FlatRule[]): FlatRule[] {
  for (const rule of Array.from(rules)) {
    if (rule instanceof CSSStyleRule) {
      acc.push({ condition, selector: rule.selectorText.replace(/\s+/g, ' ').trim(), style: rule.style });
    } else if ((rule as CSSGroupingRule).cssRules) {
      flatten((rule as CSSGroupingRule).cssRules, conditionOf(rule), acc);
    }
  }
  return acc;
}

/** Parses an injected `<style id>` through the browser's CSSOM, one entry per style rule. */
export function rulesOf(styleId: string): FlatRule[] {
  const el = document.getElementById(styleId) as HTMLStyleElement | null;
  if (!el?.sheet) throw new Error(`no stylesheet #${styleId} in the document`);
  return flatten(el.sheet.cssRules, null, []);
}

/**
 * The value `property` gets from the rule with EXACTLY `selector` under EXACTLY
 * `condition` (null = top level). Empty string when that rule does not declare it.
 */
export function declared(
  styleId: string,
  selector: string,
  property: string,
  condition: string | null = null,
): string {
  const matches = rulesOf(styleId).filter(
    (rule) => rule.selector === selector && rule.condition === condition,
  );
  if (matches.length === 0) {
    throw new Error(`#${styleId} has no rule "${selector}" under ${condition ?? 'top level'}`);
  }
  return matches.map((rule) => rule.style.getPropertyValue(property)).filter(Boolean).pop() ?? '';
}
