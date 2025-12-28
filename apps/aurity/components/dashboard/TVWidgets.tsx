/**
 * TVWidgets - Reusable Widget Components for Waiting Room TV
 *
 * Card: FI-UI-FEAT-TVD-001, FI-TV-002
 * Based on 2025 healthcare digital signage best practices
 *
 * Research insights:
 * - Digital signage reduces perceived wait time by 35%
 * - Calming visuals (nature, meditation) reduce anxiety
 * - Interactive content (trivias, exercises) improve engagement
 * - Weather + time anchors patients to reality
 *
 * FI-TV-002: Smart Text Scaling
 * - Uses CSS clamp() for responsive font sizes
 * - Viewport units (vw, vh) for TV-optimized scaling
 * - Text legible from 3-10 meters distance
 * - Full-screen layouts that fill available space
 */

'use client';

import { useEffect, useState, useRef } from 'react';

// ============================================================================
// WEATHER WIDGET
// ============================================================================

interface WeatherWidgetProps {
  city?: string;
}

export function WeatherWidget({ city = 'Ciudad de México' }: WeatherWidgetProps) {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Mock weather data (in real app, would fetch from API)
  const weather = {
    temp: 22,
    condition: 'Soleado',
    icon: '☀️',
    humidity: 45,
  };

  const formattedTime = currentTime.toLocaleTimeString('es-MX', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  const formattedDate = currentTime.toLocaleDateString('es-MX', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  return (
    <div className="bg-gradient-to-br from-blue-950/40 to-cyan-950/40 border border-blue-600/40 rounded-xl p-6 backdrop-blur-sm">
      <div className="flex items-start justify-between">
        {/* Left: Time & Date */}
        <div>
          <div className="text-5xl font-bold text-white mb-2 font-mono">
            {formattedTime}
          </div>
          <div className="text-sm text-blue-300 capitalize">
            {formattedDate}
          </div>
        </div>

        {/* Right: Weather */}
        <div className="text-right">
          <div className="text-6xl mb-2">{weather.icon}</div>
          <div className="text-3xl font-bold text-white">{weather.temp}°C</div>
          <div className="text-sm text-blue-300">{weather.condition}</div>
          <div className="text-xs fi-text-primary/60 mt-1">
            Humedad: {weather.humidity}%
          </div>
        </div>
      </div>

      {/* City */}
      <div className="mt-4 pt-4 border-t border-blue-700/30">
        <div className="fi-flex-gap text-blue-300 text-sm">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
          </svg>
          <span>{city}</span>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// HEALTH TRIVIA WIDGET - Full Screen TV Optimized
// FI-TV-002: Smart text scaling with viewport units
// ============================================================================

interface HealthTriviaWidgetProps {
  question: string;
  options: string[];
  correctAnswer: number;
  explanation: string;
}

export function HealthTriviaWidget({
  question,
  options,
  correctAnswer,
  explanation,
}: HealthTriviaWidgetProps) {
  const [showAnswer, setShowAnswer] = useState(false);
  const [countdown, setCountdown] = useState(10);

  useEffect(() => {
    // Countdown timer
    const countdownTimer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          setShowAnswer(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(countdownTimer);
  }, []);

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-emerald-950/60 to-teal-950/40 border border-emerald-600/40 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8">
      {/* Header with Timer */}
      <div className="fi-flex-between mb-4 sm:mb-6 flex-shrink-0">
        <div className="flex items-center gap-3 sm:gap-4">
          <div
            className="bg-emerald-500/10 rounded-full p-3 sm:p-4"
            style={{ fontSize: 'clamp(2rem, 4vw, 4rem)' }}
          >
            🧠
          </div>
          <div>
            <h3
              className="font-bold text-emerald-300"
              style={{ fontSize: 'clamp(1.25rem, 2.5vw, 2.5rem)' }}
            >
              Trivia de Salud
            </h3>
            <p
              className="fi-text-success/60"
              style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}
            >
              ¿Cuánto sabes?
            </p>
          </div>
        </div>
        {/* Countdown Timer */}
        {!showAnswer && (
          <div className="fi-flex-gap">
            <div
              className="w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-emerald-500/20 border-2 border-emerald-500 flex items-center justify-center"
            >
              <span
                className="font-bold text-emerald-300"
                style={{ fontSize: 'clamp(1rem, 2vw, 2rem)' }}
              >
                {countdown}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Question - Large & Centered */}
      <div className="mb-4 sm:mb-6 flex-shrink-0">
        <p
          className="text-white font-medium leading-relaxed text-center"
          style={{
            fontSize: question.length > 100
              ? 'clamp(1rem, 2vw, 1.75rem)'
              : 'clamp(1.25rem, 2.5vw, 2.25rem)',
          }}
        >
          {question}
        </p>
      </div>

      {/* Options - Grid for TV */}
      <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 min-h-0 content-center">
        {options.map((option, index) => (
          <div
            key={index}
            className={`
              px-4 sm:px-6 py-3 sm:py-4 rounded-xl border-2 transition-all duration-500
              flex items-center gap-3 sm:gap-4
              ${showAnswer && index === correctAnswer
                ? 'bg-emerald-500/30 border-emerald-400 shadow-lg shadow-emerald-500/30 scale-105'
                : showAnswer
                ? 'bg-slate-900/30 border-slate-700 opacity-60'
                : 'bg-slate-900/30 border-slate-600 hover:border-emerald-600/50'
              }
            `}
          >
            <span
              className={`font-bold ${showAnswer && index === correctAnswer ? 'text-emerald-300' : 'fi-text-success'}`}
              style={{ fontSize: 'clamp(1.25rem, 2vw, 2rem)' }}
            >
              {String.fromCharCode(65 + index)}.
            </span>
            <span
              className="text-slate-200 flex-1"
              style={{ fontSize: 'clamp(0.9rem, 1.5vw, 1.5rem)' }}
            >
              {option}
            </span>
            {showAnswer && index === correctAnswer && (
              <svg
                className="w-6 h-6 sm:w-8 sm:h-8 fi-text-success flex-shrink-0"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            )}
          </div>
        ))}
      </div>

      {/* Explanation (revealed) */}
      {showAnswer && (
        <div className="flex-shrink-0 mt-4 sm:mt-6 p-4 sm:p-6 bg-emerald-900/30 border border-emerald-600/40 rounded-xl animate-fade-in">
          <p
            className="text-emerald-200 leading-relaxed text-center"
            style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.25rem)' }}
          >
            <span className="font-semibold text-emerald-300">✓ </span>
            {explanation}
          </p>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// BREATHING EXERCISE WIDGET - Full Screen TV Optimized
// FI-TV-002: Smart text scaling with viewport units
// ============================================================================

export function BreathingExerciseWidget() {
  const [phase, setPhase] = useState<'inhale' | 'hold' | 'exhale'>('inhale');
  const [count, setCount] = useState(4);
  const phaseRef = useRef<'inhale' | 'hold' | 'exhale'>(phase);

  useEffect(() => {
    phaseRef.current = phase; // Keep ref in sync with state
  }, [phase]);

  useEffect(() => {
    const timer = setInterval(() => {
      setCount(prev => {
        if (prev === 1) {
          // Switch phase
          setPhase(current => {
            if (current === 'inhale') return 'hold';
            if (current === 'hold') return 'exhale';
            return 'inhale';
          });
          // Return the appropriate count based on the current phase ref value
          return phaseRef.current === 'hold' ? 7 : 4;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const phaseConfig = {
    inhale: {
      label: 'Inhala profundamente',
      color: 'text-cyan-300',
      bgColor: 'bg-cyan-500/20',
      borderColor: 'border-cyan-500',
      glowColor: 'shadow-cyan-500/30',
      icon: '↑',
    },
    hold: {
      label: 'Sostén la respiración',
      color: 'text-purple-300',
      bgColor: 'bg-purple-500/20',
      borderColor: 'border-purple-500',
      glowColor: 'shadow-purple-500/30',
      icon: '⏸',
    },
    exhale: {
      label: 'Exhala lentamente',
      color: 'text-orange-300',
      bgColor: 'bg-orange-500/20',
      borderColor: 'border-orange-500',
      glowColor: 'shadow-orange-500/30',
      icon: '↓',
    },
  };

  const config = phaseConfig[phase];

  return (
    <div className="h-full flex flex-col items-center justify-center bg-gradient-to-br from-slate-950/80 to-slate-900/80 border border-slate-700 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8">
      {/* Header - TV Scaled */}
      <div className="text-center mb-4 sm:mb-6 lg:mb-8 flex-shrink-0">
        <div className="text-4xl sm:text-5xl lg:text-6xl mb-2">🧘</div>
        <h3
          className="font-bold text-white"
          style={{ fontSize: 'clamp(1.5rem, 3vw, 3rem)' }}
        >
          Ejercicio de Respiración
        </h3>
        <p
          className="text-slate-400 mt-1"
          style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.5rem)' }}
        >
          Técnica 4-7-8 para reducir ansiedad
        </p>
      </div>

      {/* Animated Circle - Large & Centered */}
      <div className="flex-1 flex items-center justify-center w-full min-h-0">
        <div
          className={`
            relative rounded-full
            ${config.bgColor} ${config.borderColor} border-4 sm:border-6 lg:border-8
            flex items-center justify-center
            transition-all duration-1000 ease-in-out
            shadow-2xl ${config.glowColor}
            ${phase === 'inhale' ? 'scale-110' : phase === 'exhale' ? 'scale-90' : 'scale-100'}
          `}
          style={{
            width: 'min(50vh, 50vw, 400px)',
            height: 'min(50vh, 50vw, 400px)',
          }}
        >
          <div className="text-center">
            {/* Giant Number */}
            <div
              className={`font-bold ${config.color} leading-none`}
              style={{ fontSize: 'clamp(4rem, 15vw, 12rem)' }}
            >
              {count}
            </div>
            {/* Arrow Icon */}
            <div
              className={`${config.color} mt-2`}
              style={{ fontSize: 'clamp(2rem, 6vw, 5rem)' }}
            >
              {config.icon}
            </div>
          </div>
        </div>
      </div>

      {/* Instructions - Large Text */}
      <div className="text-center mt-4 sm:mt-6 lg:mt-8 flex-shrink-0">
        <p
          className={`font-semibold ${config.color}`}
          style={{ fontSize: 'clamp(1.25rem, 3vw, 3rem)' }}
        >
          {config.label}
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// DAILY TIP WIDGET - Full Screen TV Optimized
// FI-TV-002: Smart text scaling with viewport units
// ============================================================================

interface DailyTipWidgetProps {
  tip: string;
  category: 'nutrition' | 'exercise' | 'mental_health' | 'prevention';
  generatedBy?: 'FI' | 'static';
}

export function DailyTipWidget({ tip, category, generatedBy = 'static' }: DailyTipWidgetProps) {
  const categoryConfig = {
    nutrition: {
      icon: '🥗',
      label: 'Nutrición',
      color: 'text-green-300',
      bgColor: 'bg-gradient-to-br from-green-950/60 to-emerald-950/40',
      borderColor: 'border-green-600/40',
      accentBg: 'bg-green-500/10',
    },
    exercise: {
      icon: '🏃',
      label: 'Actividad Física',
      color: 'text-blue-300',
      bgColor: 'bg-gradient-to-br from-blue-950/60 to-cyan-950/40',
      borderColor: 'border-blue-600/40',
      accentBg: 'bg-blue-500/10',
    },
    mental_health: {
      icon: '🧠',
      label: 'Salud Mental',
      color: 'text-purple-300',
      bgColor: 'bg-gradient-to-br from-purple-950/60 to-violet-950/40',
      borderColor: 'border-purple-600/40',
      accentBg: 'bg-purple-500/10',
    },
    prevention: {
      icon: '🛡️',
      label: 'Prevención',
      color: 'text-orange-300',
      bgColor: 'bg-gradient-to-br from-orange-950/60 to-amber-950/40',
      borderColor: 'border-orange-600/40',
      accentBg: 'bg-orange-500/10',
    },
  };

  const config = categoryConfig[category];

  return (
    <div className={`h-full flex flex-col ${config.bgColor} border ${config.borderColor} rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8`}>
      {/* Header - Compact */}
      <div className="fi-flex-between mb-4 sm:mb-6 flex-shrink-0">
        <div className="flex items-center gap-3 sm:gap-4">
          <div
            className={`${config.accentBg} rounded-full p-3 sm:p-4`}
            style={{ fontSize: 'clamp(2rem, 4vw, 4rem)' }}
          >
            {config.icon}
          </div>
          <div>
            <h3
              className={`font-bold ${config.color}`}
              style={{ fontSize: 'clamp(1.25rem, 2.5vw, 2.5rem)' }}
            >
              Tip del Día
            </h3>
            <p
              className="text-slate-400"
              style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}
            >
              {config.label}
            </p>
          </div>
        </div>
        {generatedBy === 'FI' && (
          <div
            className="flex items-center gap-2 fi-text-purple bg-purple-500/10 px-3 py-1.5 rounded-full"
            style={{ fontSize: 'clamp(0.75rem, 1vw, 1rem)' }}
          >
            <svg className="w-4 h-4 sm:w-5 sm:h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M13 7H7v6h6V7z" />
              <path fillRule="evenodd" d="M7 2a1 1 0 012 0v1h2V2a1 1 0 112 0v1h2a2 2 0 012 2v2h1a1 1 0 110 2h-1v2h1a1 1 0 110 2h-1v2a2 2 0 01-2 2h-2v1a1 1 0 11-2 0v-1H9v1a1 1 0 11-2 0v-1H5a2 2 0 01-2-2v-2H2a1 1 0 110-2h1V9H2a1 1 0 010-2h1V5a2 2 0 012-2h2V2zM5 5h10v10H5V5z" clipRule="evenodd" />
            </svg>
            <span className="hidden sm:inline">Generado por FI</span>
          </div>
        )}
      </div>

      {/* Tip Content - Full Screen Centered */}
      <div className="flex-1 flex items-center justify-center min-h-0 px-4 sm:px-8 lg:px-12">
        <p
          className="text-white text-center leading-relaxed font-medium"
          style={{
            fontSize: tip.length > 150
              ? 'clamp(1rem, 2.5vw, 2rem)'
              : tip.length > 80
              ? 'clamp(1.25rem, 3vw, 2.5rem)'
              : 'clamp(1.5rem, 4vw, 3.5rem)',
            maxWidth: '90%',
          }}
        >
          {tip}
        </p>
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 mt-4 pt-4 fi-border-top/30">
        <div
          className="flex items-center justify-center gap-2 text-slate-500"
          style={{ fontSize: 'clamp(0.7rem, 1vw, 1rem)' }}
        >
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span>Consejos de salud • Actualizado diariamente</span>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// CLINIC IMAGE WIDGET
// ============================================================================

interface ClinicImageWidgetProps {
  imageUrl: string;
  title?: string;
  description?: string;
}

export function ClinicImageWidget({ imageUrl, title, description }: ClinicImageWidgetProps) {
  return (
    <div className="bg-gradient-to-br from-slate-950/80 to-slate-900/80 border border-slate-700 rounded-xl overflow-hidden backdrop-blur-sm">
      {/* Image */}
      <div className="relative w-full h-80 bg-slate-900">
        <img
          src={imageUrl}
          alt={title || 'Clinic image'}
          className="w-full h-full object-contain"
        />
      </div>

      {/* Caption */}
      {(title || description) && (
        <div className="p-6 fi-border-top/50">
          {title && (
            <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
          )}
          {description && (
            <p className="text-sm fi-text leading-relaxed">{description}</p>
          )}
          <div className="mt-3 fi-flex-gap fi-text-xs-muted">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M13 7H7v6h6V7z" />
              <path fillRule="evenodd" d="M7 2a1 1 0 012 0v1h2V2a1 1 0 112 0v1h2a2 2 0 012 2v2h1a1 1 0 110 2h-1v2h1a1 1 0 110 2h-1v2a2 2 0 01-2 2h-2v1a1 1 0 11-2 0v-1H9v1a1 1 0 11-2 0v-1H5a2 2 0 01-2-2v-2H2a1 1 0 110-2h1V9H2a1 1 0 010-2h1V5a2 2 0 012-2h2V2zM5 5h10v10H5V5z" clipRule="evenodd" />
            </svg>
            <span>Contenido de su clínica</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// CLINIC VIDEO WIDGET
// ============================================================================

interface ClinicVideoWidgetProps {
  videoUrl: string;
  title?: string;
  description?: string;
}

export function ClinicVideoWidget({ videoUrl, title, description }: ClinicVideoWidgetProps) {
  return (
    <div className="bg-gradient-to-br from-slate-950/80 to-slate-900/80 border border-slate-700 rounded-xl overflow-hidden backdrop-blur-sm">
      {/* Video */}
      <div className="relative w-full h-80 bg-slate-900">
        <video
          src={videoUrl}
          className="w-full h-full object-contain"
          autoPlay
          muted
          loop
          playsInline
        />
      </div>

      {/* Caption */}
      {(title || description) && (
        <div className="p-6 fi-border-top/50">
          {title && (
            <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
          )}
          {description && (
            <p className="text-sm fi-text leading-relaxed">{description}</p>
          )}
          <div className="mt-3 fi-flex-gap fi-text-xs-muted">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z" />
            </svg>
            <span>Contenido de su clínica</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// CLINIC CUSTOM MESSAGE WIDGET - Full Screen TV Optimized
// FI-TV-002: Smart text scaling with viewport units
// ============================================================================

interface ClinicMessageWidgetProps {
  message: string;
  title?: string;
}

export function ClinicMessageWidget({ message, title }: ClinicMessageWidgetProps) {
  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-indigo-950/60 to-violet-950/40 border border-indigo-600/40 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8">
      {/* Header */}
      <div className="flex items-center gap-4 sm:gap-6 mb-4 sm:mb-6 flex-shrink-0">
        <div
          className="rounded-full bg-gradient-to-br from-indigo-600/30 to-violet-600/30 border-2 border-indigo-500/40 flex items-center justify-center p-4 sm:p-6"
        >
          <svg
            className="text-indigo-300"
            fill="currentColor"
            viewBox="0 0 20 20"
            style={{ width: 'clamp(2rem, 4vw, 4rem)', height: 'clamp(2rem, 4vw, 4rem)' }}
          >
            <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
          </svg>
        </div>
        <div>
          <h3
            className="font-bold text-indigo-300"
            style={{ fontSize: 'clamp(1.25rem, 2.5vw, 2.5rem)' }}
          >
            {title || 'Mensaje del Doctor'}
          </h3>
          <p
            className="text-indigo-400/60"
            style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}
          >
            Información importante
          </p>
        </div>
      </div>

      {/* Message content - Full Screen Centered */}
      <div className="flex-1 flex items-center justify-center min-h-0 px-4 sm:px-8 lg:px-16">
        <p
          className="text-white text-center leading-relaxed font-medium"
          style={{
            fontSize: message.length > 200
              ? 'clamp(1rem, 2vw, 1.75rem)'
              : message.length > 100
              ? 'clamp(1.25rem, 3vw, 2.5rem)'
              : 'clamp(1.5rem, 4vw, 3.5rem)',
            maxWidth: '90%',
          }}
        >
          {message}
        </p>
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 mt-4 pt-4 border-t border-indigo-700/30">
        <div
          className="flex items-center justify-center gap-2 text-indigo-400"
          style={{ fontSize: 'clamp(0.7rem, 1vw, 1rem)' }}
        >
          <div className="w-2 h-2 sm:w-3 sm:h-3 bg-indigo-500 rounded-full animate-pulse" />
          <span>Mensaje personalizado de su clínica</span>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// FEATURED SERVICES WIDGET - Full Screen TV Gallery Template
// FI-TV-005: Widget Templates Gallery for digital signage
// ============================================================================

interface ServiceItem {
  icon: string;
  name: string;
  description: string;
}

interface FeaturedServicesWidgetProps {
  services?: ServiceItem[];
  clinicName?: string;
}

export function FeaturedServicesWidget({
  services = [
    { icon: '🩺', name: 'Consulta General', description: 'Atención médica integral' },
    { icon: '💉', name: 'Vacunación', description: 'Esquema completo' },
    { icon: '🔬', name: 'Laboratorio', description: 'Resultados rápidos' },
    { icon: '📋', name: 'Check-up', description: 'Evaluación preventiva' },
  ],
  clinicName = 'Nuestra Clínica',
}: FeaturedServicesWidgetProps) {
  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-900/80 to-slate-950/80 border border-slate-700/40 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8">
      {/* Header */}
      <div className="text-center mb-4 sm:mb-6 lg:mb-8 flex-shrink-0">
        <h2
          className="font-bold text-white mb-2"
          style={{ fontSize: 'clamp(1.5rem, 3.5vw, 3.5rem)' }}
        >
          Nuestros Servicios
        </h2>
        <p
          className="text-slate-400"
          style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.5rem)' }}
        >
          {clinicName}
        </p>
      </div>

      {/* Services Grid - 2x2 for TV */}
      <div className="flex-1 grid grid-cols-2 gap-3 sm:gap-4 lg:gap-6 min-h-0 content-center">
        {services.slice(0, 4).map((service, index) => (
          <div
            key={index}
            className="flex flex-col items-center justify-center bg-slate-800/40 border border-slate-700/40 rounded-xl p-4 sm:p-6 lg:p-8 transition-transform hover:scale-105"
          >
            <div
              className="mb-2 sm:mb-4"
              style={{ fontSize: 'clamp(3rem, 8vw, 8rem)' }}
            >
              {service.icon}
            </div>
            <h3
              className="font-bold text-white text-center mb-1 sm:mb-2"
              style={{ fontSize: 'clamp(1rem, 2vw, 2rem)' }}
            >
              {service.name}
            </h3>
            <p
              className="text-slate-400 text-center"
              style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}
            >
              {service.description}
            </p>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 mt-4 sm:mt-6 pt-4 fi-border-top/30 text-center">
        <p
          className="fi-text-success"
          style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.5rem)' }}
        >
          ✓ Atención de calidad • Horario extendido
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// PROMOTION BANNER WIDGET - Full Screen TV Gallery Template
// FI-TV-005: Widget Templates Gallery for digital signage
// ============================================================================

interface PromotionBannerWidgetProps {
  title: string;
  subtitle?: string;
  highlight?: string;
  ctaText?: string;
  backgroundColor?: string;
}

export function PromotionBannerWidget({
  title,
  subtitle,
  highlight,
  ctaText,
  backgroundColor = 'from-purple-950/70 to-indigo-950/70',
}: PromotionBannerWidgetProps) {
  return (
    <div className={`h-full flex flex-col items-center justify-center bg-gradient-to-br ${backgroundColor} border border-purple-600/40 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8 text-center`}>
      {/* Highlight badge */}
      {highlight && (
        <div
          className="bg-yellow-500/20 border border-yellow-500/50 text-yellow-300 font-bold px-4 sm:px-6 py-2 sm:py-3 rounded-full mb-4 sm:mb-6 lg:mb-8 animate-pulse"
          style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.5rem)' }}
        >
          {highlight}
        </div>
      )}

      {/* Main title - GIANT */}
      <h2
        className="font-black text-white leading-tight mb-4 sm:mb-6"
        style={{
          fontSize: title.length > 30
            ? 'clamp(1.5rem, 5vw, 4rem)'
            : 'clamp(2rem, 7vw, 6rem)',
        }}
      >
        {title}
      </h2>

      {/* Subtitle */}
      {subtitle && (
        <p
          className="fi-text max-w-3xl mb-6 sm:mb-8"
          style={{ fontSize: 'clamp(1rem, 2vw, 2rem)' }}
        >
          {subtitle}
        </p>
      )}

      {/* CTA */}
      {ctaText && (
        <div
          className="bg-white/10 border border-white/30 text-white font-semibold px-6 sm:px-10 py-3 sm:py-5 rounded-xl"
          style={{ fontSize: 'clamp(1rem, 2vw, 2rem)' }}
        >
          {ctaText}
        </div>
      )}

      {/* Decorative elements */}
      <div className="absolute top-4 right-4 sm:top-8 sm:right-8 opacity-20">
        <div
          className="text-white"
          style={{ fontSize: 'clamp(4rem, 10vw, 10rem)' }}
        >
          ✨
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// TESTIMONIAL WIDGET - Full Screen TV Gallery Template
// FI-TV-005: Widget Templates Gallery for digital signage
// ============================================================================

interface TestimonialWidgetProps {
  quote: string;
  author: string;
  role?: string;
  rating?: number;
}

export function TestimonialWidget({
  quote,
  author,
  role = 'Paciente',
  rating = 5,
}: TestimonialWidgetProps) {
  return (
    <div className="h-full flex flex-col items-center justify-center bg-gradient-to-br from-amber-950/50 to-orange-950/50 border border-amber-600/40 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8 text-center relative overflow-hidden">
      {/* Large quote marks */}
      <div
        className="absolute top-2 sm:top-4 left-4 sm:left-8 text-amber-500/20 font-serif"
        style={{ fontSize: 'clamp(6rem, 15vw, 15rem)' }}
      >
        &quot;
      </div>

      {/* Stars rating */}
      <div className="flex items-center gap-1 sm:gap-2 mb-4 sm:mb-6 lg:mb-8 z-10">
        {[...Array(5)].map((_, i) => (
          <span
            key={i}
            className={i < rating ? 'text-yellow-400' : 'text-slate-600'}
            style={{ fontSize: 'clamp(1.5rem, 3vw, 3rem)' }}
          >
            ★
          </span>
        ))}
      </div>

      {/* Quote */}
      <p
        className="text-white font-medium leading-relaxed mb-6 sm:mb-8 lg:mb-10 max-w-4xl z-10"
        style={{
          fontSize: quote.length > 150
            ? 'clamp(1rem, 2vw, 1.75rem)'
            : quote.length > 80
            ? 'clamp(1.25rem, 2.5vw, 2.25rem)'
            : 'clamp(1.5rem, 3vw, 2.75rem)',
        }}
      >
        &quot;{quote}&quot;
      </p>

      {/* Author */}
      <div className="z-10">
        <p
          className="font-bold text-amber-300 mb-1"
          style={{ fontSize: 'clamp(1rem, 2vw, 2rem)' }}
        >
          — {author}
        </p>
        <p
          className="fi-text-warning/70"
          style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}
        >
          {role}
        </p>
      </div>

      {/* Decorative bottom */}
      <div className="absolute bottom-2 sm:bottom-4 right-4 sm:right-8 text-amber-500/20 font-serif rotate-180"
        style={{ fontSize: 'clamp(6rem, 15vw, 15rem)' }}
      >
        &quot;
      </div>
    </div>
  );
}

// ============================================================================
// WAIT TIME DISPLAY WIDGET - Full Screen TV Gallery Template
// FI-TV-005: Widget Templates Gallery for digital signage
// Shows estimated wait time prominently for patient comfort
// ============================================================================

interface WaitTimeDisplayWidgetProps {
  estimatedMinutes: number;
  patientsAhead?: number;
}

export function WaitTimeDisplayWidget({
  estimatedMinutes,
  patientsAhead = 3,
}: WaitTimeDisplayWidgetProps) {
  const getTimeColor = () => {
    if (estimatedMinutes <= 10) return 'fi-text-success';
    if (estimatedMinutes <= 20) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const getTimeBg = () => {
    if (estimatedMinutes <= 10) return 'from-emerald-950/60 to-green-950/60';
    if (estimatedMinutes <= 20) return 'from-yellow-950/60 to-amber-950/60';
    return 'from-orange-950/60 to-red-950/60';
  };

  return (
    <div className={`h-full flex flex-col items-center justify-center bg-gradient-to-br ${getTimeBg()} border border-slate-700/40 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8 text-center`}>
      {/* Icon */}
      <div
        className="mb-4 sm:mb-6"
        style={{ fontSize: 'clamp(4rem, 10vw, 10rem)' }}
      >
        ⏱️
      </div>

      {/* Label */}
      <p
        className="text-slate-400 mb-2 sm:mb-4"
        style={{ fontSize: 'clamp(1rem, 2vw, 2rem)' }}
      >
        Tiempo de espera estimado
      </p>

      {/* GIANT time display */}
      <div className="flex items-baseline gap-2 sm:gap-4 mb-4 sm:mb-6">
        <span
          className={`font-black ${getTimeColor()}`}
          style={{ fontSize: 'clamp(4rem, 15vw, 14rem)' }}
        >
          {estimatedMinutes}
        </span>
        <span
          className="text-slate-400 font-bold"
          style={{ fontSize: 'clamp(1.5rem, 4vw, 4rem)' }}
        >
          min
        </span>
      </div>

      {/* Patients ahead */}
      <div className="fi-flex-gap sm:gap-3 text-slate-400">
        <span
          className="bg-slate-800/60 px-4 sm:px-6 py-2 sm:py-3 rounded-full"
          style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.5rem)' }}
        >
          👤 {patientsAhead} {patientsAhead === 1 ? 'paciente' : 'pacientes'} antes que usted
        </span>
      </div>

      {/* Reassurance */}
      <p
        className="fi-text-success/80 mt-6 sm:mt-8"
        style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.25rem)' }}
      >
        ✓ Le avisaremos cuando sea su turno
      </p>
    </div>
  );
}

// ============================================================================
// CALMING NATURE WIDGET - Full Screen TV Optimized
// FI-TV-002: Smart text scaling with viewport units
// ============================================================================

export function CalmingNatureWidget() {
  const scenes = [
    { emoji: '🌊', label: 'Olas del océano', subtitle: 'Déjate llevar por la calma del mar', color: 'from-blue-600/30 to-cyan-600/20' },
    { emoji: '🌲', label: 'Bosque tranquilo', subtitle: 'Conecta con la naturaleza', color: 'from-green-600/30 to-emerald-600/20' },
    { emoji: '🏔️', label: 'Montañas serenas', subtitle: 'Encuentra tu paz interior', color: 'from-slate-600/30 to-blue-600/20' },
    { emoji: '🌅', label: 'Atardecer dorado', subtitle: 'Un momento de serenidad', color: 'from-orange-600/30 to-pink-600/20' },
    { emoji: '🌸', label: 'Jardín zen', subtitle: 'Armonía y equilibrio', color: 'from-pink-600/30 to-rose-600/20' },
    { emoji: '⭐', label: 'Cielo estrellado', subtitle: 'Infinitas posibilidades', color: 'from-indigo-600/30 to-purple-600/20' },
  ];

  const [currentScene, setCurrentScene] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentScene(prev => (prev + 1) % scenes.length);
    }, 8000);
    return () => clearInterval(timer);
  }, []);

  const scene = scenes[currentScene];

  return (
    <div className={`h-full flex flex-col items-center justify-center bg-gradient-to-br ${scene.color} border border-slate-700/50 rounded-xl backdrop-blur-sm text-center transition-all duration-1000 p-4 sm:p-6 lg:p-8`}>
      {/* Giant Emoji */}
      <div
        className="animate-pulse mb-4 sm:mb-6 lg:mb-8"
        style={{ fontSize: 'clamp(6rem, 20vw, 16rem)' }}
      >
        {scene.emoji}
      </div>

      {/* Label */}
      <h3
        className="font-semibold text-white mb-2 sm:mb-3"
        style={{ fontSize: 'clamp(1.5rem, 4vw, 4rem)' }}
      >
        {scene.label}
      </h3>

      {/* Subtitle */}
      <p
        className="fi-text mb-4 sm:mb-6"
        style={{ fontSize: 'clamp(0.875rem, 2vw, 2rem)' }}
      >
        {scene.subtitle}
      </p>

      {/* Breathing hint */}
      <div className="flex items-center gap-3 text-slate-400 mt-auto">
        <div className="w-3 h-3 sm:w-4 sm:h-4 bg-white/30 rounded-full animate-ping" />
        <span style={{ fontSize: 'clamp(0.75rem, 1.5vw, 1.25rem)' }}>
          Respira profundo y relájate
        </span>
      </div>

      {/* Scene indicator dots */}
      <div className="flex items-center gap-2 mt-4 sm:mt-6">
        {scenes.map((_, index) => (
          <div
            key={index}
            className={`w-2 h-2 sm:w-3 sm:h-3 rounded-full transition-all duration-500 ${
              index === currentScene ? 'bg-white scale-125' : 'bg-white/30'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
