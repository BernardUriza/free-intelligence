/**
 * MediaUploader - Multimedia Upload Component for TV Display
 *
 * Card: FI-UI-FEAT-TVD-001
 * Allows doctors to upload images, videos, and custom messages
 * for waiting room TV display
 */

'use client';

import { useState, useRef, useEffect } from 'react';
import { Trash2, Eye, EyeOff, CloudUpload, Send, Layers, Loader2, Inbox } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { confirmDelete, toastError, toastSuccess, showWarning } from '@/lib/swal';

interface MediaUploaderProps {
  /** Callback when media is uploaded */
  onMediaUpload: (media: UploadedMedia) => void;

  /** Clinic ID for categorization */
  clinicId?: string;

  /** Doctor ID (Auth0 sub) */
  doctorId?: string;
}

export interface UploadedMedia {
  mediaId: string;
  mediaType: 'image' | 'video' | 'message';
  title?: string;
  description?: string;
  url?: string; // For image/video
  message?: string; // For text messages
  duration: number; // Display duration in ms
}

interface MediaItem {
  media_id: string;
  media_type: 'image' | 'video' | 'message';
  title?: string;
  description?: string;
  file_path?: string;
  uploaded_at: number;
  duration: number;
  is_active: boolean;
}

export function MediaUploader({ onMediaUpload, clinicId, doctorId }: MediaUploaderProps) {
  const [activeTab, setActiveTab] = useState<'image' | 'video' | 'message'>('message');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [messageContent, setMessageContent] = useState('');
  const [duration, setDuration] = useState(15); // seconds
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [mediaList, setMediaList] = useState<MediaItem[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file size (50MB)
    if (file.size > 50 * 1024 * 1024) {
      await showWarning('Archivo demasiado grande', 'El tamaño máximo es 50MB');
      return;
    }

    // Validate file type
    const validImageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    const validVideoTypes = ['video/mp4', 'video/webm', 'video/quicktime'];

    if (activeTab === 'image' && !validImageTypes.includes(file.type)) {
      await showWarning('Tipo no válido', 'Use imágenes JPEG, PNG, GIF o WebP');
      return;
    }

    if (activeTab === 'video' && !validVideoTypes.includes(file.type)) {
      await showWarning('Tipo no válido', 'Use videos MP4, WebM o QuickTime');
      return;
    }

    await uploadFile(file);
  };

  const uploadFile = async (file: File) => {
    setIsUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('media_type', activeTab);
      if (title) formData.append('title', title);
      if (description) formData.append('description', description);
      formData.append('duration', String(duration * 1000)); // Convert to ms
      if (clinicId) formData.append('clinic_id', clinicId);
      if (doctorId) formData.append('doctor_id', doctorId);

      const backendURL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
      const response = await fetch(`${backendURL}/api/workflows/aurity/clinic-media/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();

      // Notify parent component
      onMediaUpload({
        mediaId: data.media_id,
        mediaType: activeTab,
        title: title || file.name,
        description,
        url: `/api/workflows/aurity/clinic-media/${data.media_id}/file`,
        duration: duration * 1000,
      });

      // Reset form
      setTitle('');
      setDescription('');
      setUploadProgress(100);

      // Refresh media list
      await fetchMediaList();

      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
      }, 1000);
    } catch (error) {
      console.error('Upload failed:', error);
      toastError('Error al subir archivo');
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleMessageSubmit = async () => {
    if (!messageContent.trim()) {
      await showWarning('Campo vacío', 'El mensaje no puede estar vacío');
      return;
    }

    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('media_type', 'message');
      formData.append('message_content', messageContent.trim());
      if (title) formData.append('title', title);
      formData.append('duration', String(duration * 1000)); // Convert to ms
      if (clinicId) formData.append('clinic_id', clinicId);
      if (doctorId) formData.append('doctor_id', doctorId);

      const backendURL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
      const response = await fetch(`${backendURL}/api/workflows/aurity/clinic-media/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      const data = await response.json();

      // Notify parent component
      onMediaUpload({
        mediaId: data.media_id,
        mediaType: 'message',
        title: title || 'Mensaje Personalizado',
        message: messageContent.trim(),
        duration: duration * 1000,
      });

      // Reset form
      setTitle('');
      setDescription('');
      setMessageContent('');

      // Refresh media list
      await fetchMediaList();

      setIsUploading(false);
    } catch (error) {
      console.error('Upload failed:', error);
      toastError('Error al enviar mensaje');
      setIsUploading(false);
    }
  };

  const fetchMediaList = async () => {
    setIsLoadingList(true);
    try {
      const backendURL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
      const params = new URLSearchParams();
      if (clinicId) params.append('clinic_id', clinicId);
      params.append('active_only', 'false');

      const response = await fetch(`${backendURL}/api/workflows/aurity/clinic-media/list?${params}`);
      if (!response.ok) throw new Error('Failed to fetch media list');

      const data = await response.json();
      setMediaList(data.media || []);
    } catch (error) {
      console.error('Failed to fetch media list:', error);
    } finally {
      setIsLoadingList(false);
    }
  };

  const handleDelete = async (mediaId: string) => {
    const confirmed = await confirmDelete('este contenido');
    if (!confirmed) return;

    try {
      const backendURL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
      const response = await fetch(`${backendURL}/api/workflows/aurity/clinic-media/${mediaId}`, {
        method: 'DELETE',
      });

      if (!response.ok) throw new Error('Failed to delete media');

      // Refresh list
      await fetchMediaList();
      toastSuccess('Contenido eliminado');
    } catch (error) {
      console.error('Failed to delete media:', error);
      toastError('Error al eliminar');
    }
  };

  const handleToggleActive = async (mediaId: string, currentState: boolean) => {
    try {
      const backendURL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001';
      const response = await fetch(`${backendURL}/api/workflows/aurity/clinic-media/${mediaId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !currentState }),
      });

      if (!response.ok) throw new Error('Failed to update media');

      // Refresh list
      await fetchMediaList();
      toastSuccess(currentState ? 'Contenido desactivado' : 'Contenido activado');
    } catch (error) {
      console.error('Failed to update media:', error);
      toastError('Error al actualizar');
    }
  };

  // Load media list on mount
  useEffect(() => {
    fetchMediaList();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="px-6 py-4 bg-slate-900/50 fi-border-bottom">
        <h3 className="fi-title flex items-center gap-2">
          <CloudUpload className="fi-icon-md fi-icon-cyan" />
          Subir Contenido al TV
        </h3>
        <p className="fi-subtitle">Imágenes, videos o mensajes personalizados</p>
      </div>

      {/* Tabs */}
      <div className="flex fi-border-bottom">
        <Button
          type="button"
          onClick={() => setActiveTab('message')}
          className={`fi-tab fi-tab-full ${
            activeTab === 'message' ? 'fi-tab-active-cyan' : 'fi-tab-inactive-hover-bg'
          }`}
          variant={activeTab === 'message' ? 'cyan' : 'ghost'}
          size="sm"
        >
          Mensaje
        </Button>
        <Button
          type="button"
          onClick={() => setActiveTab('image')}
          className={`fi-tab fi-tab-full ${
            activeTab === 'image' ? 'fi-tab-active-cyan' : 'fi-tab-inactive-hover-bg'
          }`}
          variant={activeTab === 'image' ? 'cyan' : 'ghost'}
          size="sm"
        >
          Imagen
        </Button>
        <Button
          type="button"
          onClick={() => setActiveTab('video')}
          className={`fi-tab fi-tab-full ${
            activeTab === 'video' ? 'fi-tab-active-cyan' : 'fi-tab-inactive-hover-bg'
          }`}
          variant={activeTab === 'video' ? 'cyan' : 'ghost'}
          size="sm"
        >
          Video
        </Button>
      </div>

      {/* Content */}
      <div className="p-6 fi-stack-lg">
        {/* Title Input (optional) */}
        <div>
          <label className="fi-label">
            Título (opcional)
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Título del contenido"
            className="fi-input-cyan"
            maxLength={100}
          />
        </div>

        {/* Message Tab */}
        {activeTab === 'message' && (
          <div>
            <label className="fi-label">
              Mensaje *
            </label>
            <textarea
              value={messageContent}
              onChange={(e) => setMessageContent(e.target.value)}
              placeholder="Escribe tu mensaje personalizado para los pacientes..."
              className="fi-input-cyan resize-none"
              rows={4}
              maxLength={500}
            />
            <p className="fi-text-xs-muted mt-1">
              {messageContent.length}/500 caracteres
            </p>
          </div>
        )}

        {/* File Upload (Image/Video) */}
        {(activeTab === 'image' || activeTab === 'video') && (
          <>
            <div>
              <label className="fi-label">
                Descripción (opcional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Descripción del contenido..."
                className="fi-input-cyan resize-none"
                rows={2}
                maxLength={200}
              />
            </div>

            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept={activeTab === 'image' ? 'image/*' : 'video/*'}
                onChange={handleFileSelect}
                className="hidden"
              />
              <Button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="w-full px-6 py-8 border-2 border-dashed border-slate-600 rounded-lg hover:border-cyan-500 hover:bg-slate-900/30 transition-colors fi-disabled"
                variant="ghost"
                size="lg"
                fullWidth
              >
                <div className="flex flex-col items-center gap-2">
                  <CloudUpload className="w-12 h-12 text-slate-400" />
                  <p className="text-sm font-medium fi-text">
                    Haz clic para seleccionar {activeTab === 'image' ? 'imagen' : 'video'}
                  </p>
                  <p className="fi-text-xs-muted">
                    {activeTab === 'image' ? 'JPEG, PNG, GIF, WebP' : 'MP4, WebM, QuickTime'} · Máx 50MB
                  </p>
                </div>
              </Button>
            </div>
          </>
        )}

        {/* Duration Input */}
        <div>
          <label className="fi-label">
            Duración en pantalla
          </label>
          <div className="fi-flex-gap-md">
            <input
              type="range"
              min="5"
              max="60"
              step="5"
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="flex-1"
            />
            <span className="text-white font-medium w-16 text-right">{duration}s</span>
          </div>
        </div>

        {/* Upload Progress */}
        {isUploading && (
          <div>
            <div className="w-full bg-slate-700 rounded-full h-2 overflow-hidden">
              <div
                className="bg-cyan-500 h-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="fi-text-xs mt-1 text-center">
              {uploadProgress < 100 ? 'Subiendo...' : 'Completado'}
            </p>
          </div>
        )}

        {/* Submit Button */}
        {activeTab === 'message' && (
          <Button
            onClick={handleMessageSubmit}
            disabled={isUploading || !messageContent.trim()}
            variant="cyan"
            size="lg"
            icon={Send}
            loading={isUploading}
            fullWidth
          >
            {isUploading ? 'Enviando...' : 'Agregar al TV'}
          </Button>
        )}
      </div>

      {/* Media List */}
      <div className="bg-slate-800/50 border border-slate-700 rounded-lg overflow-hidden">
        <div className="px-6 py-4 bg-slate-900/50 fi-border-bottom">
          <h3 className="fi-title flex items-center gap-2">
            <Layers className="fi-icon-md fi-icon-purple" />
            Contenido Subido ({mediaList.length})
          </h3>
        </div>

        <div className="p-6">
          {isLoadingList ? (
            <div className="text-center py-8">
              <Loader2 className="w-8 h-8 animate-spin fi-text-purple mx-auto" />
              <p className="fi-subtitle mt-2">Cargando...</p>
            </div>
          ) : mediaList.length === 0 ? (
            <div className="text-center py-8">
              <Inbox className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <p className="fi-subtitle">No hay contenido subido aún</p>
              <p className="fi-text-xs-muted mt-1">Sube imágenes, videos o mensajes arriba</p>
            </div>
          ) : (
            <div className="space-y-3">
              {mediaList.map((item) => (
                <div
                  key={item.media_id}
                  className="flex items-center justify-between p-4 bg-slate-900/50 border border-slate-700 rounded-lg hover:border-purple-500/50 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <span className={`px-2 py-0.5 fi-text-xs-medium rounded ${
                        item.media_type === 'image' ? 'bg-blue-900/50 text-blue-300' :
                        item.media_type === 'video' ? 'bg-purple-900/50 text-purple-300' :
                        'bg-green-900/50 text-green-300'
                      }`}>
                        {item.media_type === 'image' ? 'Imagen' : item.media_type === 'video' ? 'Video' : 'Mensaje'}
                      </span>
                      {!item.is_active && (
                        <span className="px-2 py-0.5 fi-text-xs-medium rounded bg-slate-700 text-slate-400">
                          Inactivo
                        </span>
                      )}
                    </div>
                    <h4 className="fi-title-sm-medium truncate">{item.title || 'Sin título'}</h4>
                    {item.description && (
                      <p className="fi-text-xs mt-1 truncate">{item.description}</p>
                    )}
                    <p className="fi-text-xs-muted mt-1">
                      Duración: {item.duration / 1000}s · {new Date(item.uploaded_at).toLocaleDateString('es-MX')}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 ml-4">
                    <Button
                      onClick={() => handleToggleActive(item.media_id, item.is_active)}
                      variant={item.is_active ? 'purple' : 'secondary'}
                      size="sm"
                      icon={item.is_active ? Eye : EyeOff}
                      title={item.is_active ? 'Desactivar' : 'Activar'}
                      aria-label={item.is_active ? 'Desactivar' : 'Activar'}
                    />
                    <Button
                      onClick={() => handleDelete(item.media_id)}
                      variant="danger"
                      size="sm"
                      icon={Trash2}
                      className="bg-red-900/50 hover:bg-red-900"
                      title="Eliminar"
                      aria-label="Eliminar"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
