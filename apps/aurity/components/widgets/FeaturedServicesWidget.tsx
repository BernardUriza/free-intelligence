'use client';

interface ServiceItem {
  icon: string;
  name: string;
  description: string;
}

interface FeaturedServicesWidgetProps {
  services?: ServiceItem[];
  clinicName?: string;
}

const defaultServices: ServiceItem[] = [
  { icon: '🩺', name: 'Consulta General', description: 'Atención médica integral' },
  { icon: '💉', name: 'Vacunación', description: 'Esquema completo' },
  { icon: '🔬', name: 'Laboratorio', description: 'Resultados rápidos' },
  { icon: '📋', name: 'Check-up', description: 'Evaluación preventiva' },
];

export function FeaturedServicesWidget({
  services = defaultServices,
  clinicName = 'Nuestra Clínica',
}: FeaturedServicesWidgetProps) {
  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-900/80 to-slate-950/80 border border-slate-700/40 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8">
      <div className="text-center mb-4 sm:mb-6 lg:mb-8 flex-shrink-0">
        <h2 className="font-bold text-white mb-2" style={{ fontSize: 'clamp(1.5rem, 3.5vw, 3.5rem)' }}>
          Nuestros Servicios
        </h2>
        <p className="text-slate-400" style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.5rem)' }}>
          {clinicName}
        </p>
      </div>

      <div className="flex-1 grid grid-cols-2 gap-3 sm:gap-4 lg:gap-6 min-h-0 content-center">
        {services.slice(0, 4).map((service, index) => (
          <div
            key={index}
            className="flex flex-col items-center justify-center bg-slate-800/40 border border-slate-700/40 rounded-xl p-4 sm:p-6 lg:p-8 transition-transform hover:scale-105"
          >
            <div className="mb-2 sm:mb-4" style={{ fontSize: 'clamp(3rem, 8vw, 8rem)' }}>
              {service.icon}
            </div>
            <h3 className="font-bold text-white text-center mb-1 sm:mb-2" style={{ fontSize: 'clamp(1rem, 2vw, 2rem)' }}>
              {service.name}
            </h3>
            <p className="text-slate-400 text-center" style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}>
              {service.description}
            </p>
          </div>
        ))}
      </div>

      <div className="flex-shrink-0 mt-4 sm:mt-6 pt-4 fi-border-top/30 text-center">
        <p className="fi-text-success" style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.5rem)' }}>
          ✓ Atención de calidad • Horario extendido
        </p>
      </div>
    </div>
  );
}
