'use client';

// src/voice/recording/RecordingButton.tsx
import { forwardRef } from "react";
import { Loader2 } from "lucide-react";

// src/voice/recording/types.ts
var BUTTON_SIZES = {
  sm: {
    button: "rec-btn-sm",
    icon: "rec-icon-sm",
    ring: "rec-ring-sm"
  },
  md: {
    button: "rec-btn-md",
    icon: "rec-icon-md",
    ring: "rec-ring-md"
  },
  lg: {
    button: "rec-btn-lg",
    icon: "rec-icon-lg",
    ring: "rec-ring-lg"
  },
  xl: {
    button: "rec-btn-xl",
    icon: "rec-icon-xl",
    ring: "rec-ring-xl"
  }
};
var COLOR_THEMES = {
  medical: {
    idle: "rec-theme-medical-idle",
    starting: "rec-theme-medical-starting",
    recording: "rec-theme-medical-recording",
    pausing: "rec-theme-medical-pausing",
    paused: "rec-theme-medical-paused",
    resuming: "rec-theme-medical-resuming",
    processing: "rec-theme-medical-processing",
    stopping: "rec-theme-medical-stopping",
    finalized: "rec-theme-medical-finalized"
  },
  chat: {
    idle: "rec-theme-chat-idle",
    starting: "rec-theme-chat-starting",
    recording: "rec-theme-chat-recording",
    pausing: "rec-theme-chat-pausing",
    paused: "rec-theme-chat-paused",
    resuming: "rec-theme-chat-resuming",
    processing: "rec-theme-chat-processing",
    stopping: "rec-theme-chat-stopping",
    finalized: "rec-theme-chat-finalized"
  },
  minimal: {
    idle: "rec-theme-minimal-idle",
    starting: "rec-theme-minimal-starting",
    recording: "rec-theme-minimal-recording",
    pausing: "rec-theme-minimal-pausing",
    paused: "rec-theme-minimal-paused",
    resuming: "rec-theme-minimal-resuming",
    processing: "rec-theme-minimal-processing",
    stopping: "rec-theme-minimal-stopping",
    finalized: "rec-theme-minimal-finalized"
  }
};
var STATUS_TEXT_ES = {
  idle: "Presiona para comenzar",
  starting: "Iniciando...",
  recording: "Grabando...",
  pausing: "Pausando...",
  paused: "Pausado",
  resuming: "Reanudando...",
  processing: "Procesando...",
  stopping: "Finalizando...",
  finalized: "Completado"
};
var STATUS_TEXT_EN = {
  idle: "Press to start",
  starting: "Starting...",
  recording: "Recording...",
  pausing: "Pausing...",
  paused: "Paused",
  resuming: "Resuming...",
  processing: "Processing...",
  stopping: "Stopping...",
  finalized: "Complete"
};

// src/voice/recording/RecordingButton.tsx
import { jsx } from "react/jsx-runtime";
var RecordingButton = forwardRef(
  function RecordingButton2({
    size = "md",
    bgColor,
    icon: Icon,
    iconSpin = false,
    iconColor = "rec-icon-white",
    disabled = false,
    onClick,
    ariaLabel,
    className = "",
    borderStyle = "",
    animate = ""
  }, ref) {
    const sizeConfig = BUTTON_SIZES[size];
    const DisplayIcon = iconSpin ? Loader2 : Icon;
    return /* @__PURE__ */ jsx(
      "button",
      {
        ref,
        onClick,
        disabled,
        "aria-label": ariaLabel,
        className: `fi-recording-btn-base ${sizeConfig.button} ${bgColor} ${borderStyle} ${animate} ${disabled ? "rec-btn-disabled" : "rec-btn-enabled"} ${className}`,
        children: /* @__PURE__ */ jsx(
          DisplayIcon,
          {
            className: `${sizeConfig.icon} ${iconColor} ${iconSpin ? "rec-icon-spin" : ""}`
          }
        )
      }
    );
  }
);

// src/voice/recording/PulseRings.tsx
import { motion } from "framer-motion";
import { Fragment, jsx as jsx2, jsxs } from "react/jsx-runtime";
function PingRings({ color = "yellow-500" }) {
  const bgClass = `rec-pulse-bg-${color}`;
  return /* @__PURE__ */ jsxs(Fragment, { children: [
    /* @__PURE__ */ jsx2(
      "div",
      {
        className: `rec-pulse-ping-primary ${bgClass}`
      }
    ),
    /* @__PURE__ */ jsx2(
      "div",
      {
        className: `rec-pulse-ping-secondary ${bgClass}`,
        style: { animation: "pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite" }
      }
    )
  ] });
}
function ConcentricRings({ color = "yellow-500" }) {
  const borderClass = `rec-pulse-border-${color}`;
  const rings = [
    { scale: 1.3, opacity: 0.4, delay: 0 },
    { scale: 1.5, opacity: 0.3, delay: 0.2 },
    { scale: 1.7, opacity: 0.2, delay: 0.4 }
  ];
  return /* @__PURE__ */ jsx2(Fragment, { children: rings.map((ring, i) => /* @__PURE__ */ jsx2(
    motion.div,
    {
      className: `rec-pulse-concentric ${borderClass}`,
      initial: { scale: 1, opacity: ring.opacity },
      animate: {
        scale: [1, ring.scale, 1],
        opacity: [ring.opacity, ring.opacity * 0.5, ring.opacity]
      },
      transition: {
        duration: 1.5,
        repeat: Infinity,
        ease: "easeInOut",
        delay: ring.delay
      }
    },
    i
  )) });
}
function VADRings({
  audioLevel = 0,
  isSilent = true
}) {
  const audioScale = !isSilent ? Math.max(1, 1 + audioLevel / 255 * 1) : 1;
  const ringColor = isSilent ? "rgb(239, 68, 68)" : "rgb(34, 197, 94)";
  const rings = [
    { baseScale: 1.2, opacityBase: 0.6 },
    { baseScale: 1.4, opacityBase: 0.4 },
    { baseScale: 1.6, opacityBase: 0.2 }
  ];
  return /* @__PURE__ */ jsx2(Fragment, { children: rings.map((ring, i) => /* @__PURE__ */ jsx2(
    motion.div,
    {
      className: "rec-pulse-vad",
      style: { borderColor: ringColor },
      animate: {
        scale: audioScale * ring.baseScale,
        opacity: ring.opacityBase
      },
      transition: {
        duration: 0.2,
        // Transición suave pero rápida para seguir el ritmo
        ease: "easeOut"
      }
    },
    i
  )) });
}
function PulseRings({
  style,
  color = "yellow-500",
  audioLevel = 0,
  isSilent = true,
  className = ""
}) {
  if (style === "none") return null;
  return /* @__PURE__ */ jsxs("div", { className: `rec-pulse-container ${className}`, children: [
    style === "ping" && /* @__PURE__ */ jsx2(PingRings, { color }),
    style === "rings" && /* @__PURE__ */ jsx2(ConcentricRings, { color }),
    style === "vad" && /* @__PURE__ */ jsx2(VADRings, { audioLevel, isSilent })
  ] });
}

// src/voice/recording/RecordingTimer.tsx
import { motion as motion2 } from "framer-motion";
import { jsx as jsx3, jsxs as jsxs2 } from "react/jsx-runtime";
function formatRecordingTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}
var SIZE_CLASSES = {
  sm: "rec-timer-sm",
  md: "rec-timer-md",
  lg: "rec-timer-lg"
};
function RecordingTimer({
  time,
  visible = true,
  size = "md",
  showDot = false,
  textColor = "rec-timer-text-white",
  dotColor = "rec-timer-dot-red",
  className = ""
}) {
  if (!visible || time <= 0) return null;
  return /* @__PURE__ */ jsxs2("div", { className: `rec-timer-wrap ${SIZE_CLASSES[size]} ${className}`, children: [
    showDot && /* @__PURE__ */ jsx3(
      motion2.div,
      {
        className: `rec-timer-dot ${dotColor}`,
        animate: { opacity: [1, 0.3, 1] },
        transition: {
          duration: 1.5,
          repeat: Infinity,
          ease: "easeInOut"
        }
      }
    ),
    /* @__PURE__ */ jsx3("span", { className: `${textColor} rec-timer-value`, children: formatRecordingTime(time) })
  ] });
}

// src/voice/recording/StatusText.tsx
import { Loader2 as Loader22 } from "lucide-react";
import { motion as motion3 } from "framer-motion";
import { jsx as jsx4, jsxs as jsxs3 } from "react/jsx-runtime";
function StatusText({
  text,
  color = "rec-status-color-default",
  showLoader = false,
  animate = false,
  className = ""
}) {
  const content = /* @__PURE__ */ jsxs3("div", { className: `rec-status-wrap ${color} ${className}`, children: [
    showLoader && /* @__PURE__ */ jsx4(Loader22, { className: "rec-status-loader" }),
    /* @__PURE__ */ jsx4("p", { className: "rec-status-text", children: text })
  ] });
  if (animate) {
    return /* @__PURE__ */ jsx4(
      motion3.div,
      {
        initial: { opacity: 0.7 },
        animate: { opacity: [0.7, 1, 0.7] },
        transition: { duration: 1.5, repeat: Infinity, ease: "easeInOut" },
        children: content
      }
    );
  }
  return content;
}

