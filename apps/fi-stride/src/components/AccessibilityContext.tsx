import React, { createContext, useContext, useState, useEffect } from 'react';

interface AccessibilitySettings {
  highContrast: boolean;
  fontSize: 'normal' | 'large' | 'extra-large';
  enableTextToSpeech: boolean;
  reduceMotion: boolean;
}

interface AccessibilityContextType {
  settings: AccessibilitySettings;
  toggleHighContrast: () => void;
  setFontSize: (size: 'normal' | 'large' | 'extra-large') => void;
  toggleTextToSpeech: () => void;
  toggleReduceMotion: () => void;
  speak: (text: string) => void;
}

const AccessibilityContext = createContext<AccessibilityContextType | undefined>(
  undefined
);

export function AccessibilityProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<AccessibilitySettings>({
    highContrast: false,
    fontSize: 'normal',
    enableTextToSpeech: false,
    reduceMotion: false,
  });

  // Load settings from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('a11y-settings');
    if (saved) {
      try {
        setSettings(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to load a11y settings:', e);
      }
    }

    // Check for prefers-reduced-motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setSettings((prev) => ({ ...prev, reduceMotion: true }));
    }
  }, []);

  // Save settings to localStorage
  useEffect(() => {
    localStorage.setItem('a11y-settings', JSON.stringify(settings));

    // Apply high contrast class to document
    if (settings.highContrast) {
      document.documentElement.classList.add('high-contrast');
    } else {
      document.documentElement.classList.remove('high-contrast');
    }

    // Apply font size class
    document.documentElement.classList.remove('text-normal', 'text-large', 'text-extra-large');
    document.documentElement.classList.add(`text-${settings.fontSize}`);
  }, [settings]);

  const toggleHighContrast = () => {
    setSettings((prev) => ({ ...prev, highContrast: !prev.highContrast }));
  };

  const setFontSize = (size: 'normal' | 'large' | 'extra-large') => {
    setSettings((prev) => ({ ...prev, fontSize: size }));
  };

  const toggleTextToSpeech = () => {
    setSettings((prev) => ({ ...prev, enableTextToSpeech: !prev.enableTextToSpeech }));
  };

  const toggleReduceMotion = () => {
    setSettings((prev) => ({ ...prev, reduceMotion: !prev.reduceMotion }));
  };

  const speak = (text: string) => {
    if (!settings.enableTextToSpeech) return;

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'es-ES'; // Default to Spanish
    utterance.rate = 0.9;
    utterance.pitch = 1;

    window.speechSynthesis.speak(utterance);
  };

  return (
    <AccessibilityContext.Provider
      value={{
        settings,
        toggleHighContrast,
        setFontSize,
        toggleTextToSpeech,
        toggleReduceMotion,
        speak,
      }}
    >
      {children}
    </AccessibilityContext.Provider>
  );
}

export function useAccessibility() {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error('useAccessibility must be used within AccessibilityProvider');
  }
  return context;
}
