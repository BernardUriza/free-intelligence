import * as react from 'react';
import { ReactNode } from 'react';

interface ResourceIndexHeaderProps {
    /** A string is wrapped in the title slot; a node is used as-is (branded markup). */
    title: ReactNode;
    /** Sort affordance (a select, a menu trigger) — rendered before the CTA. */
    sortSlot?: ReactNode;
    /** The primary call to action (e.g. "New …"). */
    actionSlot?: ReactNode;
    className?: string;
}
declare function ResourceIndexHeader({ title, sortSlot, actionSlot, className, }: ResourceIndexHeaderProps): react.JSX.Element;

interface ResourceSearchInputProps {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    /** Required: a search box with no accessible name is unusable by a screen reader. */
    ariaLabel: string;
    className?: string;
}
declare function ResourceSearchInput({ value, onChange, placeholder, ariaLabel, className, }: ResourceSearchInputProps): react.JSX.Element;
/**
 * Case- and accent-insensitive substring match over the fields a consumer names.
 *
 * Accent folding is not a nicety here: typing "papeleria" must find "Papelería",
 * and a Spanish-speaking user on a phone keyboard routinely omits the accent.
 * An empty query matches everything rather than nothing.
 */
declare function filterByQuery<T>(items: T[], query: string, fields: (item: T) => (string | undefined)[]): T[];

interface ResourceCardProps {
    title: string;
    /** Clamped to three lines. Omit (or empty) and the row simply is not rendered. */
    description?: string;
    /** Already-formatted, e.g. "Updated 6 days ago" — fi-glass does no i18n or relative time. */
    meta?: ReactNode;
    /** Renders a real anchor. Without it the card is a button. */
    href?: string;
    onClick?: () => void;
    className?: string;
}
declare function ResourceCard({ title, description, meta, href, onClick, className, }: ResourceCardProps): react.JSX.Element;
interface ResourceCardGridProps {
    /** One `<li>` per child. Pass {@link ResourceCard}s. */
    children: ReactNode[];
    /** Rendered INSTEAD of the grid when there are no children. */
    emptyState?: ReactNode;
    /** Required: the list needs a name for the same reason the search box does. */
    ariaLabel: string;
    className?: string;
}
declare function ResourceCardGrid({ children, emptyState, ariaLabel, className, }: ResourceCardGridProps): react.JSX.Element;

interface WorkspaceDetailLayoutProps {
    children: ReactNode;
    /** The rail's content. Omit for a single-column workspace. */
    rail?: ReactNode;
    /** Rail width on desktop (number → px). Default 352. */
    railWidth?: number | string;
    /** Accessible label for the rail's complementary landmark. */
    railLabel?: string;
    className?: string;
}
declare function WorkspaceDetailLayout({ children, rail, railWidth, railLabel, className, }: WorkspaceDetailLayoutProps): react.JSX.Element;

interface RailPanelProps {
    /** A string is wrapped in the title slot; a node is used as-is. */
    title: ReactNode;
    children?: ReactNode;
    /** Controls rendered at the end of the head row (e.g. add / search). */
    actionSlot?: ReactNode;
    className?: string;
}
declare function RailPanel({ title, children, actionSlot, className }: RailPanelProps): react.JSX.Element;
interface RailPanelStackProps {
    children: ReactNode;
    className?: string;
}
declare function RailPanelStack({ children, className }: RailPanelStackProps): react.JSX.Element;

interface CapacityMeterProps {
    used: number;
    /** The ceiling, or `null`/`undefined` for no ceiling — the bar is then omitted. */
    max?: number | null;
    /**
     * Renders the text. Receives the computed percentage, or `null` when unbounded
     * — so the consumer writes its own words ("40 documents", "no limit") and
     * fi-glass never ships a language.
     */
    label: (percent: number | null) => ReactNode;
    className?: string;
}
declare function CapacityMeter({ used, max, label, className }: CapacityMeterProps): react.JSX.Element;

interface DocCardProps {
    title: string;
    /** Already formatted, e.g. "67 lines" / "4 chunks". */
    meta?: ReactNode;
    /** Short type marker, e.g. "TEXT". Rendered uppercase by the stylesheet. */
    badge?: string;
    onClick?: () => void;
    className?: string;
}
declare function DocCard({ title, meta, badge, onClick, className }: DocCardProps): react.JSX.Element;
interface DocCardGridProps {
    children: ReactNode[];
    emptyState?: ReactNode;
    ariaLabel: string;
    className?: string;
}
declare function DocCardGrid({ children, emptyState, ariaLabel, className }: DocCardGridProps): react.JSX.Element;