// src/voice/VoiceMicButton.tsx
import { Mic, Square, Loader2 as Loader23 } from "lucide-react";
import { motion as motion4 } from "framer-motion";
import { jsx as jsx5, jsxs as jsxs4 } from "react/jsx-runtime";
function deriveState(isRecording, isTranscribing) {
  if (isTranscribing && !isRecording) return "processing";
  if (isRecording) return "recording";
  return "idle";
}
function getButtonColor(state, isSilent) {
  if (state === "recording") {
    return isSilent ? "bg-red-500 hover:bg-red-600 text-white" : "bg-green-500 hover:bg-green-600 text-white";
  }
  if (state === "processing") {
    return "bg-blue-500 text-white";
  }
  return "bg-gray-200 hover:bg-gray-300 text-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-200";
}
function VoiceMicButton({
  isRecording,
  isTranscribing,
  audioLevel,
  isSilent,
  recordingTime,
  onStart,
  onStop,
  className = ""
}) {
  const state = deriveState(isRecording, isTranscribing);
  const isDisabled = isTranscribing && !isRecording;
  const handleClick = () => {
    if (isRecording) {
      onStop();
    } else if (!isTranscribing) {
      onStart();
    }
  };
  const icon = isTranscribing ? Loader23 : isRecording ? Square : Mic;
  const iconColor = state === "idle" ? "text-gray-700 dark:text-gray-200" : "text-white";
  return /* @__PURE__ */ jsxs4("div", { className: `relative inline-flex items-center gap-3 ${className}`, children: [
    /* @__PURE__ */ jsxs4("div", { className: "relative", children: [
      isRecording && /* @__PURE__ */ jsx5(
        PulseRings,
        {
          style: "vad",
          audioLevel,
          isSilent
        }
      ),
      /* @__PURE__ */ jsx5(
        motion4.div,
        {
          animate: {
            scale: isRecording && !isSilent ? [1, 1.05, 1] : 1
          },
          transition: {
            duration: 0.6,
            repeat: isRecording && !isSilent ? Infinity : 0,
            ease: "easeInOut"
          },
          children: /* @__PURE__ */ jsx5(
            RecordingButton,
            {
              size: "md",
              bgColor: getButtonColor(state, isSilent),
              icon,
              iconSpin: isTranscribing && !isRecording,
              iconColor,
              disabled: isDisabled,
              onClick: handleClick,
              ariaLabel: isRecording ? "Detener grabaci\xF3n" : "Iniciar grabaci\xF3n de voz",
              className: "relative z-10"
            }
          )
        }
      )
    ] }),
    isRecording && /* @__PURE__ */ jsx5(
      motion4.div,
      {
        initial: { opacity: 0, x: -10 },
        animate: { opacity: 1, x: 0 },
        exit: { opacity: 0, x: -10 },
        children: /* @__PURE__ */ jsx5(
          RecordingTimer,
          {
            time: recordingTime,
            size: "sm",
            showDot: true,
            textColor: "text-gray-700 dark:text-gray-300"
          }
        )
      }
    ),
    isTranscribing && !isRecording && /* @__PURE__ */ jsx5(
      motion4.div,
      {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        className: "text-sm text-blue-600 dark:fi-text-primary font-medium",
        children: "Transcribiendo..."
      }
    )
  ] });
}

// src/voice/SpeakButton.tsx
import { Volume2, Loader2 as Loader24, Play } from "lucide-react";
import { jsx as jsx6 } from "react/jsx-runtime";
var ICON_SIZE = { xs: "w-3 h-3", sm: "w-3.5 h-3.5", md: "w-4 h-4" };
var PAD_SIZE = { xs: "p-1", sm: "p-1.5", md: "p-2" };
function formatVoiceName(voiceId) {
  const match = voiceId.match(/([A-Z][a-z]+)Neural$/);
  if (match) return match[1];
  return voiceId.charAt(0).toUpperCase() + voiceId.slice(1);
}
function SpeakButton({
  content,
  voice = "nova",
  isUserMessage = false,
  onOpenPlayer,
  busy = false,
  cached = false,
  size = "sm",
  className,
  iconClassName,
  title,
  busyTitle = "Generando audio\u2026",
  cachedTitle = "Reproducir (ya generado)"
}) {
  const voiceDisplay = formatVoiceName(voice);
  const icon = iconClassName ?? ICON_SIZE[size];
  const label = busy ? busyTitle : cached ? cachedTitle : title ?? `Escuchar (${voiceDisplay})`;
  return /* @__PURE__ */ jsx6(
    "button",
    {
      type: "button",
      onClick: () => {
        if (!busy) onOpenPlayer(content, voice, isUserMessage);
      },
      disabled: busy,
      "aria-busy": busy,
      className: className ?? PAD_SIZE[size],
      title: label,
      "aria-label": busy ? busyTitle : cached ? cachedTitle : `Escuchar mensaje con voz ${voiceDisplay}`,
      children: busy ? /* @__PURE__ */ jsx6(Loader24, { className: `${icon} animate-spin` }) : cached ? /* @__PURE__ */ jsx6(Play, { className: icon }) : /* @__PURE__ */ jsx6(Volume2, { className: icon })
    }
  );
}

// src/voice/createAudioPlayer.ts
function clampSeekTarget(seconds, duration) {
  if (!Number.isFinite(seconds)) return 0;
  const lowerBounded = Math.max(0, seconds);
  if (Number.isFinite(duration) && duration > 0) {
    return Math.min(lowerBounded, duration);
  }
  return lowerBounded;
}
var INITIAL = {
  status: "idle",
  isPlaying: false,
  isLoading: false,
  error: null,
  currentSrc: null,
  duration: 0,
  currentTime: 0
};
function defaultCreateElement() {
  if (typeof Audio === "undefined") {
    throw new Error(
      "createAudioPlayer: no Audio constructor available. Run in a browser, or inject `createElement` for non-DOM environments/tests."
    );
  }
  return new Audio();
}
function isBlob(source) {
  return typeof Blob !== "undefined" && source instanceof Blob;
}
function createAudioPlayer(options = {}) {
  const {
    createElement = defaultCreateElement,
    createObjectURL = (blob) => URL.createObjectURL(blob),
    revokeObjectURL = (url) => URL.revokeObjectURL(url),
    onError,
    onEnded
  } = options;
  let state = { ...INITIAL };
  let el = null;
  let ownedUrl = null;
  let disposed = false;
  const listeners = /* @__PURE__ */ new Set();
  function emit() {
    for (const l of listeners) l();
  }
  function setState(patch) {
    state = { ...state, ...patch };
    emit();
  }
  const onLoadedMetadata = () => {
    setState({
      isLoading: false,
      duration: Number.isFinite(el?.duration) ? el.duration : 0
    });
  };
  const onTimeUpdate = () => {
    if (el) setState({ currentTime: el.currentTime });
  };
  const onPlaying = () => {
    setState({ status: "playing", isPlaying: true, isLoading: false, error: null });
  };
  const onPause = () => {
    if (state.status !== "idle" && state.status !== "error") {
      setState({ status: "paused", isPlaying: false });
    }
  };
  const onEndedEvt = () => {
    setState({ status: "idle", isPlaying: false, currentTime: 0 });
    onEnded?.();
  };
  const onErrorEvt = () => {
    const err = new Error("audio element error");
    setState({ status: "error", isPlaying: false, isLoading: false, error: err });
    onError?.(err, "audioPlayer:element");
  };
  function ensureElement() {
    if (el) return el;
    el = createElement();
    el.addEventListener("loadedmetadata", onLoadedMetadata);
    el.addEventListener("timeupdate", onTimeUpdate);
    el.addEventListener("playing", onPlaying);
    el.addEventListener("play", onPlaying);
    el.addEventListener("pause", onPause);
    el.addEventListener("ended", onEndedEvt);
    el.addEventListener("error", onErrorEvt);
    return el;
  }
  function releaseOwnedUrl() {
    if (ownedUrl) {
      revokeObjectURL(ownedUrl);
      ownedUrl = null;
    }
  }
  function load(source) {
    if (disposed) return;
    const element = ensureElement();
    releaseOwnedUrl();
    let url;
    if (isBlob(source)) {
      url = createObjectURL(source);
      ownedUrl = url;
    } else {
      url = source.url;
    }
    element.src = url;
    element.load();
    setState({
      status: "loading",
      isLoading: true,
      isPlaying: false,
      error: null,
      currentSrc: url,
      currentTime: 0,
      duration: 0
    });
  }
  async function play() {
    if (disposed || !el) return;
    try {
      await el.play();
      setState({ status: "playing", isPlaying: true, error: null });
    } catch (error) {
      setState({
        status: "error",
        isPlaying: false,
        error: error instanceof Error ? error : new Error(String(error))
      });
      onError?.(error, "audioPlayer:play");
    }
  }
  function pause() {
    if (disposed || !el) return;
    el.pause();
    setState({ status: "paused", isPlaying: false });
  }
  function stop() {
    if (disposed || !el) return;
    el.pause();
    el.currentTime = 0;
    el.src = "";
    releaseOwnedUrl();
    setState({
      status: "idle",
      isPlaying: false,
      isLoading: false,
      currentSrc: null,
      currentTime: 0
    });
  }
  async function toggle() {
    if (state.isPlaying) {
      pause();
      return;
    }
    await play();
  }
  function seek(seconds) {
    if (disposed || !el) return;
    const target = clampSeekTarget(seconds, state.duration);
    el.currentTime = target;
    setState({ currentTime: target });
  }
  function seekBy(deltaSeconds) {
    if (disposed || !el) return;
    const base = Number.isFinite(el.currentTime) ? el.currentTime : state.currentTime;
    seek(base + deltaSeconds);
  }
  function dispose() {
    if (disposed) return;
    disposed = true;
    if (el) {
      el.pause();
      el.removeEventListener("loadedmetadata", onLoadedMetadata);
      el.removeEventListener("timeupdate", onTimeUpdate);
      el.removeEventListener("playing", onPlaying);
      el.removeEventListener("play", onPlaying);
      el.removeEventListener("pause", onPause);
      el.removeEventListener("ended", onEndedEvt);
      el.removeEventListener("error", onErrorEvt);
    }
    releaseOwnedUrl();
    listeners.clear();
  }
  return {
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    load,
    play,
    pause,
    stop,
    toggle,
    seek,
    seekBy,
    dispose
  };
}

