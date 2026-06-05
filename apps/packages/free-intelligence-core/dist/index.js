// src/agent/state.ts
function initialAgentTurnState() {
  return {
    plan: null,
    steps: [],
    text: "",
    sources: [],
    meta: null,
    status: "thinking"
  };
}
function applyAgentEvent(state, event) {
  const streamingStatus = state.status === "thinking" ? "streaming" : state.status;
  switch (event.type) {
    case "open":
      return state;
    case "plan":
      return {
        ...state,
        plan: {
          steps: event.steps.map((label) => ({ label, status: "pending" })),
          rejection: null,
          amended: null,
          outcome: null
        },
        status: streamingStatus
      };
    case "plan_rejected":
      return state.plan ? { ...state, plan: { ...state.plan, rejection: event.rejection } } : { ...state, plan: { steps: [], rejection: event.rejection } };
    case "step_started": {
      if (!state.plan) return state;
      const idx = event.index;
      if (idx < 0 || idx >= state.plan.steps.length) return state;
      const steps = state.plan.steps.map((s, i) => {
        if (i < idx && (s.status === "pending" || s.status === "running")) {
          return { ...s, status: "done" };
        }
        if (i === idx) return { ...s, status: "running" };
        return s;
      });
      return { ...state, plan: { ...state.plan, steps } };
    }
    case "step_done": {
      if (!state.plan) return state;
      const idx = event.index;
      if (idx < 0 || idx >= state.plan.steps.length) return state;
      const steps = state.plan.steps.map((s, i) => {
        if (i !== idx) return s;
        const patch = { ...s, status: event.status };
        if (event.status === "done") {
          if (event.summary) patch.summary = event.summary;
        } else if (event.error) {
          patch.error = event.error;
        }
        return patch;
      });
      return { ...state, plan: { ...state.plan, steps } };
    }
    case "step_noted": {
      if (!state.plan) return state;
      const idx = event.index;
      if (idx < 0 || idx >= state.plan.steps.length) return state;
      const steps = state.plan.steps.map(
        (s, i) => i === idx ? { ...s, note: event.note } : s
      );
      return { ...state, plan: { ...state.plan, steps } };
    }
    case "plan_amended":
      return state.plan ? { ...state, plan: { ...state.plan, amended: event.action } } : state;
    case "plan_cancelled": {
      if (!state.plan) return state;
      const steps = state.plan.steps.map(
        (s) => s.status === "pending" || s.status === "running" ? { ...s, status: "cancelled" } : s
      );
      return { ...state, plan: { ...state.plan, steps, outcome: "cancelled" } };
    }
    case "plan_completed":
      return state.plan ? { ...state, plan: { ...state.plan, outcome: "completed" } } : state;
    case "plan_failed":
      return state.plan ? { ...state, plan: { ...state.plan, outcome: "failed" } } : state;
    case "tool_call": {
      const existing = event.call.id != null ? state.steps.findIndex((c) => c.id === event.call.id) : -1;
      const steps = existing >= 0 ? state.steps.map((c, i) => i === existing ? event.call : c) : [...state.steps, event.call];
      return { ...state, steps, status: streamingStatus };
    }
    case "text":
      return {
        ...state,
        text: state.text + event.delta,
        status: streamingStatus
      };
    case "result": {
      const text = event.text.trim() ? event.text : state.text;
      const plan = state.plan ? {
        ...state.plan,
        steps: state.plan.steps.map(
          (s) => s.status === "pending" || s.status === "running" ? { ...s, status: "done" } : s
        )
      } : state.plan;
      return {
        ...state,
        text,
        plan,
        sources: event.sources ?? state.sources,
        meta: event.meta ?? state.meta,
        status: "done"
      };
    }
    case "meta":
      return { ...state, meta: event.meta };
    case "error":
      return { ...state, status: "error", errorMessage: event.message };
    case "done":
      return state.status === "thinking" || state.status === "streaming" ? { ...state, status: "done" } : state;
    default:
      return state;
  }
}
export {
  applyAgentEvent,
  initialAgentTurnState
};
//# sourceMappingURL=index.js.map