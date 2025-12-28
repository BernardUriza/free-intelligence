/**
 * Onboarding Flow State Machine Tests
 */

import { renderHook, act } from '@testing-library/react';
import { useOnboardingFlow } from '../hooks/useOnboardingFlow';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

// Mock the FI conversation hook
jest.mock('@aurity-standalone/hooks/useFIConversation', () => ({
  useFIConversation: () => ({
    messages: ['Hello from FI'],
    loading: false,
    isTyping: false,
    getIntroduction: jest.fn(),
  }),
}));

describe('useOnboardingFlow', () => {
  beforeEach(() => {
    // Clear localStorage
    localStorage.clear();
  });

  it('starts with welcome phase', () => {
    const { result } = renderHook(() => useOnboardingFlow());
    expect(result.current.currentPhase).toBe('welcome');
  });

  it('can navigate to next phase', () => {
    const { result } = renderHook(() => useOnboardingFlow());

    act(() => {
      result.current.callbacks.next();
    });

    expect(result.current.currentPhase).toBe('survey');
  });

  it('can navigate back', () => {
    const { result } = renderHook(() => useOnboardingFlow());

    act(() => {
      result.current.callbacks.next();
      result.current.callbacks.back();
    });

    expect(result.current.currentPhase).toBe('welcome');
  });

  it('updates context', () => {
    const { result } = renderHook(() => useOnboardingFlow());

    act(() => {
      result.current.callbacks.updateContext({
        survey: { userRole: 'medico_general' },
      });
    });

    expect(result.current.context.survey.userRole).toBe('medico_general');
  });
});