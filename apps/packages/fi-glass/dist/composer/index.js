'use client';

// src/composer/AutoResizeTextarea.tsx
import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState
} from "react";
import { jsx, jsxs } from "react/jsx-runtime";
var AutoResizeTextarea = forwardRef(function AutoResizeTextarea2({
  value,
  onChange,
  maxRows = 5,
  showCounter = false,
  maxLength,
  wrapperClassName = "",
  wrapperStyle,
  className = "",
  ...props
}, ref) {
  const textareaRef = useRef(null);
  useImperativeHandle(ref, () => textareaRef.current);
  const [rows, setRows] = useState(1);
  useEffect(() => {
    if (!textareaRef.current) return;
    const textarea = textareaRef.current;
    textarea.style.height = "auto";
    const lineHeight = 20;
    const newRows = Math.min(
      Math.ceil(textarea.scrollHeight / lineHeight),
      maxRows
    );
    setRows(newRows);
    textarea.style.height = `${newRows * lineHeight}px`;
    textarea.style.width = "100%";
  }, [value, maxRows]);
  const charCount = typeof value === "string" ? value.length : 0;
  const isNearLimit = maxLength && charCount > maxLength * 0.9;
  const isOverLimit = maxLength && charCount > maxLength;
  return /* @__PURE__ */ jsxs("div", { className: `relative ${wrapperClassName}`, style: wrapperStyle, children: [
    /* @__PURE__ */ jsx(
      "textarea",
      {
        ref: textareaRef,
        value,
        onChange,
        maxLength,
        className: `
          resize-none
          ${className}
        `,
        rows,
        ...props
      }
    ),
    showCounter && maxLength && /* @__PURE__ */ jsxs("div", { className: isOverLimit ? "chat-char-counter-error" : isNearLimit ? "chat-char-counter-warning" : "chat-char-counter-ok", children: [
      charCount,
      "/",
      maxLength
    ] })
  ] });
});

// src/composer/Composer.tsx
import { jsx as jsx2 } from "react/jsx-runtime";
function Composer({
  message,
  loading = false,
  placeholder = "Escribe tu mensaje...",
  onMessageChange,
  onSend,
  maxRows = 5,
  areaClassName,
  wrapperClassName,
  wrapperStyle,
  textareaClassName,
  textareaRef
}) {
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };
  return /* @__PURE__ */ jsx2("div", { className: areaClassName, children: /* @__PURE__ */ jsx2(
    AutoResizeTextarea,
    {
      ref: textareaRef,
      value: message,
      onChange: (e) => onMessageChange(e.target.value),
      onKeyDown: handleKeyDown,
      placeholder,
      disabled: loading,
      maxRows,
      showCounter: false,
      wrapperClassName,
      wrapperStyle,
      className: textareaClassName
    }
  ) });
}
export {
  AutoResizeTextarea,
  Composer
};
//# sourceMappingURL=index.js.map