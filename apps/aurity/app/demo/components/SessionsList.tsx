import Link from 'next/link';
import { Database, ArrowRight } from 'lucide-react';

import type { DemoSession } from '../types';
import { getTypeBadgeClass } from '../constants';

interface SessionsListProps {
  sessions: DemoSession[];
}

export function SessionsList({ sessions }: SessionsListProps) {
  if (sessions.length === 0) return null;

  return (
    <section className="demo-sessions">
      <h2 className="demo-sessions-title">
        <Database className="demo-icon-sm fi-text-purple" />
        Loaded Sessions ({sessions.length})
      </h2>
      <div className="demo-sessions-list">
        {sessions.map((session) => (
          <div key={session.id} className="demo-session-card">
            <div className="demo-session-row">
              <div className="demo-session-body">
                <div className="demo-session-header">
                  <span className={`demo-session-badge ${getTypeBadgeClass(session.type)}`}>
                    {session.type.toUpperCase()}
                  </span>
                  <h3 className="demo-session-name">{session.title}</h3>
                </div>
                <p className="demo-session-desc">{session.description}</p>
                <div className="demo-session-meta">
                  <span>{session.eventCount} events</span>
                  <span>ID: {session.id}</span>
                  <span>Created: {new Date(session.created_at).toLocaleString()}</span>
                </div>
              </div>
              <Link
                href={`/viewer/${session.id}?index=0`}
                className="demo-session-view-link"
              >
                View
                <ArrowRight className="demo-icon-xs" />
              </Link>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
