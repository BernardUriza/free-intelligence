'use client';

import {
  useTouchTargetStyle,
  withTouchTarget
} from "./chunk-SMPLGG7E.js";

// src/shell/ChatFilePreview.tsx
import {
  FileText,
  FileCode,
  Image as ImageIcon,
  File,
  X,
  Loader2,
  CheckCircle,
  AlertCircle
} from "lucide-react";
import { Fragment, jsx, jsxs } from "react/jsx-runtime";
var FILE_ICONS = {
  "application/pdf": FileText,
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FileText,
  "application/msword": FileText,
  "text/plain": File,
  "text/markdown": FileCode,
  "image/png": ImageIcon,
  "image/jpeg": ImageIcon,
  "image/jpg": ImageIcon
};
function formatFileSize(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
function getFileIcon(file) {
  return FILE_ICONS[file.type] || File;
}
function ChatFilePreview({
  file,
  status,
  progress = 0,
  error,
  onCancel
}) {
  const FileIcon = getFileIcon(file);
  useTouchTargetStyle();
  const isCompleted = status === "indexed";
  const isError = status === "error";
  const isUploading = status === "uploading";
  const isProcessing = status === "processing";
  const isAwaitingUser = status === "pending_instructions";
  return /* @__PURE__ */ jsxs("div", { className: `
      flex items-center gap-3 p-3 rounded-xl border
      ${isError ? "bg-red-900/20 border-red-700/50" : isCompleted ? "bg-emerald-900/20 border-emerald-700/50" : "bg-slate-800/80 border-slate-700/50"}
      transition-colors duration-200
    `, children: [
    /* @__PURE__ */ jsx("div", { className: `
        p-2 rounded-lg
        ${isError ? "bg-red-900/50" : isCompleted ? "bg-emerald-900/50" : "bg-slate-700"}
      `, children: isProcessing ? /* @__PURE__ */ jsx(Loader2, { className: "w-5 h-5 text-slate-300 animate-spin" }) : isCompleted ? /* @__PURE__ */ jsx(CheckCircle, { className: "w-5 h-5 text-emerald-400" }) : isError ? /* @__PURE__ */ jsx(AlertCircle, { className: "w-5 h-5 text-red-400" }) : /* @__PURE__ */ jsx(FileIcon, { className: "w-5 h-5 text-slate-300" }) }),
    /* @__PURE__ */ jsxs("div", { className: "flex-1 min-w-0", children: [
      /* @__PURE__ */ jsx("p", { className: "text-sm font-medium text-slate-100 truncate", title: file.name, children: file.name }),
      /* @__PURE__ */ jsxs("div", { className: "flex items-center gap-2 text-xs text-slate-400", children: [
        /* @__PURE__ */ jsx("span", { children: formatFileSize(file.size) }),
        isUploading && /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsx("span", { children: "-" }),
          /* @__PURE__ */ jsx("span", { className: "text-slate-300", children: progress < 100 ? `Subiendo... ${progress}%` : "Completado" })
        ] }),
        isAwaitingUser && /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsx("span", { children: "-" }),
          /* @__PURE__ */ jsx("span", { className: "text-slate-300", children: "Elige c\xF3mo usarlo" })
        ] }),
        isProcessing && /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsx("span", { children: "-" }),
          /* @__PURE__ */ jsx("span", { className: "text-slate-300", children: "Procesando..." })
        ] }),
        isCompleted && /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsx("span", { children: "-" }),
          /* @__PURE__ */ jsx("span", { className: "text-emerald-400", children: "Indexado" })
        ] }),
        isError && error && /* @__PURE__ */ jsxs(Fragment, { children: [
          /* @__PURE__ */ jsx("span", { children: "-" }),
          /* @__PURE__ */ jsx("span", { className: "text-red-400 truncate", title: error, children: error })
        ] })
      ] }),
      isUploading && /* @__PURE__ */ jsx("div", { className: "mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden", children: /* @__PURE__ */ jsx(
        "div",
        {
          className: "h-full rounded-full bg-slate-300 transition-[width] duration-300",
          style: { width: `${progress}%` }
        }
      ) })
    ] }),
    !isCompleted && !isProcessing && /* @__PURE__ */ jsx(
      "button",
      {
        type: "button",
        onClick: onCancel,
        className: withTouchTarget(
          "shrink-0 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-slate-100"
        ),
        "aria-label": "Cancelar",
        title: "Cancelar",
        children: /* @__PURE__ */ jsx(X, { className: "h-4 w-4" })
      }
    )
  ] });
}

export {
  ChatFilePreview
};
//# sourceMappingURL=chunk-JK3NSWFZ.js.map