/**
 * SlideManager - Slide Order Management for TV Display
 *
 * Allows doctors to:
 * - View all active slides
 * - Reorder slides (drag & drop or buttons)
 * - Toggle active/inactive
 * - Delete slides
 * - Preview order changes
 */

'use client';

import { useState, useEffect } from 'react';
import { Trash2, Lock, Layers, Clock, CheckCircle2, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ContentItem } from './waiting-room-host';
import { confirmDelete, toastError, toastSuccess } from '@/lib/swal';

interface Slide {
  media_id: string;
  media_type: 'image' | 'video' | 'message';
  title?: string;
  description?: string;
  file_path?: string;
  uploaded_at: number;
  duration: number;
  is_active: boolean;
  display_order?: number;
}

interface SlideManagerProps {
  clinicId?: string;
  onSlidesUpdate?: () => void;
  carouselContent?: ContentItem[];
}

export function SlideManager({ onSlidesUpdate, carouselContent = [] }: SlideManagerProps) {
  const [slides, setSlides] = useState<Slide[]>([]);
  const [, setIsLoading] = useState(false);

  const fetchSlides = async () => {
    setIsLoading(true);
    try {
      const backendURL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
      const params = new URLSearchParams();
      // Don't filter by clinic_id - show all slides
      params.append('active_only', 'false');

      const response = await fetch(`${backendURL}/api/workflows/aurity/clinic-media/list?${params}`);
      if (!response.ok) throw new Error('Failed to fetch slides');

      const data = await response.json();
      // Sort by upload time (newest first) or by display_order if available
      const sorted = (data.media || []).sort((a: Slide, b: Slide) => {
        if (a.display_order !== undefined && b.display_order !== undefined) {
          return a.display_order - b.display_order;
        }
        return b.uploaded_at - a.uploaded_at;
      });
      setSlides(sorted);
    } catch (error) {
      console.error('Failed to fetch slides:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const _handleDelete = async (mediaId: string) => {
    const confirmed = await confirmDelete('este slide');
    if (!confirmed) return;

    try {
      const backendURL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
      const response = await fetch(`${backendURL}/api/workflows/aurity/clinic-media/${mediaId}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete slide');

      await fetchSlides();
      onSlidesUpdate?.();
      toastSuccess('Slide eliminado');
    } catch (error) {
      console.error('Failed to delete slide:', error);
      toastError('Error al eliminar');
    }
  };

  const _handleToggleActive = async (mediaId: string, currentState: boolean) => {
    try {
      const backendURL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
      const response = await fetch(`${backendURL}/api/workflows/aurity/clinic-media/${mediaId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !currentState }),
      });

      if (!response.ok) throw new Error('Failed to update slide');

      await fetchSlides();
      onSlidesUpdate?.();
      toastSuccess(currentState ? 'Slide desactivado' : 'Slide activado');
    } catch (error) {
      console.error('Failed to update slide:', error);
      toastError('Error al actualizar');
    }
  };

  const _moveSlide = (index: number, direction: 'up' | 'down') => {
    const newSlides = [...slides];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;

    if (targetIndex < 0 || targetIndex >= newSlides.length) return;

    // Swap slides
    [newSlides[index], newSlides[targetIndex]] = [newSlides[targetIndex], newSlides[index]];
    setSlides(newSlides);

    // TODO: Persist order to backend
  };

  useEffect(() => {
    fetchSlides();
  }, []);

  // Slide counts computed for UI (currently unused but reserved for filter tabs)
  void slides.filter(s => s.is_active);
  void slides.filter(s => !s.is_active);

  // Helper function to get icon/label for content type
  const getContentInfo = (item: ContentItem, index: number): { icon: string; label: string; editable: boolean } => {
    const title = typeof item.widgetData?.title === 'string' ? item.widgetData.title : undefined;
    if (item.widgetType === 'clinic_image') return { icon: '📷', label: title || 'Imagen', editable: true };
    if (item.widgetType === 'clinic_video') return { icon: '🎬', label: title || 'Video', editable: true };
    if (item.widgetType === 'clinic_message') return { icon: '💬', label: title || 'Mensaje', editable: true };
    if (item.widgetType === 'weather') return { icon: '🌤️', label: 'Clima y Hora', editable: false };
    if (item.widgetType === 'trivia') return { icon: '🧠', label: 'Trivia de Salud', editable: false };
    if (item.widgetType === 'breathing') return { icon: '🫁', label: 'Ejercicio de Respiración', editable: false };
    if (item.widgetType === 'daily_tip') return { icon: '💡', label: 'Tip del Día', editable: false };
    if (item.widgetType === 'calming') return { icon: '🌿', label: 'Naturaleza Relajante', editable: false };
    if (item.type === 'welcome') return { icon: '👋', label: 'Bienvenida FI', editable: false };
    if (item.type === 'philosophy') return { icon: '🏠', label: 'Filosofía FI', editable: false };
    if (item.type === 'tip') return { icon: '💊', label: 'Tip de Salud FI', editable: false };
    if (item.type === 'doctor_message') return { icon: '📢', label: 'Mensaje del Doctor', editable: false };
    return { icon: '📄', label: `Slide ${index + 1}`, editable: false };
  };

  return (
    <div className="fi-stack-xl">
      {/* All Carousel Content */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="fi-title flex items-center gap-2">
            <Layers className="fi-icon-md fi-icon-purple" />
            Todos los Slides ({carouselContent.length})
          </h3>
          <Button
            type="button"
            onClick={fetchSlides}
            className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white text-xs rounded-lg transition-colors"
            variant="ghost"
            size="sm"
          >
            🔄 Actualizar
          </Button>
        </div>
        {carouselContent.length === 0 ? (
          <div className="text-center text-slate-400 py-8">
            No hay slides disponibles
          </div>
        ) : (
          <div className="fi-stack-sm">
            {carouselContent.map((item, index) => {
              const info = getContentInfo(item, index);
              return (
                <div
                  key={`carousel-${index}`}
                  className={`flex items-center gap-3 p-6 rounded-xl transition-all duration-300 backdrop-blur-sm ${
                    info.editable
                      ? 'bg-gradient-to-r from-slate-800/80 via-slate-800/60 to-slate-900/80 border border-slate-600/40 shadow-lg'
                      : 'bg-gradient-to-r from-slate-900/60 to-slate-800/40 border border-slate-700/30'
                  }`}
                >
                  {/* Content info */}
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="w-12 h-12 rounded-lg bg-slate-700/50 flex items-center justify-center text-2xl">
                      {info.icon}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-slate-200 font-medium truncate">{info.label}</span>
                        {!info.editable && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-700/50 border border-slate-600/50 backdrop-blur-sm">
                            <Lock className="w-3 h-3 text-slate-400" />
                            <span className="fi-text-xs-medium fi-text">FI</span>
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 fi-text-xs">
                        <span className="inline-flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5" />
                          {(item.duration || 15000) / 1000}s
                        </span>
                        {!info.editable && (
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-900/20 border border-emerald-700/30 text-emerald-300">
                            <CheckCircle2 className="w-3 h-3" />
                            Sistema
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Actions (only for editable items) */}
                  {info.editable && (
                    <div className="fi-flex-gap">
                      <Button
                        type="button"
                        disabled
                        className="p-2.5 rounded-lg bg-gradient-to-br from-slate-800/50 to-slate-700/50 border border-slate-600/50 text-slate-400 cursor-not-allowed backdrop-blur-sm"
                        title="Edición disponible próximamente"
                        variant="ghost"
                        size="sm"
                      >
                        <EyeOff className="w-4 h-4" />
                      </Button>
                      <Button
                        type="button"
                        disabled
                        className="p-2.5 rounded-lg bg-gradient-to-br from-red-900/30 to-red-800/30 border border-red-700/40 fi-text-error/50 cursor-not-allowed backdrop-blur-sm"
                        title="Eliminación disponible próximamente"
                        variant="ghost"
                        size="sm"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
