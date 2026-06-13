import type { CampaignPacket, EvidenceBrief } from '@/lib/activist-api';

export function CampaignPacketCard({
  packet,
  evidence,
}: {
  packet: CampaignPacket;
  evidence: EvidenceBrief;
}) {
  // Token-colored markers, not emojis — ui.md icon rule.
  const items: Array<[string, string]> = [
    ['var(--fi-evidence)', `Evidence brief — ${evidence.claims_count ?? 0} claims, ${evidence.sources_count ?? 0} sources with provenance tiers`],
    ['var(--fi-accent)', `Outreach pack — ${packet.outreach_assets_count ?? 0} community-language assets`],
    ['var(--fi-accent)', `Task board — ${packet.volunteer_tasks_count ?? 0} volunteer actions, lawful + nonviolent`],
    ['var(--fi-approved)', `Safety audit log — ${packet.provenance_items_count ?? 0} provenance items; vetoes included, not just approvals`],
  ];
  return (
    <div className="fi-glass-panel p-4 space-y-2">
      <p className="panel-title">Campaign Packet</p>
      <p className="text-sm font-semibold">{packet.title}</p>
      <p className="text-xs" style={{ color: 'var(--fi-muted)' }}>{packet.summary}</p>
      <ul className="text-sm space-y-1.5" style={{ color: 'var(--fi-muted)' }}>
        {items.map(([color, text]) => (
          <li key={text} className="flex items-start gap-2">
            <span style={{ color }}>▪</span>
            <span>{text}</span>
          </li>
        ))}
      </ul>
      <p className="text-xs pt-1" style={{ color: 'var(--fi-faint)' }}>
        Humans hold the send button — the system assembles, it never publishes.
      </p>
    </div>
  );
}
