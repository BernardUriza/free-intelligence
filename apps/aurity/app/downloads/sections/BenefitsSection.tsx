import { BENEFITS } from '../constants';

export function BenefitsSection() {
  return (
    <section className="dl-benefits-section">
      <div className="dl-section-container-wide">
        <h2 className="dl-section-title-center">Por qué los médicos eligen Aurity</h2>
        <div className="dl-benefits-grid">
          {BENEFITS.map((benefit) => (
            <div key={benefit.title} className="dl-benefit-card">
              <div className="dl-benefit-header">
                <div className="dl-benefit-icon-box">
                  <benefit.icon className="dl-benefit-icon" />
                </div>
                <span className="dl-benefit-stat">{benefit.stat}</span>
              </div>
              <h3 className="dl-benefit-title">{benefit.title}</h3>
              <p className="dl-benefit-text">{benefit.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