// src/voice/useAudioPlayer.ts
import { useEffect, useMemo, useRef, useSyncExternalStore } from "react";
function useAudioPlayer(opts = {}) {
  const cbRef = useRef(opts);
  cbRef.current = opts;
  const controller = useMemo(
    () => createAudioPlayer({
      onError: (e, ctx) => cbRef.current.onError?.(e, ctx),
      onEnded: () => cbRef.current.onEnded?.(),
      ...opts.deps
    }),
    // One controller for the component's lifetime; deps are read once by design.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );
  useEffect(() => () => controller.dispose(), [controller]);
  const state = useSyncExternalStore(
    controller.subscribe,
    controller.getState,
    controller.getState
  );
  return {
    ...state,
    load: controller.load,
    play: controller.play,
    pause: controller.pause,
    stop: controller.stop,
    toggle: controller.toggle,
    seek: controller.seek,
    seekBy: controller.seekBy,
    playSource: async (source) => {
      controller.load(source);
      await controller.play();
    }
  };
}

// src/voice/AudioPlayer.tsx
import { Play as Play2, Pause, Square as Square2, Loader2 as Loader25, AlertCircle } from "lucide-react";
import { useEffect as useEffect2 } from "react";
import { jsx as jsx7, jsxs as jsxs5 } from "react/jsx-runtime";
var ICON = "w-4 h-4";
var BTN = "p-2 disabled:opacity-40";
function AudioPlayer({
  source,
  autoPlay = false,
  onError,
  onEnded,
  className,
  buttonClassName,
  iconClassName
}) {
  const player = useAudioPlayer({ onError, onEnded });
  const { load, play, toggle, stop, isPlaying, isLoading, error, currentSrc } = player;
  useEffect2(() => {
    if (!source) return;
    load(source);
    if (autoPlay) void play();
  }, [source, autoPlay]);
  const hasSource = currentSrc !== null;
  const btnClass = buttonClassName ?? BTN;
  const iconClass = iconClassName ?? ICON;
  return /* @__PURE__ */ jsxs5("div", { className, "data-fi-audio-player": "", children: [
    /* @__PURE__ */ jsx7(
      "button",
      {
        type: "button",
        onClick: () => void toggle(),
        disabled: !hasSource || isLoading,
        "aria-pressed": isPlaying,
        "aria-label": isPlaying ? "Pausar audio" : "Reproducir audio",
        className: btnClass,
        children: isLoading ? /* @__PURE__ */ jsx7(Loader25, { className: `${iconClass} animate-spin`, "aria-hidden": true }) : isPlaying ? /* @__PURE__ */ jsx7(Pause, { className: iconClass, "aria-hidden": true }) : /* @__PURE__ */ jsx7(Play2, { className: iconClass, "aria-hidden": true })
      }
    ),
    /* @__PURE__ */ jsx7(
      "button",
      {
        type: "button",
        onClick: stop,
        disabled: !hasSource,
        "aria-label": "Detener audio",
        className: btnClass,
        children: /* @__PURE__ */ jsx7(Square2, { className: iconClass, "aria-hidden": true })
      }
    ),
    error ? /* @__PURE__ */ jsxs5("span", { role: "alert", className: "inline-flex items-center gap-1 text-xs", children: [
      /* @__PURE__ */ jsx7(AlertCircle, { className: iconClass, "aria-hidden": true }),
      "Error de audio"
    ] }) : null
  ] });
}

// src/voice/RichAudioPlayer.tsx
import {
  Play as Play3,
  Pause as Pause2,
  Square as Square3,
  Loader2 as Loader26,
  AlertCircle as AlertCircle2,
  RotateCcw,
  RotateCw
} from "lucide-react";
import { useEffect as useEffect3 } from "react";
import { jsx as jsx8, jsxs as jsxs6 } from "react/jsx-runtime";
var ICON2 = "w-4 h-4";
var BTN2 = "p-2 disabled:opacity-40";
function formatPlaybackTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) seconds = 0;
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor(total % 3600 / 60);
  const s = total % 60;
  const ss = String(s).padStart(2, "0");
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${ss}`;
  return `${m}:${ss}`;
}
function RichAudioPlayer({
  source,
  autoPlay = false,
  skipSeconds = 10,
  showTime = true,
  onError,
  onEnded,
  className,
  buttonClassName,
  iconClassName,
  progressClassName
}) {
  const player = useAudioPlayer({ onError, onEnded });
  const {
    load,
    play,
    toggle,
    stop,
    seek,
    seekBy,
    isPlaying,
    isLoading,
    error,
    currentSrc,
    duration,
    currentTime
  } = player;
  useEffect3(() => {
    if (!source) return;
    load(source);
    if (autoPlay) void play();
  }, [source, autoPlay]);
  const hasSource = currentSrc !== null;
  const canSeek = hasSource && duration > 0;
  const btnClass = buttonClassName ?? BTN2;
  const iconClass = iconClassName ?? ICON2;
  const positionLabel = `${formatPlaybackTime(currentTime)} / ${formatPlaybackTime(
    duration
  )}`;
  return /* @__PURE__ */ jsxs6(
    "div",
    {
      className,
      "data-fi-audio-player": "rich",
      role: "group",
      "aria-label": "Controles de reproducci\xF3n de audio",
      children: [
        /* @__PURE__ */ jsx8(
          "button",
          {
            type: "button",
            onClick: () => seekBy(-skipSeconds),
            disabled: !canSeek,
            "aria-label": `Retroceder ${skipSeconds} segundos`,
            className: btnClass,
            children: /* @__PURE__ */ jsx8(RotateCcw, { className: iconClass, "aria-hidden": true })
          }
        ),
        /* @__PURE__ */ jsx8(
          "button",
          {
            type: "button",
            onClick: () => void toggle(),
            disabled: !hasSource || isLoading,
            "aria-pressed": isPlaying,
            "aria-label": isPlaying ? "Pausar audio" : "Reproducir audio",
            className: btnClass,
            children: isLoading ? /* @__PURE__ */ jsx8(Loader26, { className: `${iconClass} animate-spin`, "aria-hidden": true }) : isPlaying ? /* @__PURE__ */ jsx8(Pause2, { className: iconClass, "aria-hidden": true }) : /* @__PURE__ */ jsx8(Play3, { className: iconClass, "aria-hidden": true })
          }
        ),
        /* @__PURE__ */ jsx8(
          "button",
          {
            type: "button",
            onClick: stop,
            disabled: !hasSource,
            "aria-label": "Detener audio",
            className: btnClass,
            children: /* @__PURE__ */ jsx8(Square3, { className: iconClass, "aria-hidden": true })
          }
        ),
        /* @__PURE__ */ jsx8(
          "button",
          {
            type: "button",
            onClick: () => seekBy(skipSeconds),
            disabled: !canSeek,
            "aria-label": `Avanzar ${skipSeconds} segundos`,
            className: btnClass,
            children: /* @__PURE__ */ jsx8(RotateCw, { className: iconClass, "aria-hidden": true })
          }
        ),
        /* @__PURE__ */ jsx8(
          "input",
          {
            type: "range",
            min: 0,
            max: duration > 0 ? duration : 0,
            step: 0.1,
            value: Math.min(currentTime, duration > 0 ? duration : currentTime),
            onChange: (e) => seek(Number(e.target.value)),
            disabled: !canSeek,
            "aria-label": "Progreso de reproducci\xF3n",
            "aria-valuetext": positionLabel,
            className: progressClassName,
            "data-fi-audio-progress": ""
          }
        ),
        showTime ? /* @__PURE__ */ jsx8("span", { "data-fi-audio-time": "", "aria-hidden": true, className: "text-xs tabular-nums", children: positionLabel }) : null,
        error ? /* @__PURE__ */ jsxs6("span", { role: "alert", className: "inline-flex items-center gap-1 text-xs", children: [
          /* @__PURE__ */ jsx8(AlertCircle2, { className: iconClass, "aria-hidden": true }),
          "Error de audio"
        ] }) : null
      ]
    }
  );
}

// src/voice/AudioVisualizer.tsx
import { jsx as jsx9 } from "react/jsx-runtime";
var MIN_BAR_PCT = 4;
function normalizeLevels(levels) {
  return levels.map(
    (v) => !Number.isFinite(v) ? 0 : v < 0 ? 0 : v > 1 ? 1 : v
  );
}
function resampleLevels(levels, count) {
  if (count <= 0) return [];
  if (levels.length === 0) return new Array(count).fill(0);
  if (levels.length === count) return levels.slice();
  const out = [];
  for (let i = 0; i < count; i++) {
    const idx = Math.min(
      levels.length - 1,
      Math.floor(i / count * levels.length)
    );
    out.push(levels[idx]);
  }
  return out;
}
function AudioVisualizer({
  levels,
  variant = "bars",
  active = true,
  barCount,
  label = "Visualizador de nivel de audio",
  className,
  barClassName,
  color
}) {
  const normalized = normalizeLevels(levels);
  if (variant === "pulse") {
    const peak = active && normalized.length ? Math.max(...normalized) : 0;
    const scale = 1 + peak;
    return /* @__PURE__ */ jsx9(
      "div",
      {
        role: "img",
        "aria-label": label,
        className,
        "data-fi-audio-visualizer": "pulse",
        "data-active": active ? "" : void 0,
        children: /* @__PURE__ */ jsx9(
          "span",
          {
            "data-fi-pulse-core": "",
            style: {
              display: "inline-block",
              transform: `scale(${scale})`,
              borderColor: color
            }
          }
        )
      }
    );
  }
  const count = barCount && barCount > 0 ? barCount : normalized.length;
  const bars = resampleLevels(normalized, count);
  return /* @__PURE__ */ jsx9(
    "div",
    {
      role: "img",
      "aria-label": label,
      className,
      "data-fi-audio-visualizer": "bars",
      "data-active": active ? "" : void 0,
      style: { display: "inline-flex", alignItems: "flex-end" },
      children: bars.map((level, i) => {
        const pct = active ? Math.max(MIN_BAR_PCT, level * 100) : MIN_BAR_PCT;
        return /* @__PURE__ */ jsx9(
          "span",
          {
            "data-fi-audio-bar": "",
            className: barClassName,
            style: { height: `${pct}%`, backgroundColor: color }
          },
          i
        );
      })
    }
  );
}

// src/voice/ComposerMicSlot.tsx
import { Mic as Mic2, MicOff, Square as Square4, Loader2 as Loader27 } from "lucide-react";
import { jsx as jsx10 } from "react/jsx-runtime";
var ICON3 = "w-4 h-4";
var BTN3 = "p-2 disabled:opacity-40";
function ComposerMicSlot({
  available = false,
  recording = false,
  busy = false,
  onStart,
  onStop,
  unavailableLabel = "Dictado por voz no disponible todav\xEDa",
  startLabel = "Iniciar dictado por voz",
  stopLabel = "Detener dictado por voz",
  busyLabel = "Transcribiendo\u2026",
  className,
  buttonClassName,
  iconClassName
}) {
  const btnClass = buttonClassName ?? BTN3;
  const iconClass = iconClassName ?? ICON3;
  const disabled = !available || busy;
  const label = !available ? unavailableLabel : busy ? busyLabel : recording ? stopLabel : startLabel;
  const handleClick = () => {
    if (disabled) return;
    if (recording) onStop?.();
    else onStart?.();
  };
  const Icon = !available ? MicOff : busy ? Loader27 : recording ? Square4 : Mic2;
  return /* @__PURE__ */ jsx10("div", { className, "data-fi-mic-slot": "", "data-available": available ? "" : void 0, children: /* @__PURE__ */ jsx10(
    "button",
    {
      type: "button",
      onClick: handleClick,
      disabled,
      "aria-disabled": disabled,
      "aria-pressed": available ? recording : void 0,
      "aria-label": label,
      title: !available ? unavailableLabel : void 0,
      className: btnClass,
      children: /* @__PURE__ */ jsx10(
        Icon,
        {
          className: busy ? `${iconClass} animate-spin` : iconClass,
          "aria-hidden": true
        }
      )
    }
  ) });
}

// src/voice/useVoice.ts
import { useCallback, useRef as useRef2, useState } from "react";
function toUrl(src) {
  return src instanceof Blob ? URL.createObjectURL(src) : src.url;
}
var TTS_CACHE_MAX_CLIPS = 8;
var clipKey = (text, voice) => `${voice}\0${text}`;
function useVoice(adapter, opts = {}) {
  const { onError } = opts;
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [voiceName, setVoiceName] = useState("nova");
  const [isUserMessage, setIsUserMessage] = useState(false);
  const [currentVoice, setCurrentVoice] = useState("nova");
  const [currentText, setCurrentText] = useState("");
  const inFlight = useRef2(false);
  const clipCache = useRef2(/* @__PURE__ */ new Map());
  const synthesizeCached = useCallback(
    async (text, voice) => {
      const cache = clipCache.current;
      const key = clipKey(text, voice);
      const hit = cache.get(key);
      if (hit) {
        cache.delete(key);
        cache.set(key, hit);
        return hit;
      }
      const src = await adapter.synthesize(text, voice);
      if (src instanceof Blob && src.size > 0) {
        cache.set(key, src);
        while (cache.size > TTS_CACHE_MAX_CLIPS) {
          const oldest = cache.keys().next().value;
          if (oldest === void 0) break;
          cache.delete(oldest);
        }
      }
      return src;
    },
    [adapter]
  );
  const getVoiceDisplayName = useCallback(
    (voiceId) => {
      const found = adapter?.availableVoices?.find((v) => v.id === voiceId);
      if (found) return found.label.split(" ")[0];
      const match = voiceId.match(/([A-Z][a-z]+)Neural$/);
      return match ? match[1] : voiceId;
    },
    [adapter]
  );
  const generateAudio = useCallback(
    async (text, voice = "nova", isUser = false) => {
      if (!adapter?.synthesize) return;
      if (inFlight.current) return;
      inFlight.current = true;
      setCurrentText(text);
      setCurrentVoice(voice);
      setIsUserMessage(isUser);
      setVoiceName(getVoiceDisplayName(voice));
      setIsOpen(true);
      setAudioUrl((prev) => {
        if (prev?.startsWith("blob:")) URL.revokeObjectURL(prev);
        return null;
      });
      const isHit = clipCache.current.has(clipKey(text, voice));
      if (!isHit) setIsLoading(true);
      try {
        const src = await synthesizeCached(text, voice);
        setAudioUrl(toUrl(src));
      } catch (error) {
        onError?.(error, "useVoice:TTS");
        setIsOpen(false);
      } finally {
        inFlight.current = false;
        setIsLoading(false);
      }
    },
    [adapter, getVoiceDisplayName, onError, synthesizeCached]
  );
  const changeVoice = useCallback(
    async (newVoice) => {
      if (!currentText || !adapter?.synthesize) return;
      if (inFlight.current) return;
      inFlight.current = true;
      setCurrentVoice(newVoice);
      setVoiceName(getVoiceDisplayName(newVoice));
      setIsLoading(true);
      if (audioUrl) URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
      try {
        const src = await synthesizeCached(currentText, newVoice);
        setAudioUrl(toUrl(src));
      } catch (error) {
        onError?.(error, "useVoice:VoiceChange");
      } finally {
        inFlight.current = false;
        setIsLoading(false);
      }
    },
    [adapter, audioUrl, currentText, getVoiceDisplayName, onError, synthesizeCached]
  );
  const close = useCallback(() => {
    setIsOpen(false);
    setAudioUrl(null);
    setIsLoading(false);
    setCurrentText("");
    setIsUserMessage(false);
  }, []);
  const hasCachedAudio = useCallback(
    (text, voice = "nova") => clipCache.current.has(clipKey(text, voice)),
    []
  );
  return {
    isOpen,
    isLoading,
    audioUrl,
    voiceName,
    isUserMessage,
    currentVoice,
    currentText,
    generateAudio,
    changeVoice,
    close,
    hasCachedAudio
  };
}

// src/voice/useDictation.ts
import { useCallback as useCallback3, useState as useState4 } from "react";

// src/voice/useRecorder.ts
import { useState as useState2, useRef as useRef3, useCallback as useCallback2 } from "react";

// src/voice/makeRecorder.ts
async function makeRecorder(stream, onChunk, opts) {
  const timeSlice = opts?.timeSlice;
  const channels = opts?.channels ?? 1;
  const mod = await import("recordrtc");
  const RecordRTC = mod.default ?? mod;
  if (!RecordRTC) {
    throw new Error("[makeRecorder] RecordRTC library not available");
  }
  const mimeType = "audio/wav";
  let currentRecorder = null;
  let loopTimer = null;
  let isActive = false;
  const createRecorder = () => {
    return new RecordRTC(stream, {
      type: "audio",
      recorderType: RecordRTC.StereoAudioRecorder,
      mimeType,
      numberOfAudioChannels: channels,
      desiredSampRate: opts?.sampleRate ?? 16e3,
      disableLogs: true
    });
  };
  const startLoop = async () => {
    if (!isActive) return;
    currentRecorder = createRecorder();
    currentRecorder.startRecording();
    if (timeSlice && timeSlice > 0) {
      loopTimer = setTimeout(async () => {
        if (!currentRecorder || !isActive) return;
        currentRecorder.stopRecording(() => {
          if (!isActive) return;
          const blob = currentRecorder.getBlob();
          if (blob && blob.size > 0) {
            onChunk(blob);
          }
          if (isActive) {
            startLoop();
          }
        });
      }, timeSlice);
    }
  };
  return {
    start: () => {
      isActive = true;
      startLoop();
    },
    stop: () => new Promise((resolve) => {
      isActive = false;
      if (loopTimer) {
        clearTimeout(loopTimer);
        loopTimer = null;
      }
      if (currentRecorder) {
        currentRecorder.stopRecording(() => {
          const finalBlob = currentRecorder.getBlob();
          resolve(finalBlob);
        });
      } else {
        resolve(new Blob([], { type: mimeType }));
      }
    }),
    kind: "recordrtc"
  };
}

// src/voice/useRecorder.ts
var log = {
  error: (_m, _meta) => {
    void _m;
    void _meta;
  },
  warn: (_m, _meta) => {
    void _m;
    void _meta;
  }
};
function useRecorder(config) {
  const {
    onChunk,
    onError,
    timeSlice = 3e3,
    sampleRate = 16e3,
    channels = 1,
    externalStream = null,
    deviceId = null
  } = config;
  const [isRecording, setIsRecording] = useState2(false);
  const [recordingTime, setRecordingTime] = useState2(0);
  const [fullAudioBlob, setFullAudioBlob] = useState2(null);
  const [fullAudioUrl, setFullAudioUrl] = useState2(null);
  const [currentStream, setCurrentStream] = useState2(null);
  const recorderRef = useRef3(null);
  const continuousRecorderRef = useRef3(null);
  const currentStreamRef = useRef3(null);
  const recordingTimerRef = useRef3(null);
  const fullAudioUrlRef = useRef3(null);
  const chunkNumberRef = useRef3(0);
  const startRecording = useCallback2(async () => {
    try {
      chunkNumberRef.current = 0;
      setRecordingTime(0);
      setFullAudioBlob(null);
      if (fullAudioUrlRef.current) {
        URL.revokeObjectURL(fullAudioUrlRef.current);
        fullAudioUrlRef.current = null;
        setFullAudioUrl(null);
      }
      let stream;
      if (externalStream) {
        stream = externalStream;
      } else {
        try {
          const timeoutMs = 15e3;
          const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => {
              reject(new Error(
                "Microphone permission timeout (15s). Check: 1) macOS System Preferences \u2192 Privacy \u2192 Microphone has your browser enabled, 2) Restart browser after granting permission"
              ));
            }, timeoutMs);
          });
          const audioConstraints = deviceId ? { deviceId: { exact: deviceId } } : true;
          stream = await Promise.race([
            navigator.mediaDevices.getUserMedia({ audio: audioConstraints }),
            timeoutPromise
          ]);
        } catch (micError) {
          log.error("Microphone access failed", { error: String(micError) });
          throw micError;
        }
      }
      currentStreamRef.current = stream;
      setCurrentStream(stream);
      const chunkedRecorder = await makeRecorder(
        stream,
        async (blob) => {
          const chunkNumber = chunkNumberRef.current++;
          await onChunk(blob, chunkNumber);
        },
        {
          timeSlice,
          sampleRate,
          channels
        }
      );
      recorderRef.current = chunkedRecorder;
      chunkedRecorder.start();
      const continuousRecorder = await makeRecorder(
        stream,
        () => {
        },
        // Empty callback - blob comes from .stop() return value
        {
          // NO timeSlice = records continuously until stop()
          sampleRate,
          channels
        }
      );
      continuousRecorderRef.current = continuousRecorder;
      continuousRecorder.start();
      setIsRecording(true);
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1e3);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "No se pudo acceder al micr\xF3fono. Por favor, verifica los permisos.";
      log.error("Start failed", { error: String(err) });
      if (onError) {
        onError(errorMessage);
      }
    }
  }, [onChunk, onError, timeSlice, sampleRate, channels, externalStream, deviceId]);
  const stopRecording = useCallback2(async () => {
    try {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      setIsRecording(false);
      if (currentStreamRef.current) {
        currentStreamRef.current.getTracks().forEach((track) => {
          track.stop();
        });
        currentStreamRef.current = null;
        setCurrentStream(null);
      }
      let fullBlob = null;
      if (continuousRecorderRef.current) {
        try {
          fullBlob = await continuousRecorderRef.current.stop();
          if (fullBlob && fullBlob.size > 0) {
            if (fullAudioUrlRef.current) {
              URL.revokeObjectURL(fullAudioUrlRef.current);
            }
            const audioUrl = URL.createObjectURL(fullBlob);
            fullAudioUrlRef.current = audioUrl;
            setFullAudioUrl(audioUrl);
            setFullAudioBlob(fullBlob);
          }
        } catch (err) {
          log.warn("Continuous recorder stop error (non-critical)", { error: String(err) });
        }
        continuousRecorderRef.current = null;
      }
      if (recorderRef.current) {
        try {
          const lastChunk = await recorderRef.current.stop();
          if (lastChunk && lastChunk.size > 0) {
            const finalChunkNumber = chunkNumberRef.current++;
            try {
              const result = onChunk(lastChunk, finalChunkNumber);
              if (result instanceof Promise) {
                result.catch((err) => {
                  log.error("Final chunk processing failed", { error: String(err) });
                });
              }
            } catch (err) {
              log.error("Final chunk processing failed", { error: String(err) });
            }
          }
        } catch (err) {
          log.warn("Chunked recorder stop error (non-critical)", { error: String(err) });
        }
        recorderRef.current = null;
      }
      return fullBlob;
    } catch (err) {
      log.error("Stop failed", { error: String(err) });
      if (currentStreamRef.current) {
        currentStreamRef.current.getTracks().forEach((track) => track.stop());
        currentStreamRef.current = null;
        setCurrentStream(null);
      }
      setIsRecording(false);
      if (onError) {
        onError(err instanceof Error ? err.message : "Error al detener grabaci\xF3n");
      }
      return null;
    }
  }, [onChunk, onError]);
  return {
    isRecording,
    recordingTime,
    currentStream,
    fullAudioBlob,
    fullAudioUrl,
    startRecording,
    stopRecording
  };
}

// src/voice/useAudioAnalysis.ts
import { useState as useState3, useRef as useRef4, useEffect as useEffect4 } from "react";
var AUDIO_CONFIG = { SILENCE_THRESHOLD: 2, AUDIO_GAIN: 2.5 };
function frequencyDataToBands(data, bandCount, gain) {
  if (bandCount <= 0 || data.length === 0) return new Array(Math.max(0, bandCount)).fill(0);
  const usable = Math.floor(data.length * 0.75) || data.length;
  const sliceSize = Math.max(1, Math.floor(usable / bandCount));
  const bands = new Array(bandCount);
  for (let b = 0; b < bandCount; b++) {
    const start = b * sliceSize;
    let sum = 0;
    let n = 0;
    for (let i = start; i < start + sliceSize && i < usable; i++) {
      sum += data[i];
      n++;
    }
    const avg = n ? sum / n : 0;
    const scaled = avg / 255 * gain;
    bands[b] = scaled > 1 ? 1 : scaled < 0 ? 0 : scaled;
  }
  return bands;
}
function useAudioAnalysis(stream, config) {
  const {
    silenceThreshold = AUDIO_CONFIG.SILENCE_THRESHOLD,
    gain = AUDIO_CONFIG.AUDIO_GAIN,
    isActive,
    bandCount = 24
  } = config;
  const [audioLevel, setAudioLevel] = useState3(0);
  const [bands, setBands] = useState3([]);
  const analyserRef = useRef4(null);
  const audioContextRef = useRef4(null);
  const animationFrameRef = useRef4(null);
  const isSilent = audioLevel < silenceThreshold;
  useEffect4(() => {
    if (!stream || !isActive) {
      setAudioLevel(0);
      setBands([]);
      return;
    }
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const gainNode = audioContext.createGain();
    const source = audioContext.createMediaStreamSource(stream);
    gainNode.gain.value = gain;
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.8;
    source.connect(gainNode);
    gainNode.connect(analyser);
    audioContextRef.current = audioContext;
    analyserRef.current = analyser;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    const updateLevel = () => {
      if (!analyserRef.current) return;
      analyserRef.current.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
      setAudioLevel(average);
      setBands(frequencyDataToBands(dataArray, bandCount, gain));
      animationFrameRef.current = requestAnimationFrame(updateLevel);
    };
    updateLevel();
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [stream, isActive, gain, silenceThreshold, bandCount]);
  return { audioLevel, isSilent, bands };
}

// src/voice/useDictation.ts
function useDictation(adapter, opts = {}) {
  const { timeSliceMs = 3e4, deviceId = null, onTranscriptUpdate, onError } = opts;
  const [liveTranscript, setLiveTranscript] = useState4("");
  const [isTranscribing, setIsTranscribing] = useState4(false);
  const handleChunk = useCallback3(
    async (blob, chunkNumber) => {
      if (!adapter?.transcribe) return;
      setIsTranscribing(true);
      try {
        const { text } = await adapter.transcribe(blob, { index: chunkNumber });
        if (text) {
          setLiveTranscript((prev) => {
            const updated = prev ? `${prev} ${text}` : text;
            onTranscriptUpdate?.(updated);
            return updated;
          });
        }
      } catch (err) {
        onError?.(err instanceof Error ? err.message : "transcription failed");
      } finally {
        setIsTranscribing(false);
      }
    },
    [adapter, onTranscriptUpdate, onError]
  );
  const { isRecording, recordingTime, currentStream, startRecording, stopRecording } = useRecorder({
    onChunk: handleChunk,
    onError,
    timeSlice: timeSliceMs,
    deviceId
  });
  const { audioLevel, isSilent, bands } = useAudioAnalysis(currentStream, {
    isActive: isRecording
  });
  const start = useCallback3(async () => {
    setLiveTranscript("");
    await startRecording();
  }, [startRecording]);
  const stop = useCallback3(async () => {
    await stopRecording();
  }, [stopRecording]);
  return {
    isRecording,
    recordingTime,
    audioLevel,
    isSilent,
    bands,
    liveTranscript,
    isTranscribing,
    startRecording: start,
    stopRecording: stop
  };
}

// src/voice/audioArtifact.ts
var AUDIO_QUEUE_DEFAULTS = {
  maxItems: 10,
  maxBytes: 50 * 1024 * 1024,
  // 50 MB total queue
  maxBytesPerItem: 10 * 1024 * 1024
  // 10 MB per artifact
};
function makeArtifactId() {
  return `audio-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
