import { Og118AgentChat } from '@/components/Og118AgentChat';
import { Auth0Wrapper } from '@/components/Auth0Wrapper';
import { AuthGate } from '@/components/AuthGate';

// "/" is og118, chat-first + glass-box: AgentHook + fi-glass/agent panels.
// In auth0 mode Auth0Wrapper provides the SPA session + AuthGate requires login;
// both are passthroughs in bearer mode (no behavior change until the cutover).
export default function Page() {
  return (
    <Auth0Wrapper>
      <AuthGate>
        <Og118AgentChat />
      </AuthGate>
    </Auth0Wrapper>
  );
}