interface BreadcrumbCrumb {
    label: string;
    /** A crumb without `href` and without `onClick` is inert — the current page. */
    href?: string;
    onClick?: () => void;
}
interface WorkspaceBreadcrumbProps {
    crumbs: BreadcrumbCrumb[];
    /** Rendered between crumbs. Default "/". */
    separator?: ReactNode;
    ariaLabel: string;
    className?: string;
}
declare function WorkspaceBreadcrumb({ crumbs, separator, ariaLabel, className, }: WorkspaceBreadcrumbProps): react.JSX.Element;

declare const FI_INDEX_HEADER_CLASS = "fi-resource-index-header";
declare const FI_INDEX_TITLE_CLASS = "fi-resource-index-title";
declare const FI_INDEX_ACTIONS_CLASS = "fi-resource-index-actions";
declare const FI_SEARCH_CLASS = "fi-resource-search";
declare const FI_CARD_GRID_CLASS = "fi-resource-card-grid";
declare const FI_CARD_CLASS = "fi-resource-card";
declare const FI_CARD_TITLE_CLASS = "fi-resource-card-title";
declare const FI_CARD_DESC_CLASS = "fi-resource-card-desc";
declare const FI_CARD_META_CLASS = "fi-resource-card-meta";
declare const FI_DETAIL_CLASS = "fi-workspace-detail";
declare const FI_DETAIL_MAIN_CLASS = "fi-workspace-main";
declare const FI_DETAIL_RAIL_CLASS = "fi-workspace-rail";
declare const FI_RAIL_STACK_CLASS = "fi-rail-stack";
declare const FI_RAIL_PANEL_CLASS = "fi-rail-panel";
declare const FI_RAIL_PANEL_HEAD_CLASS = "fi-rail-panel-head";
declare const FI_RAIL_PANEL_TITLE_CLASS = "fi-rail-panel-title";
declare const FI_METER_CLASS = "fi-capacity-meter";
declare const FI_METER_TRACK_CLASS = "fi-capacity-meter-track";
declare const FI_METER_FILL_CLASS = "fi-capacity-meter-fill";
declare const FI_METER_LABEL_CLASS = "fi-capacity-meter-label";
declare const FI_DOC_GRID_CLASS = "fi-doc-grid";
declare const FI_DOC_CARD_CLASS = "fi-doc-card";
declare const FI_DOC_CARD_TITLE_CLASS = "fi-doc-card-title";
declare const FI_DOC_CARD_META_CLASS = "fi-doc-card-meta";
declare const FI_DOC_CARD_BADGE_CLASS = "fi-doc-card-badge";
declare const FI_BREADCRUMB_CLASS = "fi-workspace-breadcrumb";
/** Inject the idempotent resource-workspace stylesheet (no-op on the server / if already present). */
declare function ensureResourceStyle(): void;
/** Ensure the resource-workspace stylesheet is present for the lifetime of the component. */
declare function useResourceStyle(): void;

export { type BreadcrumbCrumb, CapacityMeter, type CapacityMeterProps, DocCard, DocCardGrid, type DocCardGridProps, type DocCardProps, FI_BREADCRUMB_CLASS, FI_CARD_CLASS, FI_CARD_DESC_CLASS, FI_CARD_GRID_CLASS, FI_CARD_META_CLASS, FI_CARD_TITLE_CLASS, FI_DETAIL_CLASS, FI_DETAIL_MAIN_CLASS, FI_DETAIL_RAIL_CLASS, FI_DOC_CARD_BADGE_CLASS, FI_DOC_CARD_CLASS, FI_DOC_CARD_META_CLASS, FI_DOC_CARD_TITLE_CLASS, FI_DOC_GRID_CLASS, FI_INDEX_ACTIONS_CLASS, FI_INDEX_HEADER_CLASS, FI_INDEX_TITLE_CLASS, FI_METER_CLASS, FI_METER_FILL_CLASS, FI_METER_LABEL_CLASS, FI_METER_TRACK_CLASS, FI_RAIL_PANEL_CLASS, FI_RAIL_PANEL_HEAD_CLASS, FI_RAIL_PANEL_TITLE_CLASS, FI_RAIL_STACK_CLASS, FI_SEARCH_CLASS, RailPanel, type RailPanelProps, RailPanelStack, type RailPanelStackProps, ResourceCard, ResourceCardGrid, type ResourceCardGridProps, type ResourceCardProps, ResourceIndexHeader, type ResourceIndexHeaderProps, ResourceSearchInput, type ResourceSearchInputProps, WorkspaceBreadcrumb, type WorkspaceBreadcrumbProps, WorkspaceDetailLayout, type WorkspaceDetailLayoutProps, ensureResourceStyle, filterByQuery, useResourceStyle };
