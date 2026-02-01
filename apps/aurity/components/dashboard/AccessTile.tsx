"use client";

/**
 * AccessTile Component
 * Card: FI-UI-FEAT-208
 *
 * Individual tile for Index Hub navigation
 */

import Link from "next/link";
import { type NavRoute } from "@/lib/navigation";

interface AccessTileProps {
  route: NavRoute;
  onClick?: () => void;
}

export function AccessTile({ route, onClick }: AccessTileProps) {
  const Icon = route.icon;

  return (
    <Link
      href={route.href}
      onClick={onClick}
      className="group relative flex flex-col gap-3 p-6 bg-slate-800/60 border border-white/10 hover:border-emerald-500/40 hover:bg-slate-800/80 backdrop-blur-md rounded-xl transition-all duration-300 ease-out focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:ring-offset-2 focus:ring-offset-slate-900 shadow-sm shadow-black/5 hover:shadow-md hover:shadow-emerald-500/10"
      aria-label={`${route.title}: ${route.description}. Shortcut: ${route.shortcut}`}
    >
      {/* Shortcut badge */}
      <div className="absolute top-3 right-3">
        <kbd className="px-2 py-1 text-xs font-semibold text-slate-400 bg-slate-700/50 rounded border border-slate-600">
          {route.shortcut}
        </kbd>
      </div>

      {/* Icon */}
      <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-blue-500/10 fi-text-primary group-hover:bg-blue-500/20 group-hover:text-blue-300 transition-colors">
        <Icon className="fi-icon-lg" />
      </div>

      {/* Content */}
      <div className="space-y-1">
        <h3 className="text-lg font-semibold text-slate-50 group-hover:text-blue-300 transition-colors">
          {route.title}
        </h3>
        <p className="fi-subtitle line-clamp-2">{route.description}</p>
      </div>

      {/* Badge (optional) */}
      {route.badge && (
        <div className="mt-auto">
          <span className="inline-flex items-center px-2 py-1 fi-text-xs-medium text-blue-300 bg-blue-500/10 rounded">
            {route.badge}
          </span>
        </div>
      )}
    </Link>
  );
}