function isPending(a) {
  return a.state !== "transcribed" && a.state !== "deleted";
}
function isTerminal(a) {
  return a.state === "transcribed" || a.state === "deleted";
}
function artifactLabel(state) {
  const map = {
    recording: "Grabando",
    paused: "En pausa",
    saved: "Guardado",
    queued: "En cola",
    uploading: "Subiendo",
    transcribing: "Transcribiendo",
    transcribed: "Transcrito",
    failed: "Fall\xF3",
    deleted: "Eliminado"
  };
  return map[state];
}
function formatArtifactSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
function formatArtifactDuration(ms) {
  if (!ms) return "--:--";
  const s = Math.floor(ms / 1e3);
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

// src/voice/AudioQueueStore.ts
var DEFAULT_DB_NAME = "free-intelligence-audio-queue";
var DEFAULT_STORE_NAME = "audio-artifacts";
var DB_VERSION = 1;
var CREATED_AT_INDEX = "by_createdAt";
function unavailable() {
  return typeof indexedDB === "undefined";
}
function unavailableError() {
  return new Error(
    "AudioQueueStore: IndexedDB is not available (SSR or storage disabled)."
  );
}
var AudioQueueStore = class {
  constructor(opts = {}) {
    this.dbPromise = null;
    this.dbName = opts.dbName ?? DEFAULT_DB_NAME;
    this.storeName = opts.storeName ?? DEFAULT_STORE_NAME;
  }
  open() {
    if (unavailable()) return Promise.reject(unavailableError());
    if (!this.dbPromise) {
      this.dbPromise = new Promise((resolve, reject) => {
        const req = indexedDB.open(this.dbName, DB_VERSION);
        req.onupgradeneeded = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains(this.storeName)) {
            const store = db.createObjectStore(this.storeName, { keyPath: "id" });
            store.createIndex(CREATED_AT_INDEX, "createdAt", { unique: false });
          }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error ?? new Error("AudioQueueStore: open failed"));
      });
    }
    return this.dbPromise;
  }
  async run(mode, makeRequest) {
    const db = await this.open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(this.storeName, mode);
      const req = makeRequest(tx.objectStore(this.storeName));
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error ?? new Error("AudioQueueStore: request failed"));
    });
  }
  async list() {
    return this.run("readonly", (s) => s.getAll());
  }
  async get(id) {
    const r = await this.run(
      "readonly",
      (s) => s.get(id)
    );
    return r ?? null;
  }
  async put(artifact) {
    await this.run("readwrite", (s) => s.put(artifact));
  }
  async updateMeta(id, patch) {
    const existing = await this.get(id);
    if (!existing) return;
    await this.put({
      ...existing,
      ...patch,
      id,
      updatedAt: (/* @__PURE__ */ new Date()).toISOString()
    });
  }
  async delete(id) {
    await this.run("readwrite", (s) => s.delete(id));
  }
  async clear() {
    await this.run("readwrite", (s) => s.clear());
  }
};

