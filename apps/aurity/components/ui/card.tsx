/**
 * Card Component - Stub
 *
 * Minimal implementation to unblock build.
 */

import React from 'react';

export interface CardProps {
  className?: string;
  children: React.ReactNode;
}

export function Card({ className = '', children }: CardProps) {
  return <div className={`fi-card-solid ${className}`}>{children}</div>;
}

export interface CardHeaderProps {
  className?: string;
  children: React.ReactNode;
}

export function CardHeader({ className = '', children }: CardHeaderProps) {
  return <div className={`fi-card-header ${className}`}>{children}</div>;
}

export interface CardTitleProps {
  className?: string;
  children: React.ReactNode;
}

export function CardTitle({ className = '', children }: CardTitleProps) {
  return <h3 className={`fi-title ${className}`}>{children}</h3>;
}

export interface CardDescriptionProps {
  className?: string;
  children: React.ReactNode;
}

export function CardDescription({ className = '', children }: CardDescriptionProps) {
  return <p className={`fi-subtitle ${className}`}>{children}</p>;
}

export interface CardContentProps {
  className?: string;
  children: React.ReactNode;
}

export function CardContent({ className = '', children }: CardContentProps) {
  return <div className={`fi-card-body ${className}`}>{children}</div>;
}

export interface CardFooterProps {
  className?: string;
  children: React.ReactNode;
}

export function CardFooter({ className = '', children }: CardFooterProps) {
  return <div className={`fi-card-footer ${className}`}>{children}</div>;
}
