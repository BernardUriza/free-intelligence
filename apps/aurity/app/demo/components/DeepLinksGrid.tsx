import Link from 'next/link';
import { Play, ArrowRight } from 'lucide-react';

import { DEEP_LINKS } from '../constants';

export function DeepLinksGrid() {
  return (
    <section>
      <h2 className="demo-features-title">
        <Play className="demo-icon-sm fi-text-success" />
        Explore Features
      </h2>
      <div className="demo-features-grid">
        {DEEP_LINKS.map((link) => {
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`demo-feature-card ${link.cardClass}`}
            >
              <div className="demo-feature-row">
                <div className={`demo-feature-icon-wrap ${link.cardClass}`}>
                  <Icon className={`demo-icon-sm ${link.color}`} />
                </div>
                <div>
                  <h3 className={`demo-feature-label ${link.color}`}>{link.label}</h3>
                  <p className="fi-subtitle">{link.description}</p>
                </div>
                <ArrowRight className={`demo-feature-arrow ${link.color}`} />
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
