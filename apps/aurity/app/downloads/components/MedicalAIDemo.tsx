'use client';

import { useState, useEffect, useRef } from 'react';
import { ArrowRight, CheckCircle2 } from 'lucide-react';

import { DEMO_STEPS, STEP_DURATIONS_MS } from '../constants';

/**
 * Animated timeline showing the Aurity medical AI pipeline:
 * Dictation -> Transcription -> AI Analysis -> SOAP Note.
 * Loops continuously with cleanup on unmount.
 */
export function MedicalAIDemo() {
  const [activeStep, setActiveStep] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const isCleanedUpRef = useRef(false);

  useEffect(() => {
    const timeoutIds: NodeJS.Timeout[] = [];

    const runAnimation = () => {
      if (isCleanedUpRef.current) return;

      isCleanedUpRef.current = false;
      setActiveStep(0);
      setIsComplete(false);

      let totalDelay = 0;

      STEP_DURATIONS_MS.forEach((duration, index) => {
        const stepTimeout = setTimeout(() => {
          if (isCleanedUpRef.current) return;
          setActiveStep(index);
          if (index === STEP_DURATIONS_MS.length - 1) {
            const completeTimeout = setTimeout(() => {
              if (isCleanedUpRef.current) return;
              setIsComplete(true);
            }, duration - 500);
            timeoutIds.push(completeTimeout);
          }
        }, totalDelay);
        timeoutIds.push(stepTimeout);
        totalDelay += duration;
      });

      const loopTimeout = setTimeout(() => {
        if (!isCleanedUpRef.current) {
          runAnimation();
        }
      }, totalDelay + 2000);
      timeoutIds.push(loopTimeout);
    };

    runAnimation();

    return () => {
      isCleanedUpRef.current = true;
      timeoutIds.forEach((id) => clearTimeout(id));
    };
  }, []);

  return (
    <div className="dl-demo-card">
      {/* Header */}
      <div className="dl-demo-header">
        <h3 className="dl-demo-title">Así funciona Aurity</h3>
        <p className="dl-demo-subtitle">De tu voz a una nota SOAP en segundos</p>
      </div>

      {/* Timeline */}
      <div className="dl-demo-timeline">
        {DEMO_STEPS.map((step, index) => {
          const Icon = step.icon;
          const isActive = index === activeStep;
          const isPast = index < activeStep || isComplete;

          return (
            <div key={step.id} className="dl-step-wrapper">
              <div className={isActive ? 'dl-demo-step-active' : 'dl-demo-step'}>
                {/* Icon Circle */}
                <div
                  className={
                    isActive
                      ? 'dl-demo-circle-active'
                      : isPast
                        ? 'dl-demo-circle-past'
                        : 'dl-demo-circle-default'
                  }
                >
                  <Icon className={isActive || isPast ? 'dl-demo-icon-active' : 'dl-demo-icon-default'} />
                  {isActive && <div className="dl-demo-pulse" />}
                </div>

                {/* Label */}
                <span
                  className={
                    isActive
                      ? 'dl-demo-label-active'
                      : isPast
                        ? 'dl-demo-label-past'
                        : 'dl-demo-label-default'
                  }
                >
                  {step.label}
                </span>

                {/* Duration badge */}
                <span
                  className={
                    isActive
                      ? 'dl-demo-badge-active'
                      : isPast
                        ? 'dl-demo-badge-past'
                        : 'dl-demo-badge-default'
                  }
                >
                  {step.duration}
                </span>
              </div>

              {/* Desktop arrow connector */}
              {index < DEMO_STEPS.length - 1 && (
                <div className="dl-demo-connector">
                  <div className={isPast ? 'dl-demo-hline-past' : 'dl-demo-hline-default'} />
                  <ArrowRight className={isPast ? 'dl-demo-arrow-past' : 'dl-demo-arrow-default'} />
                </div>
              )}

              {/* Mobile vertical connector */}
              {index < DEMO_STEPS.length - 1 && (
                <div className="dl-demo-connector-mobile">
                  <div className={isPast ? 'dl-demo-vline-past' : 'dl-demo-vline-default'} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Current step description */}
      <div className="dl-demo-footer">
        <div className={isComplete ? 'dl-demo-status-complete' : 'dl-demo-status-progress'}>
          {isComplete ? (
            <>
              <CheckCircle2 className="dl-icon-sm" />
              <span className="dl-demo-status-text">Nota SOAP lista para revisión</span>
            </>
          ) : (
            <span className="dl-demo-status-text">{DEMO_STEPS[activeStep]?.description}</span>
          )}
        </div>
      </div>
    </div>
  );
}
