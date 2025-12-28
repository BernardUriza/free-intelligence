/**
 * Onboarding Steps Smoke Tests
 */

import { render } from '@testing-library/react';
import { WelcomeStep } from '../steps/WelcomeStep';
import { SurveyStep } from '../steps/SurveyStep';
import type { OnboardingContext, StepCallbacks, StepStatus } from '../types';

const mockContext: OnboardingContext = {
  survey: {},
  patient: { nombre: '', edad: '', genero: '', motivoConsulta: '' },
  messages: ['Test message'],
  isTyping: false,
};

const mockCallbacks: StepCallbacks = {
  next: jest.fn(),
  back: jest.fn(),
  skip: jest.fn(),
  complete: jest.fn(),
  updateContext: jest.fn(),
};

const mockStatus: StepStatus = { busy: false };

describe('Onboarding Steps', () => {
  it('WelcomeStep renders without crashing', () => {
    const { container } = render(
      <WelcomeStep
        context={mockContext}
        callbacks={mockCallbacks}
        status={mockStatus}
      />
    );
    expect(container).toBeInTheDocument();
  });

  it('SurveyStep renders without crashing', () => {
    const { container } = render(
      <SurveyStep
        context={mockContext}
        callbacks={mockCallbacks}
        status={mockStatus}
      />
    );
    expect(container).toBeInTheDocument();
  });
});