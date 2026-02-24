import { Heart, Lock, Users, Globe } from 'lucide-react';

export function PhilosophySection() {
  return (
    <section className="dl-philosophy-section">
      <div className="dl-section-container">
        {/* Section Header */}
        <div className="dl-section-header">
          <div className="dl-section-badge">
            <Heart className="dl-icon-sm" />
            Nuestra Filosofía
          </div>
          <h2 className="dl-section-title">Free Intelligence</h2>
          <p className="dl-section-subtitle">
            Creemos que la inteligencia artificial médica debe ser libre, privada y accesible para
            todos.
          </p>
        </div>

        {/* Philosophy Cards */}
        <div className="dl-philosophy-grid">
          <div className="dl-feature-card">
            <div className="dl-feature-icon-box">
              <Lock className="dl-feature-icon" />
            </div>
            <h3 className="dl-feature-title">Soberanía de Datos</h3>
            <p className="dl-feature-text">
              Tus datos clínicos son tuyos. No los vendemos, no los analizamos, no los compartimos.
              Corren en <strong className="dl-feature-emphasis">tu hardware</strong>, bajo{' '}
              <strong className="dl-feature-emphasis">tu control</strong>.
            </p>
          </div>

          <div className="dl-feature-card">
            <div className="dl-feature-icon-box">
              <Users className="dl-feature-icon" />
            </div>
            <h3 className="dl-feature-title">IA para Todos</h3>
            <p className="dl-feature-text">
              La tecnología médica avanzada no debería ser exclusiva de grandes hospitales. Cualquier
              consultorio merece herramientas de{' '}
              <strong className="dl-feature-emphasis">clase mundial</strong>.
            </p>
          </div>

          <div className="dl-feature-card">
            <div className="dl-feature-icon-box">
              <Globe className="dl-feature-icon" />
            </div>
            <h3 className="dl-feature-title">Sin Dependencias</h3>
            <p className="dl-feature-text">
              Sin internet, sin servidores externos, sin suscripciones mensuales. Aurity funciona
              donde tú trabajes,{' '}
              <strong className="dl-feature-emphasis">siempre disponible</strong>.
            </p>
          </div>
        </div>

        {/* Bottom Statement */}
        <div className="dl-philosophy-footer">
          <p className="dl-philosophy-quote">
            &ldquo;La privacidad del paciente no es una feature premium. Es un derecho
            fundamental.&rdquo;
          </p>
        </div>
      </div>
    </section>
  );
}
