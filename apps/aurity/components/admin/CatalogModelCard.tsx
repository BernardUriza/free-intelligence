/**
 * CatalogModelCard Component
 *
 * Displays a model from the catalog (GPT4All, HuggingFace, Ollama)
 * with install/delete actions and source badges.
 */

'use client';

import { Download, Trash2, Check, HardDrive, Cpu, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { CatalogModel } from '@/lib/api/catalog';
import { SOURCE_INFO, QUANT_INFO, formatBytes } from '@/lib/api/catalog';

interface CatalogModelCardProps {
  model: CatalogModel;
  isInstalling?: boolean;
  installProgress?: number;
  onInstall: () => void;
  onDelete?: () => void;
}

// Strip HTML tags for clean text display
function stripHtml(html: string): string {
  return html
    .replace(/<[^>]*>/g, '') // Remove HTML tags
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ') // Collapse whitespace
    .trim();
}

export function CatalogModelCard({
  model,
  isInstalling = false,
  installProgress = 0,
  onInstall,
  onDelete,
}: CatalogModelCardProps) {
  const sourceInfo = SOURCE_INFO[model.source];
  const quantInfo = QUANT_INFO[model.quantization];
  const cleanDescription = model.description ? stripHtml(model.description) : null;

  return (
    <div className={model.is_installed ? 'admin-card-installed' : 'admin-card-default'}>
      {/* Header */}
      <div className="admin-card-header">
        <div className="admin-card-header-inner">
          <span className="text-2xl" title={sourceInfo.label}>{sourceInfo.icon}</span>
          <div>
            <h3 className="admin-card-title" title={model.name}>{model.name}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`admin-source-badge ${sourceInfo.color}`}>{sourceInfo.label}</span>
              {model.is_installed && (
                <span className="admin-installed-badge">
                  <Check className="admin-installed-badge-icon" />
                  Instalado
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Description */}
      {cleanDescription && <p className="admin-card-description">{cleanDescription}</p>}

      {/* Stats Grid */}
      <div className="admin-card-stats-grid">
        <div className="admin-card-stat">
          <HardDrive className="admin-card-stat-icon" />
          <span className="admin-card-stat-value">{formatBytes(model.size_bytes)}</span>
        </div>
        {model.ram_required_gb && (
          <div className="admin-card-stat">
            <Cpu className="admin-card-stat-icon" />
            <span className="admin-card-stat-value">{model.ram_required_gb.toFixed(1)} GB RAM</span>
          </div>
        )}
        <div className="admin-card-stat">
          <FileText className="admin-card-stat-icon" />
          <span className="admin-card-stat-value">{quantInfo.label}</span>
        </div>
        {model.parameters && (
          <div className="admin-card-stat">
            <span className="text-slate-400">P:</span>
            <span className="admin-card-stat-value">{model.parameters}</span>
          </div>
        )}
      </div>

      {/* Tags */}
      {model.tags.length > 0 && (
        <div className="admin-card-tags">
          {model.tags.slice(0, 4).map((tag) => (
            <span key={tag} className="admin-card-tag">{tag}</span>
          ))}
          {model.tags.length > 4 && <span className="admin-card-tag-more">+{model.tags.length - 4}</span>}
        </div>
      )}

      {/* Progress Bar (when installing) */}
      {isInstalling && (
        <div className="admin-progress-container">
          <div className="admin-progress-header">
            <span>Instalando...</span>
            <span>{installProgress}%</span>
          </div>
          <div className="admin-progress-bar">
            <div className="admin-progress-fill" style={{ width: `${installProgress}%` }} />
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="admin-card-actions">
        {!model.is_installed ? (
          <Button onClick={onInstall} disabled={isInstalling} className="admin-card-btn-install" icon={Download} type="button">
            {isInstalling ? 'Instalando...' : 'Instalar'}
          </Button>
        ) : (
          <>
            <div className="admin-card-btn-installed">
              <Check className="w-4 h-4" />
              Listo para usar
            </div>
            {onDelete && model.source === 'ollama' && (
              <Button onClick={onDelete} className="admin-card-btn-delete" title="Eliminar modelo" icon={Trash2} variant="ghost" size="sm" type="button" />
            )}
          </>
        )}
      </div>

      {/* Filename (small) */}
      <div className="admin-card-footer">
        <p className="admin-card-footer-text" title={model.filename}>{model.filename}</p>
      </div>
    </div>
  );
}
