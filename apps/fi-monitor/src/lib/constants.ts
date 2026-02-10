export const SERVICE_PORTS = {
  OLLAMA: 11434,
  RAG: 11435,
  GATEWAY: 11400,
} as const

export const SERVICE_URLS = {
  OLLAMA: `http://localhost:${SERVICE_PORTS.OLLAMA}`,
  RAG: `http://localhost:${SERVICE_PORTS.RAG}`,
  GATEWAY: `http://localhost:${SERVICE_PORTS.GATEWAY}`,
} as const