// src/voice/useDurableRecording.ts
import { useState as useState5, useRef as useRef5, useCallback as useCallback4, useEffect as useEffect5 } from "react";
var MIC_TIMEOUT_MS = 15e3;
async function loadRecordRTC() {
  const mod = await import("recordrtc");
  const RTC = mod.default ?? mod.RecordRTC ?? mod;
  if (!RTC || typeof RTC !== "function") {
    throw new Error("[useDurableRecording] RecordRTC not available");
  }
  return RTC;
}
function useDurableRecording(opts) {
  const {
    store,
    policy = AUDIO_QUEUE_DEFAULTS,
    deviceId = null,
    onSaved,
    onError
  } = opts;
  const [artifact, setArtifact] = useState5(null);
  const [recordingTime, setRecordingTime] = useState5(0);
  const [currentStream, setCurrentStream] = useState5(null);
  const [isAtCapacity, setIsAtCapacity] = useState5(false);
  const recorderRef = useRef5(null);
  const streamRef = useRef5(null);
  const timerRef = useRef5(null);
  const startTimeRef = useRef5(0);
  const pausedElapsedRef = useRef5(0);
  const artifactRef = useRef5(null);
  useEffect5(() => {
    artifactRef.current = artifact;
  }, [artifact]);
  useEffect5(() => {
    store.list().then((stored) => {
      const pending = stored.filter(
        (a) => a.state !== "transcribed" && a.state !== "deleted"
      );
      const totalBytes = pending.reduce((s, a) => s + a.size, 0);
      setIsAtCapacity(
        pending.length >= policy.maxItems || totalBytes >= policy.maxBytes
      );
    }).catch(() => {
    });
  }, [store, policy]);
  const { audioLevel, isSilent, bands } = useAudioAnalysis(currentStream, {
    isActive: artifact?.state === "recording"
  });
  const stopTimer = useCallback4(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);
  const releaseStream = useCallback4(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      setCurrentStream(null);
    }
  }, []);
  const updateArtifact = useCallback4(
    (patch) => {
      setArtifact((prev) => {
        if (!prev) return prev;
        const updated = { ...prev, ...patch, updatedAt: (/* @__PURE__ */ new Date()).toISOString() };
        artifactRef.current = updated;
        return updated;
      });
    },
    []
  );
  const startRecording = useCallback4(async () => {
    if (artifact?.state === "recording" || artifact?.state === "paused") return;
    try {
      const stored = await store.list();
      const pending = stored.filter(
        (a) => a.state !== "transcribed" && a.state !== "deleted"
      );
      const totalBytes = pending.reduce((s, a) => s + a.size, 0);
      if (pending.length >= policy.maxItems || totalBytes >= policy.maxBytes) {
        setIsAtCapacity(true);
        onError?.(
          `Cola llena (m\xE1ximo ${policy.maxItems} audios o ${Math.round(policy.maxBytes / 1024 / 1024)} MB). Transcribe o elimina audios antes de grabar.`
        );
        return;
      }
      const timeoutPromise = new Promise(
        (_, reject) => setTimeout(
          () => reject(new Error("Permiso de micr\xF3fono expirado (15s).")),
          MIC_TIMEOUT_MS
        )
      );
      const audioConstraints = deviceId ? { deviceId: { exact: deviceId } } : true;
      const stream = await Promise.race([
        navigator.mediaDevices.getUserMedia({ audio: audioConstraints }),
        timeoutPromise
      ]);
      streamRef.current = stream;
      setCurrentStream(stream);
      const RecordRTC = await loadRecordRTC();
      const recorder = new RecordRTC(stream, {
        type: "audio",
        recorderType: RecordRTC.StereoAudioRecorder,
        mimeType: "audio/wav",
        numberOfAudioChannels: 1,
        desiredSampRate: 16e3,
        disableLogs: true
      });
      recorderRef.current = recorder;
      recorder.startRecording();
      const now = Date.now();
      startTimeRef.current = now;
      pausedElapsedRef.current = 0;
      setRecordingTime(0);
      timerRef.current = setInterval(() => {
        setRecordingTime(
          Math.floor((Date.now() - startTimeRef.current) / 1e3)
        );
      }, 1e3);
      const newArtifact = {
        id: makeArtifactId(),
        mime: "audio/wav",
        size: 0,
        createdAt: (/* @__PURE__ */ new Date()).toISOString(),
        updatedAt: (/* @__PURE__ */ new Date()).toISOString(),
        state: "recording"
      };
      setArtifact(newArtifact);
      artifactRef.current = newArtifact;
    } catch (err) {
      releaseStream();
      onError?.(err instanceof Error ? err.message : "No se pudo iniciar la grabaci\xF3n.");
    }
  }, [artifact, store, policy, deviceId, onError, releaseStream]);
  const pauseRecording = useCallback4(() => {
    if (artifactRef.current?.state !== "recording") return;
    recorderRef.current?.pauseRecording();
    stopTimer();
    pausedElapsedRef.current = Date.now() - startTimeRef.current;
    updateArtifact({ state: "paused" });
  }, [stopTimer, updateArtifact]);
  const resumeRecording = useCallback4(() => {
    if (artifactRef.current?.state !== "paused") return;
    recorderRef.current?.resumeRecording();
    startTimeRef.current = Date.now() - pausedElapsedRef.current;
    timerRef.current = setInterval(() => {
      setRecordingTime(
        Math.floor((Date.now() - startTimeRef.current) / 1e3)
      );
    }, 1e3);
    updateArtifact({ state: "recording" });
  }, [updateArtifact]);
  const stopRecording = useCallback4(async () => {
    const current = artifactRef.current;
    if (current?.state !== "recording" && current?.state !== "paused") {
      return null;
    }
    stopTimer();
    const durationMs = Date.now() - startTimeRef.current + pausedElapsedRef.current;
    releaseStream();
    return new Promise((resolve) => {
      if (!recorderRef.current) {
        resolve(null);
        return;
      }
      recorderRef.current.stopRecording(async () => {
        const blob = recorderRef.current?.getBlob() ?? null;
        recorderRef.current = null;
        if (!blob || blob.size === 0) {
          updateArtifact({ state: "failed", errorMessage: "Grabaci\xF3n vac\xEDa." });
          resolve(null);
          return;
        }
        if (blob.size > policy.maxBytesPerItem) {
          updateArtifact({
            state: "failed",
            errorMessage: `Audio demasiado grande (${Math.round(blob.size / 1024 / 1024)} MB, m\xE1ximo ${Math.round(policy.maxBytesPerItem / 1024 / 1024)} MB).`
          });
          resolve(null);
          return;
        }
        const finalArtifact = {
          ...current,
          size: blob.size,
          durationMs,
          state: "queued",
          updatedAt: (/* @__PURE__ */ new Date()).toISOString()
        };
        updateArtifact({
          size: blob.size,
          durationMs,
          state: "queued"
        });
        try {
          await store.put({ ...finalArtifact, blob });
          onSaved?.(finalArtifact);
          setIsAtCapacity(false);
          resolve(finalArtifact);
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Error al guardar audio.";
          updateArtifact({ state: "failed", errorMessage: msg });
          onError?.(msg);
          resolve(null);
        }
      });
    });
  }, [store, policy, releaseStream, stopTimer, updateArtifact, onSaved, onError]);
  const cancelRecording = useCallback4(() => {
    stopTimer();
    releaseStream();
    if (recorderRef.current) {
      try {
        recorderRef.current.stopRecording(() => {
        });
      } catch {
      }
      recorderRef.current = null;
    }
    setArtifact(null);
    artifactRef.current = null;
    setRecordingTime(0);
  }, [stopTimer, releaseStream]);
  return {
    artifact,
    recordingTime,
    bands,
    audioLevel,
    isSilent,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    cancelRecording,
    isAtCapacity
  };
}

