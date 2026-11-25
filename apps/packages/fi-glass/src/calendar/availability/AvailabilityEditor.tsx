'use client';

import { useId, useState, type ComponentType, type KeyboardEvent } from 'react';
import { ExceptionsTab } from './ExceptionsTab';
import { PreviewTab } from './PreviewTab';
import { RulesTab } from './RulesTab';
import { TemplatesTab } from './TemplatesTab';
import { WeeklyTab } from './WeeklyTab';
import type { AvailabilityTabProps } from './tab';

export type AvailabilityTab = 'weekly' | 'exceptions' | 'rules' | 'templates' | 'preview';

const TABS: Record<AvailabilityTab, { label: string; Panel: ComponentType<AvailabilityTabProps> }> = {
  weekly: { label: 'Semanal', Panel: WeeklyTab },
  exceptions: { label: 'Excepciones', Panel: ExceptionsTab },
  rules: { label: 'Reglas', Panel: RulesTab },
  templates: { label: 'Plantillas', Panel: TemplatesTab },
  preview: { label: 'Vista previa', Panel: PreviewTab },
};

const ALL_TABS = Object.keys(TABS) as AvailabilityTab[];
const ARROW_STEP: Record<string, number> = { ArrowRight: 1, ArrowLeft: -1 };

export interface AvailabilityEditorProps extends AvailabilityTabProps {
  tabs?: AvailabilityTab[];
  theme?: 'dark' | 'light';
}

export function AvailabilityEditor({ form, disabled, tabs = ALL_TABS, theme = 'dark' }: AvailabilityEditorProps) {
  const [active, setActive] = useState(tabs[0]);
  const id = useId();
  const tabId = (tab: AvailabilityTab) => `${id}-${tab}`;
  const { Panel } = TABS[active];

  const moveWithArrows = (event: KeyboardEvent) => {
    const step = ARROW_STEP[event.key];
    if (!step) return;
    event.preventDefault();
    const next = tabs[(tabs.indexOf(active) + step + tabs.length) % tabs.length];
    setActive(next);
    document.getElementById(tabId(next))?.focus();
  };

  return (
    <div className="fi-availability" data-theme={theme}>
      <div className="fi-availability-tabs" role="tablist" onKeyDown={moveWithArrows}>
        {tabs.map((tab) => (
          <button
            key={tab}
            id={tabId(tab)}
            type="button"
            role="tab"
            className="fi-availability-tab"
            aria-selected={tab === active}
            aria-controls={`${id}-panel`}
            tabIndex={tab === active ? 0 : -1}
            onClick={() => setActive(tab)}
          >
            {TABS[tab].label}
          </button>
        ))}
      </div>
      <div id={`${id}-panel`} className="fi-availability-panel" role="tabpanel" aria-labelledby={tabId(active)}>
        <Panel form={form} disabled={disabled} />
      </div>
    </div>
  );
}
