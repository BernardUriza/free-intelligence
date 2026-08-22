'use client';

/**
 * fi-glass · the trail back out of a workspace detail.
 *
 * `AgentWorkspaceShell` has no header slot to hang this on — checked before
 * writing it (Art. 6) — so it is a primitive rather than a shell prop.
 *
 * A `<nav>` with an accessible name, and the last crumb marked
 * `aria-current="page"`: that is what tells a screen reader which one is where
 * you already are, instead of announcing every crumb as an equal link.
 */

import { Fragment, useEffect, type ReactNode } from 'react';
import { ensureTouchTargetStyle } from '../shell/touchTarget';
import { withTouchTarget } from '../shell/touchTarget';
import { FI_BREADCRUMB_CLASS, useResourceStyle } from './resourceStyle';

export interface BreadcrumbCrumb {
  label: string;
  /** A crumb without `href` and without `onClick` is inert — the current page. */
  href?: string;
  onClick?: () => void;
}

export interface WorkspaceBreadcrumbProps {
  crumbs: BreadcrumbCrumb[];
  /** Rendered between crumbs. Default "/". */
  separator?: ReactNode;
  ariaLabel: string;
  className?: string;
}

export function WorkspaceBreadcrumb({
  crumbs,
  separator = '/',
  ariaLabel,
  className,
}: WorkspaceBreadcrumbProps) {
  useResourceStyle();
  // The crumbs compose the framework minimum, so its sheet must be present.
  useEffect(() => ensureTouchTargetStyle(), []);
  return (
    <nav
      className={className ? `${FI_BREADCRUMB_CLASS} ${className}` : FI_BREADCRUMB_CLASS}
      aria-label={ariaLabel}
    >
      {crumbs.map((crumb, i) => {
        const last = i === crumbs.length - 1;
        return (
          <Fragment key={i}>
            {i > 0 && <span aria-hidden="true">{separator}</span>}
            {crumb.href ? (
              <a
                className={withTouchTarget()}
                href={crumb.href}
                onClick={crumb.onClick}
                aria-current={last ? 'page' : undefined}
              >
                {crumb.label}
              </a>
            ) : crumb.onClick ? (
              <button
                type="button"
                className={withTouchTarget()}
                onClick={crumb.onClick}
                aria-current={last ? 'page' : undefined}
              >
                {crumb.label}
              </button>
            ) : (
              <span aria-current={last ? 'page' : undefined}>{crumb.label}</span>
            )}
          </Fragment>
        );
      })}
    </nav>
  );
}