// src/voice/useAudioQueue.ts
import { useState as useState6, useEffect as useEffect6, useCallback as useCallback5 } from "react";
function useAudioQueue(opts) {
  const { store, adapter, onTranscribed, onError } = opts;
  const [artifacts, setArtifacts] = useState6([]);
  const [isLoading, setIsLoading] = useState6(true);
  const loadFromStore = useCallback5(async () => {
    try {
      const stored = await store.list();
      const metas = stored.filter((a) => a.state !== "deleted").map(({ blob: _blob, ...meta }) => meta).sort((a, b) => a.createdAt.localeCompare(b.createdAt));
      setArtifacts(metas);
    } catch {
    }
    setIsLoading(false);
  }, [store]);
  useEffect6(() => {
    loadFromStore();
  }, [loadFromStore]);
  const patchLocal = useCallback5(
    (id, patch) => {
      setArtifacts(
        (prev) => prev.map(
          (a) => a.id === id ? { ...a, ...patch, updatedAt: (/* @__PURE__ */ new Date()).toISOString() } : a
        )
      );
    },
    []
  );
  const doTranscribe = useCallback5(
    async (id) => {
      if (!adapter?.transcribe) {
        onError?.(id, "Adaptador de voz sin capacidad de transcripci\xF3n.");
        return;
      }
      patchLocal(id, { state: "transcribing", errorMessage: void 0 });
      await store.updateMeta(id, { state: "transcribing", errorMessage: void 0 });
      const stored = await store.get(id);
      if (!stored) {
        patchLocal(id, { state: "failed", errorMessage: "Artefacto no encontrado." });
        onError?.(id, "Artefacto no encontrado.");
        return;
      }
      patchLocal(id, { state: "uploading" });
      await store.updateMeta(id, { state: "uploading" });
      try {
        const { text } = await adapter.transcribe(stored.blob);
        patchLocal(id, { state: "transcribed", transcript: text });
        await store.updateMeta(id, { state: "transcribed", transcript: text });
        onTranscribed?.(id, text);
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Transcripci\xF3n fallida.";
        patchLocal(id, { state: "failed", errorMessage: msg });
        await store.updateMeta(id, { state: "failed", errorMessage: msg });
        onError?.(id, msg);
      }
    },
    [adapter, store, patchLocal, onTranscribed, onError]
  );
  const transcribeArtifact = useCallback5(
    async (id) => {
      const a = artifacts.find((x) => x.id === id);
      if (!a || a.state !== "queued" && a.state !== "saved") return;
      await doTranscribe(id);
    },
    [artifacts, doTranscribe]
  );
  const retryTranscription = useCallback5(
    async (id) => {
      const a = artifacts.find((x) => x.id === id);
      if (!a || a.state !== "failed") return;
      await doTranscribe(id);
    },
    [artifacts, doTranscribe]
  );
  const getPlaybackUrl = useCallback5(
    async (id) => {
      const stored = await store.get(id);
      if (!stored?.blob || stored.blob.size === 0) return null;
      return URL.createObjectURL(stored.blob);
    },
    [store]
  );
  const deleteArtifact = useCallback5(
    async (id) => {
      await store.delete(id);
      setArtifacts((prev) => prev.filter((a) => a.id !== id));
    },
    [store]
  );
  const clearTranscribed = useCallback5(async () => {
    const toDelete = artifacts.filter((a) => a.state === "transcribed");
    await Promise.all(toDelete.map((a) => store.delete(a.id)));
    setArtifacts((prev) => prev.filter((a) => a.state !== "transcribed"));
  }, [artifacts, store]);
  const reload = useCallback5(async () => {
    setIsLoading(true);
    await loadFromStore();
  }, [loadFromStore]);
  const totalBytes = artifacts.filter(isPending).reduce((s, a) => s + a.size, 0);
  return {
    artifacts,
    totalBytes,
    isLoading,
    transcribeArtifact,
    retryTranscription,
    getPlaybackUrl,
    deleteArtifact,
    clearTranscribed,
    reload
  };
}

