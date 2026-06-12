export type SourceState =
  | 'LIVE API'
  | 'MOCK FALLBACK'
  | 'STARTING'
  | 'STREAMING'
  | 'ERROR'
  | 'IDLE';

const SOURCE_CLASS: Record<SourceState, string> = {
  'LIVE API': 'fi-badge fi-badge--approved',
  'MOCK FALLBACK': 'fi-badge fi-badge--vetoed',
  STARTING: 'fi-badge fi-badge--provenance',
  STREAMING: 'fi-badge fi-badge--band',
  ERROR: 'fi-badge fi-badge--vetoed',
  IDLE: 'fi-badge fi-badge--local',
};

export function SourceBadge({ state }: { state: SourceState }) {
  return <span className={SOURCE_CLASS[state]}>{state}</span>;
}

export function TransportBadge({ transport }: { transport: 'local' | 'band' }) {
  return transport === 'band' ? (
    <span className="fi-badge fi-badge--band">LIVE BAND</span>
  ) : (
    <span className="fi-badge fi-badge--local">LOCAL</span>
  );
}
