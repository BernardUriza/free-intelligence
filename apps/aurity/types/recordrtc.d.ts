/**
 * Type declarations for recordrtc module
 */

declare module 'recordrtc' {
  interface RecordRTCOptions {
    type?: 'video' | 'audio' | 'canvas' | 'gif';
    mimeType?: string;
    timeSlice?: number;
    ondataavailable?: (blob: Blob) => void;
    recorderType?: any;
    disableLogs?: boolean;
    numberOfAudioChannels?: number;
    desiredSampRate?: number;
    bufferSize?: number;
  }

  class RecordRTC {
    constructor(stream: MediaStream, options?: RecordRTCOptions);
    startRecording(): void;
    stopRecording(callback?: () => void): void;
    pauseRecording(): void;
    resumeRecording(): void;
    getBlob(): Blob;
    getDataURL(callback: (dataURL: string) => void): void;
    reset(): void;
    destroy(): void;
    state: 'inactive' | 'recording' | 'paused' | 'stopped';
    blob: Blob | null;
  }

  export = RecordRTC;
}
