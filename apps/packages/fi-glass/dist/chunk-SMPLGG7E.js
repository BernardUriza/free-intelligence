'use client';

import {
  FI_TOUCH_QUERY
} from "./chunk-HJ2CVNCV.js";

// src/shell/touchTarget.ts
import { useInsertionEffect } from "react";
var FI_TOUCH_TARGET_CLASS = "fi-touch-target";
var TOUCH_TARGET_STYLE_ID = "fi-touch-target-style";
function ensureTouchTargetStyle() {
  if (typeof document === "undefined") return;
  if (document.getElementById(TOUCH_TARGET_STYLE_ID)) return;
  const el = document.createElement("style");
  el.id = TOUCH_TARGET_STYLE_ID;
  el.textContent = `
    @media ${FI_TOUCH_QUERY} {
      .${FI_TOUCH_TARGET_CLASS} {
        min-width: var(--fi-touch-target, 44px);
        min-height: var(--fi-touch-target, 44px);
        box-sizing: border-box;
      }
      :where(.${FI_TOUCH_TARGET_CLASS}) {
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
    }
  `;
  document.head.appendChild(el);
}
function useTouchTargetStyle() {
  useInsertionEffect(() => {
    ensureTouchTargetStyle();
  }, []);
}
function withTouchTarget(className) {
  return className ? `${FI_TOUCH_TARGET_CLASS} ${className}` : FI_TOUCH_TARGET_CLASS;
}

export {
  FI_TOUCH_TARGET_CLASS,
  ensureTouchTargetStyle,
  useTouchTargetStyle,
  withTouchTarget
};
//# sourceMappingURL=chunk-SMPLGG7E.js.map