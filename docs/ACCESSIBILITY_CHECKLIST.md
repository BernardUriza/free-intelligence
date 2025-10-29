# Accessibility Checklist (WCAG 2.1 AA)

**Card**: FI-UX-STR-001
**Standard**: WCAG 2.1 Level AA
**Owner**: Frontend Team
**Date**: 2025-10-29

---

## Overview

Free Intelligence targets **WCAG 2.1 Level AA** compliance. This checklist must be reviewed before each release.

---

## 1. Perceivable

### 1.1 Text Alternatives

- [ ] **1.1.1**: All images have meaningful `alt` attributes
  - Decorative images: `alt=""`
  - Functional images: describe purpose (e.g., `alt="Export session"`)
  - Complex images: link to long description

**Testing**: Disable images, verify content still understandable

---

### 1.2 Time-based Media

- [ ] **1.2.1**: Audio-only content has text transcript
- [ ] **1.2.2**: Video has captions
- [ ] **1.2.3**: Audio description for video (if needed)

**Current Status**: N/A (no video/audio in v1)

---

### 1.3 Adaptable

- [ ] **1.3.1**: Use semantic HTML (`<nav>`, `<main>`, `<article>`, `<section>`)
- [ ] **1.3.2**: Reading order follows visual order (test with Tab key)
- [ ] **1.3.3**: No info conveyed by sensory characteristics alone (e.g., "Click the green button")

**Example**:
```html
<!-- ✅ Good -->
<nav aria-label="Main navigation">
  <ul>
    <li><a href="/timeline">Timeline</a></li>
  </ul>
</nav>

<!-- ❌ Bad -->
<div class="navigation">
  <span onclick="navigate()">Timeline</span>
</div>
```

---

### 1.4 Distinguishable

- [ ] **1.4.1**: Color not sole indicator (use icons + text)
- [ ] **1.4.3**: Contrast ratio ≥4.5:1 (text), ≥3:1 (large text, UI components)
- [ ] **1.4.4**: Text resizable to 200% without loss of content
- [ ] **1.4.10**: Reflow at 320px width (no horizontal scroll)
- [ ] **1.4.11**: Non-text contrast ≥3:1 (buttons, inputs)
- [ ] **1.4.12**: Text spacing adjustable (line-height 1.5×, paragraph spacing 2×)
- [ ] **1.4.13**: Hover/focus content dismissible and persistent

**Color Palette** (Free Intelligence Dark Theme):
| Element | Color | Background | Ratio | Pass |
|---------|-------|------------|-------|------|
| Body text | `#f8fafc` (slate-50) | `#0f172a` (slate-900) | 17.4:1 | ✅ AAA |
| Links | `#60a5fa` (blue-400) | `#0f172a` | 8.1:1 | ✅ AAA |
| Disabled | `#64748b` (slate-500) | `#0f172a` | 4.6:1 | ✅ AA |
| Error | `#f87171` (red-400) | `#0f172a` | 5.9:1 | ✅ AA |
| Success | `#4ade80` (green-400) | `#0f172a` | 8.8:1 | ✅ AAA |

**Testing Tools**:
- Chrome DevTools → Lighthouse (Accessibility score)
- axe DevTools extension
- WebAIM Contrast Checker

---

## 2. Operable

### 2.1 Keyboard Accessible

- [ ] **2.1.1**: All functionality available via keyboard
- [ ] **2.1.2**: No keyboard trap (can Tab away)
- [ ] **2.1.4**: Single-key shortcuts don't conflict (use Cmd+key)

**Keyboard Shortcuts**:
| Action | Shortcut | Conflicts? |
|--------|----------|------------|
| New Session | `Cmd+N` | No (browser opens new window, but we capture first) |
| Search | `Cmd+K` | No |
| Pin/Unpin | `p` | OK (single key allowed when focus in Timeline) |
| Tag | `t` | OK |
| Export | `Cmd+E` | No |
| Verify | `Cmd+Shift+V` | No |

---

### 2.2 Enough Time

- [ ] **2.2.1**: Time limits adjustable (if any)
- [ ] **2.2.2**: Moving content can be paused (carousels, auto-scroll)

**Current Status**: No time limits or auto-moving content in v1

---

### 2.3 Seizures and Physical Reactions

- [ ] **2.3.1**: No flashing content >3 times per second

**Current Status**: No flashing animations

---

### 2.4 Navigable

- [ ] **2.4.1**: Skip to main content link
- [ ] **2.4.2**: Page has `<title>` describing topic
- [ ] **2.4.3**: Focus order follows meaningful sequence
- [ ] **2.4.4**: Link purpose clear from text (avoid "Click here")
- [ ] **2.4.5**: Multiple ways to find pages (nav + search)
- [ ] **2.4.6**: Headings and labels descriptive
- [ ] **2.4.7**: Focus indicator visible (outline, background change)

**Example**:
```tsx
// ✅ Good focus indicator
<button className="focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
  Export
</button>

// ❌ Bad (no visible focus)
<button className="focus:outline-none">
  Export
</button>
```

---

### 2.5 Input Modalities

- [ ] **2.5.1**: Pointer gestures have keyboard/single-tap alternative
- [ ] **2.5.2**: Pointer cancellation (can abort click by moving away)
- [ ] **2.5.3**: Label text matches accessible name
- [ ] **2.5.4**: Motion actuation can be disabled (shake to undo, etc.)

**Current Status**: No motion-based controls

---

## 3. Understandable

### 3.1 Readable

- [ ] **3.1.1**: Page language declared (`<html lang="en">`)
- [ ] **3.1.2**: Language changes marked (`<span lang="es">Hola</span>`)

