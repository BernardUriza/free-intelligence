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
      className="dash-access-tile"
      aria-label={`${route.title}: ${route.description}. Shortcut: ${route.shortcut}`}
    >
      {/* Shortcut badge */}
      <div className="absolute top-3 right-3">
        <kbd className="dash-access-tile-shortcut">
          {route.shortcut}
        </kbd>
      </div>

      {/* Icon */}
      <div className="dash-access-tile-icon">
        <Icon className="fi-icon-lg" />
      </div>

      {/* Content */}
      <div className="space-y-1">
        <h3 className="dash-access-tile-title">
          {route.title}
        </h3>
        <p className="fi-subtitle line-clamp-2">{route.description}</p>
      </div>

      {/* Badge (optional) */}
      {route.badge && (
        <div className="mt-auto">
          <span className="dash-access-tile-badge">
            {route.badge}
          </span>
        </div>
      )}
    </Link>
  );
}
