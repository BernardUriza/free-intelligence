'use client';

import { useEffect, useState } from 'react';
import { Brain, Check } from 'lucide-react';

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
    let isActive = true;
    const countdownTimer = setInterval(() => {
      if (!isActive) return;
      setCountdown(prev => {
        if (prev <= 1) {
          setShowAnswer(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      isActive = false;
      clearInterval(countdownTimer);
    };
  }, []);

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-emerald-950/60 to-teal-950/40 border border-emerald-600/40 rounded-xl backdrop-blur-sm p-4 sm:p-6 lg:p-8">
      <div className="fi-flex-between mb-4 sm:mb-6 flex-shrink-0">
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="bg-emerald-500/10 rounded-full p-3 sm:p-4 flex items-center justify-center">
            <Brain className="w-10 h-10 sm:w-14 sm:h-14 lg:w-16 lg:h-16 text-emerald-400" strokeWidth={1.5} aria-hidden="true" />
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
        {!showAnswer && (
          <div className="fi-flex-gap">
            <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-emerald-500/20 border-2 border-emerald-500 flex items-center justify-center">
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
              <svg className="w-6 h-6 sm:w-8 sm:h-8 fi-text-success flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            )}
          </div>
        ))}
      </div>

      {showAnswer && (
        <div className="flex-shrink-0 mt-4 sm:mt-6 p-4 sm:p-6 bg-emerald-900/30 border border-emerald-600/40 rounded-xl animate-fade-in">
          <p
            className="text-emerald-200 leading-relaxed text-center"
            style={{ fontSize: 'clamp(0.875rem, 1.5vw, 1.25rem)' }}
          >
            <Check className="w-4 h-4 sm:w-5 sm:h-5 text-emerald-300 inline-flex mr-1" strokeWidth={2} aria-hidden="true" />
            {explanation}
          </p>
        </div>
      )}
    </div>
  );
}