// src/voice/AudioQueuePanel.tsx
import { Loader2 as Loader29, Trash2 as Trash22, ShieldAlert } from "lucide-react";

// src/voice/AudioQueueItem.tsx
import { useState as useState7, useCallback as useCallback6 } from "react";
import {
  Mic as Mic3,
  PauseCircle,
  CheckCircle2,
  AlertCircle as AlertCircle3,
  Loader2 as Loader28,
  Play as Play4,
  RotateCcw as RotateCcw2,
  Trash2,
  FileAudio
} from "lucide-react";
import { jsx as jsx11, jsxs as jsxs7 } from "react/jsx-runtime";
function StateIcon({ state }) {
  const base = "w-4 h-4 shrink-0";
  switch (state) {
    case "recording":
      return /* @__PURE__ */ jsx11(Mic3, { className: `${base} text-red-400 animate-pulse` });
    case "paused":
      return /* @__PURE__ */ jsx11(PauseCircle, { className: `${base} text-yellow-400` });
    case "transcribed":
      return /* @__PURE__ */ jsx11(CheckCircle2, { className: `${base} text-green-400` });
    case "failed":
      return /* @__PURE__ */ jsx11(AlertCircle3, { className: `${base} text-red-400` });
    case "transcribing":
    case "uploading":
      return /* @__PURE__ */ jsx11(Loader28, { className: `${base} text-blue-400 animate-spin` });
    default:
      return /* @__PURE__ */ jsx11(FileAudio, { className: `${base} text-gray-400` });
  }
}
function AudioQueueItem({
  artifact,
  onTranscribe,
  onRetry,
  onDelete,
  onGetPlaybackUrl,
  className = ""
}) {
  const [playing, setPlaying] = useState7(false);
  const [audioEl, setAudioEl] = useState7(null);
  const handlePlay = useCallback6(async () => {
    if (!onGetPlaybackUrl) return;
    if (playing && audioEl) {
      audioEl.pause();
      setPlaying(false);
      return;
    }
    const url = await onGetPlaybackUrl(artifact.id);
    if (!url) return;
    const el = new Audio(url);
    setAudioEl(el);
    setPlaying(true);
    el.play().catch(() => setPlaying(false));
    el.addEventListener("ended", () => {
      setPlaying(false);
      URL.revokeObjectURL(url);
    });
    el.addEventListener("error", () => {
      setPlaying(false);
      URL.revokeObjectURL(url);
    });
  }, [artifact.id, onGetPlaybackUrl, playing, audioEl]);
  const canTranscribe = artifact.state === "queued" || artifact.state === "saved";
  const canRetry = artifact.state === "failed";
  const canPlay = !!onGetPlaybackUrl && artifact.size > 0 && artifact.state !== "recording" && artifact.state !== "paused";
  const isBusy = artifact.state === "transcribing" || artifact.state === "uploading";
  return /* @__PURE__ */ jsxs7(
    "div",
    {
      className: `flex items-start gap-3 p-3 rounded-lg bg-white/5 border border-white/10 ${className}`,
      children: [
        /* @__PURE__ */ jsx11(StateIcon, { state: artifact.state }),
        /* @__PURE__ */ jsxs7("div", { className: "flex-1 min-w-0 space-y-0.5", children: [
          /* @__PURE__ */ jsxs7("div", { className: "flex items-center gap-2 text-xs", children: [
            /* @__PURE__ */ jsx11("span", { className: "font-medium text-white/80", children: artifactLabel(artifact.state) }),
            /* @__PURE__ */ jsx11("span", { className: "text-white/40", children: "\xB7" }),
            /* @__PURE__ */ jsx11("span", { className: "text-white/50", children: formatArtifactDuration(artifact.durationMs) }),
            /* @__PURE__ */ jsx11("span", { className: "text-white/40", children: "\xB7" }),
            /* @__PURE__ */ jsx11("span", { className: "text-white/50", children: formatArtifactSize(artifact.size) })
          ] }),
          artifact.state === "transcribed" && artifact.transcript && /* @__PURE__ */ jsx11("p", { className: "text-xs text-white/60 truncate", children: artifact.transcript }),
          artifact.state === "failed" && artifact.errorMessage && /* @__PURE__ */ jsx11("p", { className: "text-xs text-red-400/80 truncate", children: artifact.errorMessage }),
          /* @__PURE__ */ jsx11("p", { className: "text-[10px] text-white/30", children: new Date(artifact.createdAt).toLocaleString("es-MX", {
            hour: "2-digit",
            minute: "2-digit",
            day: "numeric",
            month: "short"
          }) })
        ] }),
        /* @__PURE__ */ jsxs7("div", { className: "flex items-center gap-1 shrink-0", children: [
          canPlay && /* @__PURE__ */ jsx11(
            "button",
            {
              onClick: handlePlay,
              disabled: isBusy,
              className: "p-1.5 rounded-md hover:bg-white/10 text-white/50 hover:text-white/80 transition-colors",
              "aria-label": playing ? "Pausar" : "Reproducir",
              children: /* @__PURE__ */ jsx11(Play4, { className: "w-3.5 h-3.5" })
            }
          ),
          canTranscribe && onTranscribe && /* @__PURE__ */ jsx11(
            "button",
            {
              onClick: () => onTranscribe(artifact.id),
              disabled: isBusy,
              className: "px-2 py-1 rounded-md text-xs bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 transition-colors",
              children: "Transcribir"
            }
          ),
          canRetry && onRetry && /* @__PURE__ */ jsx11(
            "button",
            {
              onClick: () => onRetry(artifact.id),
              className: "p-1.5 rounded-md hover:bg-white/10 text-yellow-400/70 hover:text-yellow-400 transition-colors",
              "aria-label": "Reintentar transcripci\xF3n",
              children: /* @__PURE__ */ jsx11(RotateCcw2, { className: "w-3.5 h-3.5" })
            }
          ),
          onDelete && artifact.state !== "recording" && artifact.state !== "paused" && /* @__PURE__ */ jsx11(
            "button",
            {
              onClick: () => onDelete(artifact.id),
              disabled: isBusy,
              className: "p-1.5 rounded-md hover:bg-white/10 text-white/30 hover:text-red-400 transition-colors",
              "aria-label": "Eliminar audio",
              children: /* @__PURE__ */ jsx11(Trash2, { className: "w-3.5 h-3.5" })
            }
          )
        ] })
      ]
    }
  );
}

