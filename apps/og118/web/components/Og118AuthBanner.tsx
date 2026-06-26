'use client';

interface Og118AuthBannerProps {
  token: string;
  onTokenChange: (token: string) => void;
  onSave: () => void;
}

export function Og118AuthBanner({ token, onTokenChange, onSave }: Og118AuthBannerProps) {
  return (
    <div className="og-auth-banner" data-ref="og118-auth-banner">
      <span className="og-auth-banner-label">
        Acceso restringido — pega tu token de og118 para continuar.
      </span>
      <div className="og-auth-banner-row">
        <input
          type="password"
          className="og-auth-banner-input"
          value={token}
          onChange={(e) => onTokenChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') onSave();
          }}
          placeholder="og118 access token"
          data-ref="og118-auth-token-input"
        />
        <button className="og-auth-banner-save" onClick={onSave} data-ref="og118-auth-save">
          Guardar
        </button>
      </div>
    </div>
  );
}
