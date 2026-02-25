/**
 * useOrderManagement Hook
 *
 * Manages order state, CRUD operations, and auto-polling.
 */

import { useState, useCallback, useEffect } from 'react';
import { createLogger } from '@/lib/internal/logger';
import { medicalWorkflowApi, type MedicalOrder } from '@aurity-standalone/api-client/medical-workflow';

const log = createLogger('OrderEntry');
import type { OrderType } from '../types';

export function useOrderManagement(sessionId: string) {
  const [orders, setOrders] = useState<MedicalOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const loadOrders = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const fetchedOrders = await medicalWorkflowApi.getOrders(sessionId);
      setOrders(fetchedOrders);
      setLastRefresh(new Date());
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);

      const isNoDataError = errorMsg.includes('not found') ||
                           errorMsg.includes('404') ||
                           errorMsg.includes('does not exist');

      if (isNoDataError) {
        setOrders([]);
        setLastRefresh(new Date());
      } else {
        log.error('Failed to load orders', { error: String(err) });
        setError('Error al cargar órdenes médicas');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [sessionId]);

  // Load orders on mount
  useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  // Auto-poll every 3s if no orders
  useEffect(() => {
    if (orders.length === 0 && !loading) {
      const interval = setInterval(() => {
        loadOrders();
      }, 3000);

      return () => {
        clearInterval(interval);
      };
    }
  }, [orders.length, loading, loadOrders]);

  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    loadOrders();
  }, [loadOrders]);

  const handleAddOrder = useCallback(async (
    type: OrderType,
    description: string,
    details?: string
  ) => {
    if (!description.trim()) return;

    try {
      setSubmitting(true);
      setError(null);

      const orderId = await medicalWorkflowApi.createOrder(sessionId, {
        type,
        description: description.trim(),
        details: details?.trim() || undefined
      });

      const newOrder: MedicalOrder = {
        id: orderId,
        type,
        description: description.trim(),
        details: details?.trim() || undefined,
        source: 'manual',
        created_at: new Date().toISOString()
      };

      setOrders(prev => [...prev, newOrder]);
      return true;
    } catch (err) {
      log.error('Failed to create order', { error: String(err) });
      setError('Error al crear la orden');
      return false;
    } finally {
      setSubmitting(false);
    }
  }, [sessionId]);

  const handleRemoveOrder = useCallback(async (id: string) => {
    try {
      setError(null);
      setOrders(prev => prev.filter(order => order.id !== id));
      await medicalWorkflowApi.deleteOrder(sessionId, id);
    } catch (err) {
      log.error('Failed to delete order', { error: String(err) });
      setError('Error al eliminar la orden');
      const fetchedOrders = await medicalWorkflowApi.getOrders(sessionId);
      setOrders(fetchedOrders);
    }
  }, [sessionId]);

  const addOrderFromChat = useCallback((order: MedicalOrder) => {
    setOrders(prev => [...prev, order]);
  }, []);

  // Group orders by type
  const groupedOrders = orders.reduce((acc, order) => {
    if (!acc[order.type]) acc[order.type] = [];
    acc[order.type].push(order);
    return acc;
  }, {} as Record<string, MedicalOrder[]>);

  return {
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
  };
}