---

### 3.2 Predictable

- [ ] **3.2.1**: Focus doesn't trigger context change
- [ ] **3.2.2**: Input doesn't trigger context change (unless warned)
- [ ] **3.2.3**: Navigation consistent across pages
- [ ] **3.2.4**: Components identified consistently (e.g., search always top-right)

---

### 3.3 Input Assistance

- [ ] **3.3.1**: Error messages describe issue ("Email invalid" not "Error")
- [ ] **3.3.2**: Labels or instructions for user input
- [ ] **3.3.3**: Error suggestions provided (when possible)
- [ ] **3.3.4**: Reversible actions (undo) or confirmation for legal/financial

**Example**:
```tsx
// ✅ Good error handling
<input
  type="email"
  aria-describedby="email-error"
  aria-invalid={hasError}
/>
{hasError && (
  <span id="email-error" role="alert">
    Email must include @ symbol (e.g., user@example.com)
  </span>
)}
```

---

## 4. Robust

### 4.1 Compatible

- [ ] **4.1.1**: Valid HTML (no duplicate IDs, closed tags)
- [ ] **4.1.2**: Name, role, value for UI components
- [ ] **4.1.3**: Status messages programmatically determinable

**ARIA Usage**:
```tsx
// Loading state
<div role="status" aria-live="polite">
  Loading session...
</div>

// Success notification
<div role="alert" aria-live="assertive">
  ✅ Session exported successfully
</div>

// Button with icon only
<button aria-label="Export session">
  <DownloadIcon />
</button>
```

---

## Testing Protocol

### **Automated Testing**

**Tools**:
1. **axe DevTools** (Chrome extension)
   - Run on every page
   - Fix all Critical + Serious issues
   - Document Moderate/Minor issues

2. **Lighthouse** (Chrome DevTools)
   - Target: Accessibility score ≥90
   - Run in CI on every PR

3. **axe-core** (Playwright integration)
   ```typescript
   import { injectAxe, checkA11y } from 'axe-playwright';

   test('Timeline page is accessible', async ({ page }) => {
     await page.goto('http://localhost:9000/timeline');
     await injectAxe(page);
     await checkA11y(page);
   });
   ```

---

### **Manual Testing**

**Keyboard Navigation** (10 min):
1. Unplug mouse
2. Navigate entire app with Tab/Shift+Tab
3. Activate all buttons with Enter/Space
4. Close modals with Esc
5. Use shortcuts (Cmd+K, etc.)

**Acceptance**: All functionality accessible, focus always visible

---

**Screen Reader** (15 min):
1. Install NVDA (Windows) or VoiceOver (Mac)
2. Navigate Timeline page
3. Create session
4. Export session
5. Verify session

**Acceptance**: All actions announced clearly, no confusing labels

---

**Color Blindness** (5 min):
1. Use Chrome DevTools → Rendering → Emulate vision deficiencies
2. Test Deuteranopia, Protanopia, Tritanopia
3. Verify info not conveyed by color alone

**Acceptance**: Status indicators use icons + text, not just color

---

**Zoom Test** (5 min):
1. Set browser zoom to 200%
2. Navigate app
3. Verify no horizontal scroll
4. Verify no content cut off

**Acceptance**: All content accessible at 200% zoom

---

## Common Issues & Fixes

### Issue 1: Low Contrast
**Problem**: Gray text on dark background (ratio 2.8:1)
**Fix**: Use `text-slate-100` instead of `text-slate-400`

### Issue 2: Missing Alt Text
**Problem**: `<img src="logo.png" />`
**Fix**: `<img src="logo.png" alt="Free Intelligence logo" />`

### Issue 3: Keyboard Trap in Modal
**Problem**: Tab goes outside modal
**Fix**: Use `focus-trap-react` or Radix UI Dialog

### Issue 4: Unclear Error Message
**Problem**: "Invalid input"
**Fix**: "Email must include @ symbol (e.g., user@example.com)"

### Issue 5: Icon-only Button
**Problem**: `<button><TrashIcon /></button>`
**Fix**: `<button aria-label="Delete session"><TrashIcon /></button>`

---

## CI Integration

**GitHub Actions** (`.github/workflows/a11y.yml`):
```yaml
name: Accessibility Tests

on: [pull_request]

jobs:
  a11y:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Install dependencies
        run: pnpm install

      - name: Build app
        run: pnpm build

      - name: Start app
        run: pnpm start &

      - name: Wait for app
        run: npx wait-on http://localhost:9000

      - name: Run Lighthouse
        run: |
          npm install -g @lhci/cli
          lhci autorun --collect.url=http://localhost:9000

      - name: Run axe tests
        run: pnpm test:a11y

      - name: Check results
        run: |
          if [ $(jq '.accessibility < 90' lighthouse-report.json) ]; then
            echo "❌ Accessibility score below 90"
            exit 1
          fi
```

---

## Sign-off

**Before Release**:
- [ ] All automated tests pass (axe + Lighthouse ≥90)
- [ ] Manual keyboard test completed
- [ ] Screen reader test completed
- [ ] Color blindness test completed
- [ ] Zoom test (200%) completed
- [ ] Accessibility champion approved

**Champion**: @ux-lead

---

## References

- **WCAG 2.1 AA**: https://www.w3.org/WAI/WCAG21/quickref/?currentsidebar=%23col_customize&levels=aa
- **axe DevTools**: https://www.deque.com/axe/devtools/
- **WebAIM**: https://webaim.org/resources/contrastchecker/
- **A11y Project**: https://www.a11yproject.com/checklist/

---

_"Accesibilidad no es opcional. Es respeto."_
