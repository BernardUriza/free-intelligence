import React, { useState } from 'react';
import { useAccessibility } from './AccessibilityContext';

interface ConsentFlowProps {
  onAccept: () => void;
  onDecline?: () => void;
}

export function ConsentFlow({ onAccept, onDecline }: ConsentFlowProps) {
  const [accepted, setAccepted] = useState(false);
  const [currentStep, setCurrentStep] = useState<'welcome' | 'details' | 'confirm'>('welcome');
  const { settings, speak } = useAccessibility();

  const handleAccept = () => {
    setAccepted(true);
    if (settings.enableTextToSpeech) {
      speak('Consentimiento aceptado');
    }
    onAccept();
  };

  const handleDecline = () => {
    if (settings.enableTextToSpeech) {
      speak('Consentimiento rechazado');
    }
    onDecline?.();
  };

  if (accepted) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 p-4">
        <div className="bg-slate-800 rounded-lg p-6 md:p-8 max-w-md text-center">
          <div className="text-4xl mb-4">✅</div>
          <h2 className="text-xl md:text-2xl font-bold mb-3">¡Consentimiento Aceptado!</h2>
          <p className="text-slate-300 mb-4">Gracias por entender cómo usamos tus datos de forma segura.</p>
          <p className="text-sm text-slate-400">Ahora puedes acceder a todas las funciones de Aurity.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-900 to-slate-800 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl">
        {/* Welcome Step */}
        {currentStep === 'welcome' && (
          <div className="bg-slate-800 rounded-lg p-6 md:p-8 border border-slate-700">
            <h1 className="text-2xl md:text-3xl font-bold mb-4">Bienvenido a Aurity</h1>
            <p className="text-slate-300 mb-6">
              Antes de continuar, necesitamos que entiendas cómo protegemos tu información médica.
            </p>
            <div className="bg-slate-700 rounded p-4 mb-6">
              <p className="text-sm text-slate-200">
                <strong>Lectura Fácil:</strong> Aurity es una app segura. Tus datos médicos están protegidos.
                Solo tú y los profesionales autorizados pueden verlos. Nunca compartimos datos sin tu permiso.
              </p>
            </div>
            <button
              onClick={() => {
                setCurrentStep('details');
                if (settings.enableTextToSpeech) {
                  speak('Detalles del consentimiento');
                }
              }}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-3 px-4 rounded-lg transition-colors text-lg"
            >
              Continuar
            </button>
          </div>
        )}

        {/* Details Step */}
        {currentStep === 'details' && (
          <div className="bg-slate-800 rounded-lg p-6 md:p-8 border border-slate-700">
            <h2 className="text-2xl font-bold mb-6">Lo que necesitas saber</h2>

            <div className="space-y-4 mb-6">
              {[
                {
                  title: '🔒 Seguridad',
                  desc: 'Tus datos están encriptados y almacenados localmente en tu dispositivo.',
                },
                {
                  title: '👤 Privacidad',
                  desc: 'Nadie puede acceder a tus datos sin tu permiso. Ni siquiera el servidor.',
                },
                {
                  title: '📊 Control',
                  desc: 'Puedes ver, descargar o borrar todos tus datos en cualquier momento.',
                },
                {
                  title: '✅ Transparencia',
                  desc: 'Te informaremos si tus datos se usan para investigación o análisis.',
                },
              ].map((item, idx) => (
                <div
                  key={idx}
                  className="bg-slate-700 rounded p-4 cursor-pointer hover:bg-slate-600 transition-colors"
                  onClick={() => {
                    if (settings.enableTextToSpeech) {
                      speak(`${item.title} ${item.desc}`);
                    }
                  }}
                >
                  <h3 className="font-semibold mb-1">{item.title}</h3>
                  <p className="text-sm text-slate-300">{item.desc}</p>
                </div>
              ))}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setCurrentStep('welcome')}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-white font-bold py-2 px-4 rounded-lg transition-colors"
              >
                Atrás
              </button>
              <button
                onClick={() => {
                  setCurrentStep('confirm');
                  if (settings.enableTextToSpeech) {
                    speak('Confirma tu consentimiento');
                  }
                }}
                className="flex-1 bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-lg transition-colors"
              >
                Continuar
              </button>
            </div>
          </div>
        )}

        {/* Confirm Step */}
        {currentStep === 'confirm' && (
          <div className="bg-slate-800 rounded-lg p-6 md:p-8 border border-slate-700">
            <h2 className="text-2xl font-bold mb-6">Confirma tu consentimiento</h2>

            <div className="bg-blue-900 border border-blue-700 rounded p-4 mb-6">
              <p className="text-sm mb-4">
                <strong>Entiendo que:</strong>
              </p>
              <ul className="text-sm space-y-2 text-slate-200">
                <li>✓ Mis datos médicos están protegidos con encriptación</li>
                <li>✓ Solo yo puedo acceder a mis datos</li>
                <li>✓ Puedo eliminar mis datos cuando quiera</li>
                <li>✓ Seré informado si mis datos se usan para investigación</li>
              </ul>
            </div>

            <label className="flex items-start gap-3 mb-6 p-3 bg-slate-700 rounded cursor-pointer hover:bg-slate-600 transition-colors">
              <input
                type="checkbox"
                checked={accepted}
                onChange={(e) => setAccepted(e.target.checked)}
                className="w-5 h-5 mt-1"
                aria-label="Acepto las condiciones"
              />
              <span className="text-sm">
                Acepto estas condiciones y entiendo cómo se protegen mis datos
              </span>
            </label>

            <div className="flex gap-3">
              <button
                onClick={() => setCurrentStep('details')}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-white font-bold py-3 px-4 rounded-lg transition-colors"
              >
                Atrás
              </button>
              <button
                onClick={handleDecline}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-white font-bold py-3 px-4 rounded-lg transition-colors"
              >
                Rechazar
              </button>
              <button
                onClick={handleAccept}
                disabled={!accepted}
                className={`flex-1 font-bold py-3 px-4 rounded-lg transition-colors ${
                  accepted
                    ? 'bg-green-600 hover:bg-green-700 text-white cursor-pointer'
                    : 'bg-slate-600 text-slate-400 cursor-not-allowed'
                }`}
              >
                Aceptar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
