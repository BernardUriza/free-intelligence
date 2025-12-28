/**
 * OrderEntry Constants
 */

import type { OrderTypeConfig, OrderType } from './types';

export const ORDER_TYPES: Record<OrderType, OrderTypeConfig> = {
  medication: {
    label: 'Medicación',
    icon: '💊',
    color: 'emerald',
    gradientClass: 'fi-gradient-emerald-subtle',
    border: 'border-emerald-500/50',
    text: 'fi-text-success'
  },
  lab: {
    label: 'Laboratorio',
    icon: '🔬',
    color: 'cyan',
    gradientClass: 'fi-gradient-cyan-subtle',
    border: 'border-cyan-500/50',
    text: 'fi-text-info'
  },
  imaging: {
    label: 'Imagenología',
    icon: '🔍',
    color: 'purple',
    gradientClass: 'fi-gradient-purple-subtle',
    border: 'border-purple-500/50',
    text: 'fi-text-purple'
  },
  followup: {
    label: 'Seguimiento',
    icon: '📅',
    color: 'amber',
    gradientClass: 'fi-gradient-amber-subtle',
    border: 'border-amber-500/50',
    text: 'fi-text-warning'
  }
};

export const ORDER_TYPE_KEYS = Object.keys(ORDER_TYPES) as OrderType[];

export const getPlaceholderForType = (type: OrderType): string => {
  switch (type) {
    case 'medication':
      return 'Ej: Paracetamol 500mg, cada 8 horas';
    case 'lab':
      return 'Ej: Biometría hemática completa';
    case 'imaging':
      return 'Ej: Radiografía de tórax PA y lateral';
    case 'followup':
      return 'Ej: Control en 7 días';
  }
};
