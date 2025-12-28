let started: Promise<void> | null = null;

const MOCK_ENV_FLAGS = ['NEXT_PUBLIC_USE_MOCKS', 'NEXT_PUBLIC_MOCK_BACKEND'];

function readEnvFlag(): boolean {
  if (typeof process === 'undefined') return false;
  return MOCK_ENV_FLAGS.some((key) => (process.env as Record<string, string | undefined>)[key] === 'true');
}

function readClientFlag(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return localStorage.getItem('USE_MOCKS') === 'true';
  } catch {
    return false;
  }
}

export function shouldUseMocks(): boolean {
  return readEnvFlag() || readClientFlag();
}

export async function startMockWorker(): Promise<void> {
  if (typeof window === 'undefined') return;
  if (started) return started;

  started = import('./browser').then(async ({ worker }) => {
    await worker.start({ onUnhandledRequest: 'bypass' });
  });

  return started;
}
