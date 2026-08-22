// fi-glass · resource workspace — the anatomy of a resource seen as a PAGE.
//
// An INDEX (header + search + card grid) and a DETAIL (main column + a rail of
// panels, with a capacity meter and document cards). og118 renders its Projects
// with these; fi-glass does not know that word and must never learn it — no
// `projectCount`, no `newProjectLabel`, no copy of any kind. Every string, every
// control and every formatted date arrives from the consumer through a slot.
//
// Also importable via `fi-glass/resource`.

export {
  ResourceIndexHeader,
  type ResourceIndexHeaderProps,
} from './ResourceIndexHeader';

export {
  ResourceSearchInput,
  filterByQuery,
  type ResourceSearchInputProps,
} from './ResourceSearchInput';

export {
  ResourceCard,
  ResourceCardGrid,
  type ResourceCardProps,
  type ResourceCardGridProps,
} from './ResourceCardGrid';

export {
  WorkspaceDetailLayout,
  type WorkspaceDetailLayoutProps,
} from './WorkspaceDetailLayout';

export {
  RailPanel,
  RailPanelStack,
  type RailPanelProps,
  type RailPanelStackProps,
} from './RailPanel';

export { CapacityMeter, type CapacityMeterProps } from './CapacityMeter';

export {
  DocCard,
  DocCardGrid,
  type DocCardProps,
  type DocCardGridProps,
} from './DocCard';

export {
  WorkspaceBreadcrumb,
  type BreadcrumbCrumb,
  type WorkspaceBreadcrumbProps,
} from './WorkspaceBreadcrumb';

export {
  FI_INDEX_HEADER_CLASS,
  FI_INDEX_TITLE_CLASS,
  FI_INDEX_ACTIONS_CLASS,
  FI_SEARCH_CLASS,
  FI_CARD_GRID_CLASS,
  FI_CARD_CLASS,
  FI_CARD_TITLE_CLASS,
  FI_CARD_DESC_CLASS,
  FI_CARD_META_CLASS,
  FI_DETAIL_CLASS,
  FI_DETAIL_MAIN_CLASS,
  FI_DETAIL_RAIL_CLASS,
  FI_RAIL_STACK_CLASS,
  FI_RAIL_PANEL_CLASS,
  FI_RAIL_PANEL_HEAD_CLASS,
  FI_RAIL_PANEL_TITLE_CLASS,
  FI_METER_CLASS,
  FI_METER_TRACK_CLASS,
  FI_METER_FILL_CLASS,
  FI_METER_LABEL_CLASS,
  FI_DOC_GRID_CLASS,
  FI_DOC_CARD_CLASS,
  FI_DOC_CARD_TITLE_CLASS,
  FI_DOC_CARD_META_CLASS,
  FI_DOC_CARD_BADGE_CLASS,
  FI_BREADCRUMB_CLASS,
  ensureResourceStyle,
  useResourceStyle,
} from './resourceStyle';
