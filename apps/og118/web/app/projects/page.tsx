import { Auth0Wrapper } from '@/components/Auth0Wrapper';
import { AuthGate } from '@/components/AuthGate';
import { Og118ProjectsPage } from '@/components/projects/Og118ProjectsPage';

// ONE static route for both the index and the detail, with `?p=<id>` selecting
// the project.
//
// og118 is a Next STATIC EXPORT (`output: 'export'`), and a filesystem segment
// `projects/[id]` needs `generateStaticParams` at build time — impossible for
// ids minted per account at runtime. Emitting the segment with no params would
// still work while clicking inside the SPA and then 404 on the SWA for anyone
// who refreshes or opens a shared link, because there is no
// `staticwebapp.config.json` fallback. A query param is deep-linkable and
// back-button-correct with zero infra change.
export default function Page() {
  return (
    <Auth0Wrapper>
      <AuthGate>
        <Og118ProjectsPage />
      </AuthGate>
    </Auth0Wrapper>
  );
}
