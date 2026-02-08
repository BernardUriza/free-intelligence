'use client';

/**
 * OrderEntry Component - AURITY Medical Workflow
 *
 * Medical orders and prescriptions management.
 * Tracks medications, lab tests, imaging, and follow-up appointments.
 */

import { useState } from 'react';
import { Plus, ChevronRight, ClipboardList, Loader2, Zap, RefreshCw, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

import type { OrderEntryProps, OrderType } from './types';
import { getPlaceholderForType } from './constants';
import { useOrderManagement, useOrderChatbot } from './hooks';
import { OrderTypeSelector, OrderStats, OrdersList, OrderChatbot } from './components';

export function OrderEntry({
  sessionId,
  onNext,
  onPrevious,
  className = ''
}: OrderEntryProps) {
  // Form state
  const [newOrderType, setNewOrderType] = useState<OrderType>('medication');
  const [newOrderDescription, setNewOrderDescription] = useState('');
  const [newOrderDetails, setNewOrderDetails] = useState('');

  // Order management
  const {
    orders,
    groupedOrders,
    loading,
    error,
    submitting,
    refreshing,
    lastRefresh,
    handleRefresh,
    handleAddOrder,
    handleRemoveOrder,
    addOrderFromChat,
  } = useOrderManagement(sessionId);

  // Chatbot
  const {
    showChatbot,
    chatMessages,
    chatInput,
    chatLoading,
    toggleChatbot,
    closeChatbot,
    setChatInput,
    handleChatSend,
  } = useOrderChatbot({ sessionId, onOrderCreated: addOrderFromChat });

  const handleSubmitOrder = async () => {
    const success = await handleAddOrder(newOrderType, newOrderDescription, newOrderDetails);
    if (success) {
      setNewOrderDescription('');
      setNewOrderDetails('');
    }
  };

  return (
    <div className={`space-y-8 ${className} max-w-5xl mx-auto`}>
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="med-order-icon-box">
          <ClipboardList className="h-8 w-8 fi-text-success" />
        </div>
        <div className="flex items-center justify-center gap-4">
          <h2 className="text-3xl font-bold text-white tracking-tight">Órdenes Médicas</h2>

          <Button
            onClick={handleRefresh}
            disabled={refreshing || loading}
            variant="secondary"
            size="sm"
            icon={RefreshCw}
            className={refreshing ? '[&_svg]:animate-spin' : ''}
            title="Refrescar órdenes"
            aria-label="Refrescar órdenes"
          />

          <Button
            onClick={toggleChatbot}
            variant={showChatbot ? 'success' : 'secondary'}
            icon={Zap}
          >
            Asistente IA
          </Button>
        </div>

        {lastRefresh && !loading && (
          <p className="fi-text-xs-muted">
            Última actualización: {lastRefresh.toLocaleTimeString()}
            {orders.length === 0 && <span className="ml-2 fi-text-success">• Auto-actualizando...</span>}
          </p>
        )}
        <p className="text-slate-400 text-lg max-w-2xl mx-auto">
          Gestiona prescripciones, estudios de laboratorio e imagenología de forma segura
        </p>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-red-500/10 border border-red-500 rounded-xl p-5 flex items-start gap-3 animate-shake">
          <AlertCircle className="h-6 w-6 fi-text-error flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="fi-text-error font-semibold mb-1">Error al cargar órdenes</p>
            <p className="text-red-300 text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="fi-empty-state py-16">
          <Loader2 className="h-12 w-12 text-emerald-500 animate-spin mb-4" />
          <span className="fi-text text-lg font-medium">Cargando órdenes médicas...</span>
          <span className="text-slate-500 text-sm mt-2">Sesión: {sessionId.slice(0, 20)}...</span>
        </div>
      )}

      {/* Quick Stats */}
      {!loading && orders.length > 0 && <OrderStats orders={orders} />}

      {!loading && (
        <>
          {/* Add New Order Form */}
          <div className="med-order-form-card">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-emerald-500/10 rounded-lg">
                <Plus className="h-5 w-5 fi-text-success" />
              </div>
              <h3 className="fi-title-xl">Nueva Orden Médica</h3>
            </div>

            <div className="fi-stack-xl">
              <div>
                <label className="block text-sm font-medium fi-text mb-3">
                  Tipo de orden
                </label>
                <OrderTypeSelector
                  selectedType={newOrderType}
                  onSelect={setNewOrderType}
                />
              </div>

              <div>
                <label className="fi-label">
                  Descripción <span className="fi-text-error">*</span>
                </label>
                <input
                  type="text"
                  value={newOrderDescription}
                  onChange={(e) => setNewOrderDescription(e.target.value)}
                  placeholder={getPlaceholderForType(newOrderType)}
                  className="med-order-input"
                />
              </div>

              <div>
                <label className="fi-label">
                  Detalles adicionales <span className="text-slate-500 text-xs">(opcional)</span>
                </label>
                <textarea
                  value={newOrderDetails}
                  onChange={(e) => setNewOrderDetails(e.target.value)}
                  placeholder="Instrucciones especiales, horarios, precauciones..."
                  rows={3}
                  className="med-order-textarea"
                />
              </div>

              <Button
                onClick={handleSubmitOrder}
                disabled={!newOrderDescription.trim() || submitting}
                variant="primary"
                size="xl"
                icon={submitting ? undefined : Plus}
                loading={submitting}
                fullWidth
                className="shadow-lg hover:shadow-emerald-500/50"
              >
                {submitting ? 'Guardando orden...' : 'Agregar Orden Médica'}
              </Button>
            </div>
          </div>

          {/* Orders List */}
          <OrdersList groupedOrders={groupedOrders} onRemove={handleRemoveOrder} />

          {/* Summary */}
          <div className="med-order-summary-card">
            <div className="fi-flex-between">
              <div className="fi-flex-gap-md">
                <div className="p-3 bg-emerald-500/20 rounded-xl">
                  <ClipboardList className="h-6 w-6 fi-text-success" />
                </div>
                <div>
                  <p className="fi-subtitle">Total de órdenes</p>
                  <p className="fi-title-2xl">{orders.length}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="fi-subtitle">Sesión</p>
                <p className="fi-text-xs-muted font-mono">{sessionId.slice(0, 12)}...</p>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex gap-4 pt-4">
            {onPrevious && (
              <Button
                onClick={onPrevious}
                variant="secondary"
                size="xl"
                className="flex-1"
              >
                Anterior
              </Button>
            )}
            {onNext && (
              <Button
                onClick={onNext}
                variant="primary"
                size="xl"
                icon={ChevronRight}
                className="flex-1 shadow-lg hover:shadow-emerald-500/50"
              >
                Continuar al Resumen
              </Button>
            )}
          </div>
        </>
      )}

      {/* Chatbot */}
      {showChatbot && (
        <OrderChatbot
          messages={chatMessages}
          input={chatInput}
          loading={chatLoading}
          onInputChange={setChatInput}
          onSend={handleChatSend}
          onClose={closeChatbot}
        />
      )}
    </div>
  );
}

export default OrderEntry;
