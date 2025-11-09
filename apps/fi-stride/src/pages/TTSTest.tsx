/**
 * TTS Test Page - Test Azure TTS voice
 *
 * Simple interface to test KATNISS voice:
 * - Play predefined messages
 * - Test different texts
 * - Check TTS status
 *
 * Navigate to: http://localhost:5173/tts-test
 */

import React, { useState } from 'react';
import { useTTS } from '../hooks/useTTS';
import sesion06Config from '../config/sesion-06.config';

export function TTSTest() {
  const [text, setText] = useState('Hola, soy KATNISS tu coach. Estás muy fuerte hoy.');
  const [isLoading, setIsLoading] = useState(false);
  const { synthesize, isReady, activeEngine, state, error } = useTTS(sesion06Config.tts);

  const messages = [
    '¡Bienvenido a FI-Stride!',
    'Vamos a entrenar. ¡Tú puedes!',
    '¡Excelente trabajo! 🎉',
    '¡Muy bien! 5 repeticiones completadas',
    '¡Mitad del camino! ¡Sigue adelante! 🔥',
    '¡LO HICISTE! 🏆 ¡Eres un campeón!',
    '¡Wow! ¡Increíble energía! 🚀',
    'Sesión completada. ¡Buen trabajo!',
  ];

  const handlePlayMessage = async (message: string) => {
    setIsLoading(true);
    try {
      await synthesize(message);
      console.log('✓ Message played successfully');
    } catch (err) {
      console.error('✗ Playback error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePlayCustom = async () => {
    if (!text.trim()) return;
    setIsLoading(true);
    try {
      await synthesize(text);
      console.log('✓ Custom message played successfully');
    } catch (err) {
      console.error('✗ Playback error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50 p-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">🎙️ KATNISS Voice Test</h1>
          <p className="text-lg text-gray-600">Test Azure TTS with KATNISS coach voice</p>
        </div>

        {/* Status Card */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8 border-l-4 border-purple-600">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Status</h2>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-700 font-medium">TTS Engine:</span>
              <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full font-mono">
                {activeEngine || 'Loading...'}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-gray-700 font-medium">State:</span>
              <span
                className={`px-3 py-1 rounded-full font-mono ${
                  state === 'ready'
                    ? 'bg-green-100 text-green-800'
                    : state === 'error'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-yellow-100 text-yellow-800'
                }`}
              >
                {state}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-gray-700 font-medium">Ready:</span>
              <span className={isReady ? 'text-2xl' : 'text-gray-400'}>
                {isReady ? '✅' : '⏳'}
              </span>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded text-red-800 text-sm">
                <strong>Error:</strong> {error.message}
              </div>
            )}
          </div>
        </div>

        {/* Predefined Messages */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Predefined Messages</h2>
          <p className="text-gray-600 text-sm mb-4">Click to test KATNISS feedback messages</p>

          <div className="space-y-2">
            {messages.map((message, idx) => (
              <button
                key={idx}
                onClick={() => handlePlayMessage(message)}
                disabled={!isReady || isLoading}
                className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all ${
                  isReady && !isLoading
                    ? 'border-purple-300 hover:border-purple-600 hover:bg-purple-50 cursor-pointer'
                    : 'border-gray-200 bg-gray-50 opacity-50 cursor-not-allowed'
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">🔊</span>
                  <span className="text-gray-800 font-medium">{message}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Custom Text */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Custom Text</h2>

          <div className="space-y-4">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={!isReady || isLoading}
              className={`w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:outline-none focus:border-purple-600 resize-none ${
                !isReady || isLoading ? 'bg-gray-50 opacity-50 cursor-not-allowed' : 'bg-white'
              }`}
              rows={4}
              placeholder="Type your text here..."
            />

            <button
              onClick={handlePlayCustom}
              disabled={!isReady || isLoading || !text.trim()}
              className={`w-full px-6 py-3 rounded-lg font-bold text-white transition-all ${
                isReady && !isLoading && text.trim()
                  ? 'bg-purple-600 hover:bg-purple-700 cursor-pointer'
                  : 'bg-gray-400 opacity-50 cursor-not-allowed'
              }`}
            >
              {isLoading ? '⏳ Playing...' : '🔊 Play'}
            </button>
          </div>
        </div>

        {/* Info */}
        <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-gray-700">
          <p>
            <strong>✓ Azure TTS Working:</strong> If you hear audio, the Azure TTS endpoint is properly
            configured.
          </p>
          <p className="mt-2">
            <strong>🔊 Voice:</strong> Azure "nova" (female voice, Spanish/English)
          </p>
          <p className="mt-2">
            <strong>⚡ Features:</strong> Rate 0.85x (slow for accessibility), Pitch 1.0 (normal)
          </p>
          <p className="mt-2">
            <strong>📋 Logs:</strong> Open browser DevTools (F12) → Console to see TTS debug messages
          </p>
        </div>
      </div>
    </div>
  );
}
