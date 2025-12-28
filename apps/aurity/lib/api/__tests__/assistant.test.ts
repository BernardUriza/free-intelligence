// Mock external workspace packages before importing the module under test
vi.mock('@aurity-standalone/auth', () => ({
  getRoles: (_claims: unknown) => [] as string[],
}));

vi.mock('@aurity-standalone/observability', () => ({
  sanitizeMessagePreview: (_s: string) => _s,
  hash8: (_s: string) => 'deadbeef',
}));

import { assistantApi } from '../assistant';
import { api } from '../client';

vi.mock('../client', () => ({
  api: {
    post: vi.fn(),
  },
}));

describe('assistantApi.chat persona normalization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('sends persona string when context.persona is string', async () => {
    (api.post as unknown as vi.Mock).mockResolvedValue({ id: '1', model: 'm', choices: [{ message: { role: 'assistant', content: 'ok' }, finish_reason: 'stop' }], persona: 'onboarding_guide' });

    await assistantApi.chat({ message: 'hello', context: { persona: 'onboarding_guide' } as any });

    expect(api.post).toHaveBeenCalled();
    const calledWith = (api.post as unknown as vi.Mock).mock.calls[0][1];
    expect(calledWith.persona).toBe('onboarding_guide');
  });

  it('extracts persona id when context.persona is object', async () => {
    (api.post as unknown as vi.Mock).mockResolvedValue({ id: '1', model: 'm', choices: [{ message: { role: 'assistant', content: 'ok' }, finish_reason: 'stop' }], persona: 'onboarding_guide' });

    await assistantApi.chat({ message: 'hello', context: { persona: { id: 'onboarding_guide', name: 'Onboarding Guide' } } as any });

    expect(api.post).toHaveBeenCalled();
    const calledWith = (api.post as unknown as vi.Mock).mock.calls[0][1];
    expect(calledWith.persona).toBe('onboarding_guide');
  });

  it('falls back to general_assistant when persona missing', async () => {
    (api.post as unknown as vi.Mock).mockResolvedValue({ id: '1', model: 'm', choices: [{ message: { role: 'assistant', content: 'ok' }, finish_reason: 'stop' }], persona: 'general_assistant' });

    await assistantApi.chat({ message: 'hello', context: {} });

    expect(api.post).toHaveBeenCalled();
    const calledWith = (api.post as unknown as vi.Mock).mock.calls[0][1];
    expect(calledWith.persona).toBe('general_assistant');
  });
});
