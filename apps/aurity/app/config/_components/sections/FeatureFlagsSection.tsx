/**
 * FeatureFlagsSection
 *
 * Toggles for experimental features.
 * Renders from the FEATURE_FLAGS constant — add new flags in constants.ts.
 */

import { FEATURE_FLAGS } from '../constants';

export function FeatureFlagsSection() {
  return (
    <div className="cfg-section-card">
      <div className="cfg-section-header">
        <h2 className="fi-title">Feature Flags</h2>
        <p className="fi-subtitle">Activar/desactivar características experimentales</p>
      </div>
      <div className="cfg-section-body">
        {FEATURE_FLAGS.map((flag, idx) => {
          const isLast = idx === FEATURE_FLAGS.length - 1;
          return (
            <div
              key={flag.label}
              className={isLast ? 'fi-settings-row' : 'fi-settings-row-bordered'}
            >
              <div>
                <p className="cfg-setting-label">{flag.label}</p>
                <p className="fi-subtitle">{flag.description}</p>
              </div>
              <ToggleIndicator active={flag.active} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Co-located — visual-only toggle indicator
// ---------------------------------------------------------------------------

function ToggleIndicator({ active }: { active: boolean }) {
  if (active) {
    return (
      <div className="fi-flex-gap">
        <span className="cfg-toggle-label-active">Activo</span>
        <div className="cfg-toggle-on">
          <div className="cfg-toggle-knob-right" />
        </div>
      </div>
    );
  }

  return (
    <div className="fi-flex-gap">
      <span className="cfg-toggle-label-inactive">Inactivo</span>
      <div className="cfg-toggle-off">
        <div className="cfg-toggle-knob-left" />
      </div>
    </div>
  );
}
