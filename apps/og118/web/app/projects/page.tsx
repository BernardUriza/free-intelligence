import { Auth0Wrapper } from '@/components/Auth0Wrapper';
import { AuthGate } from '@/components/AuthGate';
import { proyectosActivos } from '@/lib/og118Flags';
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
  // NEXT_PUBLIC_OG118_PROYECTOS off → this route still EXISTS (a static export
  // emits every page; deleting the file is what Bernard asked not to do), but it
  // ships a notice instead of the app. The whole client tree — Auth0Wrapper,
  // AuthGate, the projects hooks — is never mounted, so a bookmarked
  // `/projects/` cannot fire a single request at a `/projects` API that the
  // backend, with its own flag off, answers with a real 404.
  if (!proyectosActivos()) {
    return (
      <main className="og-projects-shell">
        <p className="og-projects-note">
          Proyectos no está disponible por ahora.{' '}
          <a className="og-projects-nav" href="/">
            Volver al chat →
          </a>
        </p>
      </main>
    );
  }

  return (
    <Auth0Wrapper>
      <AuthGate>
        <Og118ProjectsPage />
      </AuthGate>
    </Auth0Wrapper>
  );
}
