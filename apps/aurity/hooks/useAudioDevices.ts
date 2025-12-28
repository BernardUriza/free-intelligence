/**
 * useAudioDevices Hook
 *
 * Manages audio input device enumeration, selection, and persistence.
 * Handles permission flow and device hot-plug/unplug detection.
 *
 * Features:
 * - Enumerates available audio input devices
 * - Persists selection to localStorage
 * - Validates stored device on load (fallback if unavailable)
 * - Subscribes to device change events
 * - Manages permission state
 */

'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface AudioDevice {
  deviceId: string;
  label: string;
  isDefault: boolean;
}

export type PermissionState = 'prompt' | 'granted' | 'denied' | 'unknown';

export interface UseAudioDevicesReturn {
  /** List of available audio input devices */
  devices: AudioDevice[];
  /** Currently selected device ID (null = use system default) */
  selectedDeviceId: string | null;
  /** Currently selected device object */
  selectedDevice: AudioDevice | null;
  /** Loading state during enumeration */
  isLoading: boolean;
  /** Error message if enumeration failed */
  error: string | null;
  /** Current microphone permission state */
  permissionState: PermissionState;
  /** Select a specific device (null = default) */
  selectDevice: (deviceId: string | null) => void;
  /** Refresh the device list */
  refreshDevices: () => Promise<void>;
  /** Request microphone permission */
  requestPermission: () => Promise<boolean>;
}

// =============================================================================
// Constants
// =============================================================================

const STORAGE_KEY = 'fi_audio_input_device';
// Label for default device selection (exported for use by UI components)
export const DEFAULT_DEVICE_LABEL = 'Micrófono predeterminado';

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Gets stored device ID from localStorage
 */
function getStoredDeviceId(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

/**
 * Saves device ID to localStorage
 */
function saveDeviceId(deviceId: string | null): void {
  if (typeof window === 'undefined') return;
  try {
    if (deviceId === null) {
      localStorage.removeItem(STORAGE_KEY);
    } else {
      localStorage.setItem(STORAGE_KEY, deviceId);
    }
  } catch (err) {
    console.warn('[useAudioDevices] Failed to save device ID:', err);
  }
}

/**
 * Enumerates audio input devices
 */
async function enumerateAudioInputDevices(): Promise<AudioDevice[]> {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices) {
    return [];
  }

  const allDevices = await navigator.mediaDevices.enumerateDevices();
  const audioInputs = allDevices.filter((d) => d.kind === 'audioinput');

  return audioInputs.map((device, index) => ({
    deviceId: device.deviceId,
    label: device.label || `Micrófono ${index + 1}`,
    isDefault: device.deviceId === 'default' || index === 0,
  }));
}

/**
 * Checks if the Permissions API supports microphone query
 */
async function queryMicrophonePermission(): Promise<PermissionState> {
  if (typeof navigator === 'undefined' || !navigator.permissions) {
    return 'unknown';
  }

  try {
    const result = await navigator.permissions.query({
      name: 'microphone' as PermissionName,
    });
    return result.state as PermissionState;
  } catch {
    // Safari doesn't support microphone permission query
    return 'unknown';
  }
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAudioDevices(): UseAudioDevicesReturn {
  const [devices, setDevices] = useState<AudioDevice[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [permissionState, setPermissionState] = useState<PermissionState>('unknown');

  const isInitialized = useRef(false);
  const tempStreamRef = useRef<MediaStream | null>(null);

  // Derive selected device from ID
  const selectedDevice = devices.find((d) => d.deviceId === selectedDeviceId) || null;

  /**
   * Refresh the device list
   */
  const refreshDevices = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const deviceList = await enumerateAudioInputDevices();
      setDevices(deviceList);

      // Validate stored selection
      const storedId = getStoredDeviceId();
      if (storedId) {
        const deviceExists = deviceList.some((d) => d.deviceId === storedId);
        if (deviceExists) {
          setSelectedDeviceId(storedId);
        } else {
          // Stored device no longer exists, clear selection
          console.warn('[useAudioDevices] Stored device not found, using default');
          saveDeviceId(null);
          setSelectedDeviceId(null);
        }
      }

      // Update permission state
      const permState = await queryMicrophonePermission();
      setPermissionState(permState);
    } catch (err) {
      console.error('[useAudioDevices] Failed to enumerate devices:', err);
      setError('No se pudieron enumerar los dispositivos de audio');
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Request microphone permission
   * Returns true if permission granted, false otherwise
   */
  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices) {
      setError('API de audio no disponible');
      return false;
    }

    try {
      // Request access to trigger permission prompt
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      tempStreamRef.current = stream;

      // Stop the stream immediately - we just needed permission
      stream.getTracks().forEach((track) => track.stop());
      tempStreamRef.current = null;

      setPermissionState('granted');

      // Refresh devices to get full labels
      await refreshDevices();
      return true;
    } catch (err) {
      console.error('[useAudioDevices] Permission denied:', err);
      setPermissionState('denied');
      setError('Permiso de micrófono denegado');
      return false;
    }
  }, [refreshDevices]);

  /**
   * Select a specific device
   */
  const selectDevice = useCallback((deviceId: string | null) => {
    console.log('[useAudioDevices] Selecting device:', deviceId);
    setSelectedDeviceId(deviceId);
    saveDeviceId(deviceId);
  }, []);

  // Initialize on mount
  useEffect(() => {
    if (isInitialized.current) return;
    isInitialized.current = true;

    // Load stored device ID first
    const storedId = getStoredDeviceId();
    if (storedId) {
      setSelectedDeviceId(storedId);
    }

    // Then refresh devices
    refreshDevices();
  }, [refreshDevices]);

  // Subscribe to device changes
  useEffect(() => {
    if (typeof navigator === 'undefined' || !navigator.mediaDevices) return;

    const handleDeviceChange = () => {
      console.log('[useAudioDevices] Device change detected');
      refreshDevices();
    };

    navigator.mediaDevices.addEventListener('devicechange', handleDeviceChange);

    return () => {
      navigator.mediaDevices.removeEventListener('devicechange', handleDeviceChange);

      // Cleanup any temp stream
      if (tempStreamRef.current) {
        tempStreamRef.current.getTracks().forEach((track) => track.stop());
        tempStreamRef.current = null;
      }
    };
  }, [refreshDevices]);

  // Subscribe to permission changes
  useEffect(() => {
    if (typeof navigator === 'undefined' || !navigator.permissions) return;

    let permissionStatus: PermissionStatus | null = null;

    const handlePermissionChange = () => {
      if (permissionStatus) {
        setPermissionState(permissionStatus.state as PermissionState);
        if (permissionStatus.state === 'granted') {
          refreshDevices();
        }
      }
    };

    navigator.permissions
      .query({ name: 'microphone' as PermissionName })
      .then((status) => {
        permissionStatus = status;
        status.addEventListener('change', handlePermissionChange);
      })
      .catch(() => {
        // Safari doesn't support this
      });

    return () => {
      if (permissionStatus) {
        permissionStatus.removeEventListener('change', handlePermissionChange);
      }
    };
  }, [refreshDevices]);

  return {
    devices,
    selectedDeviceId,
    selectedDevice,
    isLoading,
    error,
    permissionState,
    selectDevice,
    refreshDevices,
    requestPermission,
  };
}
