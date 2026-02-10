'use client';

import { Stethoscope, Syringe, Microscope, ClipboardList } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface ServiceItem {
  icon: LucideIcon;
  name: string;
  description: string;
}

interface FeaturedServicesWidgetProps {
  services?: ServiceItem[];
  clinicName?: string;
}

const defaultServices: ServiceItem[] = [
  { icon: Stethoscope, name: 'Consulta General', description: 'Atención médica integral' },
  { icon: Syringe, name: 'Vacunación', description: 'Esquema completo' },
  { icon: Microscope, name: 'Laboratorio', description: 'Resultados rápidos' },
  { icon: ClipboardList, name: 'Check-up', description: 'Evaluación preventiva' },
];

export function FeaturedServicesWidget({
  services = defaultServices,
  clinicName = 'Nuestra Clínica',
}: FeaturedServicesWidgetProps) {
  return (
    <div className="wgt-services-card">
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
            className="wgt-service-item"
          >
            <div className="mb-2 sm:mb-4 text-emerald-400">
              <service.icon style={{ width: 'clamp(3rem, 8vw, 6rem)', height: 'clamp(3rem, 8vw, 6rem)' }} strokeWidth={1.5} />
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
          Atención de calidad - Horario extendido
        </p>
      </div>
    </div>
  );
}
