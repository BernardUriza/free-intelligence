import { useRouter } from 'next/navigation';
import { CheckCircle2 } from 'lucide-react';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { Button } from '@/components/ui/button';

/** Shown when running inside Tauri desktop — user already has the app. */
export function TauriInstalledView() {
  const router = useRouter();

  return (
    <AppTemplate backgroundGradient="none" maxWidth="none">
      <div className="dl-tauri-screen">
        <div className="dl-tauri-card">
          <CheckCircle2 className="dl-tauri-check" />
          <h1 className="dl-tauri-title">Ya tienes Aurity Desktop</h1>
          <p className="dl-tauri-text">
            Estás corriendo la aplicación de escritorio. No necesitas descargar nada más.
          </p>
          <Button onClick={() => router.push('/chat')}>Ir al Chat</Button>
        </div>
      </div>
    </AppTemplate>
  );
}
