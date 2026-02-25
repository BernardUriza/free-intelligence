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
import { listClinicMedia, deleteClinicMedia, updateClinicMedia } from '@/lib/api/clinic-media';
import {
  Trash2,
  Lock,
  Layers,
  Clock,
  CheckCircle2,
  EyeOff,
  Camera,
  Video,
  MessageCircle,
  CloudSun,
  Brain,
  Activity,
  Lightbulb,
  Leaf,
  Hand,
  Home,
  Pill,
  Megaphone,
  FileText,
  RefreshCw,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
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
      const media = await listClinicMedia({ activeOnly: false });
      // Sort by upload time (newest first) or by display_order if available
      const sorted = (media as Slide[]).sort((a: Slide, b: Slide) => {
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
      await deleteClinicMedia(mediaId);

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
      await updateClinicMedia(mediaId, { is_active: !currentState });

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

  };

  useEffect(() => {
    fetchSlides();
  }, []);

  // Helper function to get icon/label for content type
  const getContentInfo = (item: ContentItem, index: number): { icon: LucideIcon; label: string; editable: boolean } => {
    const title = typeof item.widgetData?.title === 'string' ? item.widgetData.title : undefined;
    if (item.widgetType === 'clinic_image') return { icon: Camera, label: title || 'Imagen', editable: true };
    if (item.widgetType === 'clinic_video') return { icon: Video, label: title || 'Video', editable: true };
    if (item.widgetType === 'clinic_message') return { icon: MessageCircle, label: title || 'Mensaje', editable: true };
    if (item.widgetType === 'weather') return { icon: CloudSun, label: 'Clima y Hora', editable: false };
    if (item.widgetType === 'trivia') return { icon: Brain, label: 'Trivia de Salud', editable: false };
    if (item.widgetType === 'breathing') return { icon: Activity, label: 'Ejercicio de Respiración', editable: false };
    if (item.widgetType === 'daily_tip') return { icon: Lightbulb, label: 'Tip del Día', editable: false };
    if (item.widgetType === 'calming') return { icon: Leaf, label: 'Naturaleza Relajante', editable: false };
    if (item.type === 'welcome') return { icon: Hand, label: 'Bienvenida FI', editable: false };
    if (item.type === 'philosophy') return { icon: Home, label: 'Filosofía FI', editable: false };
    if (item.type === 'tip') return { icon: Pill, label: 'Tip de Salud FI', editable: false };
    if (item.type === 'doctor_message') return { icon: Megaphone, label: 'Mensaje del Doctor', editable: false };
    return { icon: FileText, label: `Slide ${index + 1}`, editable: false };
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
            className="slide-refresh-btn"
            variant="ghost"
            size="sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Actualizar
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
                    <div className="slide-thumb-icon">
                      <info.icon className="w-6 h-6" strokeWidth={1.5} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-slate-200 font-medium truncate">{info.label}</span>
                        {!info.editable && (
                          <span className="slide-fi-badge">
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
                          <span className="slide-system-badge">
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
                        className="slide-btn-disabled"
                        title="Edición disponible próximamente"
                        variant="ghost"
                        size="sm"
                      >
                        <EyeOff className="w-4 h-4" />
                      </Button>
                      <Button
                        type="button"
                        disabled
                        className="slide-btn-delete-disabled"
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