// src/voice/AudioQueuePanel.tsx
import { jsx as jsx12, jsxs as jsxs8 } from "react/jsx-runtime";
var DEFAULT_PRIVACY_NOTICE = "Tu audio se guarda localmente hasta que lo transcribas o elimines. No se env\xEDa al servidor hasta que lo solicites.";
function AudioQueuePanel({
  queue,
  className = "",
  privacyNotice = DEFAULT_PRIVACY_NOTICE,
  maxVisible = 6
}) {
  const {
    artifacts,
    totalBytes,
    isLoading,
    transcribeArtifact,
    retryTranscription,
    deleteArtifact,
    clearTranscribed,
    getPlaybackUrl
  } = queue;
  const visible = artifacts.filter((a) => a.state !== "deleted");
  const hasTranscribed = visible.some((a) => a.state === "transcribed");
  if (isLoading) {
    return /* @__PURE__ */ jsx12("div", { className: `flex items-center justify-center p-4 ${className}`, children: /* @__PURE__ */ jsx12(Loader29, { className: "w-4 h-4 text-white/40 animate-spin" }) });
  }
  if (visible.length === 0) return null;
  return /* @__PURE__ */ jsxs8("div", { className: `space-y-2 ${className}`, children: [
    /* @__PURE__ */ jsxs8("div", { className: "flex items-start gap-2 px-3 py-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20", children: [
      /* @__PURE__ */ jsx12(ShieldAlert, { className: "w-3.5 h-3.5 text-yellow-400 shrink-0 mt-0.5" }),
      /* @__PURE__ */ jsx12("p", { className: "text-[11px] text-yellow-200/70 leading-relaxed", children: privacyNotice })
    ] }),
    /* @__PURE__ */ jsxs8("div", { className: "flex items-center justify-between px-1", children: [
      /* @__PURE__ */ jsxs8("span", { className: "text-xs text-white/50", children: [
        visible.length,
        " audio",
        visible.length !== 1 ? "s" : "",
        " \xB7 ",
        formatArtifactSize(totalBytes)
      ] }),
      hasTranscribed && /* @__PURE__ */ jsxs8(
        "button",
        {
          onClick: clearTranscribed,
          className: "flex items-center gap-1 text-xs text-white/40 hover:text-white/70 transition-colors",
          children: [
            /* @__PURE__ */ jsx12(Trash22, { className: "w-3 h-3" }),
            "Limpiar transcritos"
          ]
        }
      )
    ] }),
    /* @__PURE__ */ jsx12(
      "div",
      {
        className: "space-y-1.5 overflow-y-auto",
        style: { maxHeight: `${maxVisible * 68}px` },
        children: visible.map((artifact) => /* @__PURE__ */ jsx12(
          AudioQueueItem,
          {
            artifact,
            onTranscribe: transcribeArtifact,
            onRetry: retryTranscription,
            onDelete: deleteArtifact,
            onGetPlaybackUrl: getPlaybackUrl
          },
          artifact.id
        ))
      }
    )
  ] });
}
export {
  AUDIO_QUEUE_DEFAULTS,
  AudioPlayer,
  AudioQueueItem,
  AudioQueuePanel,
  AudioQueueStore,
  AudioVisualizer,
  BUTTON_SIZES,
  COLOR_THEMES,
  ComposerMicSlot,
  PulseRings,
  RecordingButton,
  RecordingTimer,
  RichAudioPlayer,
  STATUS_TEXT_EN,
  STATUS_TEXT_ES,
  SpeakButton,
  StatusText,
  VoiceMicButton,
  artifactLabel,
  createAudioPlayer,
  formatArtifactDuration,
  formatArtifactSize,
  formatPlaybackTime,
  formatRecordingTime,
  isPending,
  isTerminal,
  makeArtifactId,
  makeRecorder,
  normalizeLevels,
  resampleLevels,
  useAudioAnalysis,
  useAudioPlayer,
  useAudioQueue,
  useDictation,
  useDurableRecording,
  useRecorder,
  useVoice
};
//# sourceMappingURL=index.js.map