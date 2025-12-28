/**
 * Tests for navigation.ts
 * Updated: 2025-12-12 - Added tests for categories and grouped routes
 */

import {
  NAV_ROUTES,
  CATEGORIES,
  getRouteByShortcut,
  getRouteByHref,
  getRoutesByCategory,
  getGroupedRoutes,
  getVisibleRoutes,
} from "./navigation";

describe("Navigation Configuration", () => {
  test("All shortcuts are unique", () => {
    const shortcuts = NAV_ROUTES.map((route) => route.shortcut);
    const uniqueShortcuts = new Set(shortcuts);
    expect(shortcuts.length).toBe(uniqueShortcuts.size);
  });

  test("Get route by valid shortcut", () => {
    const shortcut = "1"; // Example shortcut
    const route = getRouteByShortcut(shortcut);
    expect(route).toBeDefined();
    expect(route?.shortcut).toBe(shortcut);
  });

  test("Get route by invalid shortcut", () => {
    const shortcut = "invalid";
    const route = getRouteByShortcut(shortcut);
    expect(route).toBeUndefined();
  });

  test("Get route by valid href", () => {
    const href = "/medical-ai"; // Example href
    const route = getRouteByHref(href);
    expect(route).toBeDefined();
    expect(route?.href).toBe(href);
  });

  test("Get route by invalid href", () => {
    const href = "/invalid-href";
    const route = getRouteByHref(href);
    expect(route).toBeUndefined();
  });

  test("Hidden routes are correctly flagged", () => {
    const hiddenRoutes = NAV_ROUTES.filter((route) => route.hidden);
    hiddenRoutes.forEach((route) => {
      expect(route.hidden).toBe(true);
    });
  });
});

describe("Category System", () => {
  test("All routes have a valid category", () => {
    NAV_ROUTES.forEach((route) => {
      expect(CATEGORIES[route.category]).toBeDefined();
    });
  });

  test("All routes have an order property", () => {
    NAV_ROUTES.forEach((route) => {
      expect(typeof route.order).toBe("number");
      expect(route.order).toBeGreaterThan(0);
    });
  });

  test("Get routes by category returns sorted routes", () => {
    const clinicalRoutes = getRoutesByCategory("clinical");
    expect(clinicalRoutes.length).toBeGreaterThan(0);

    // Check ordering
    for (let i = 1; i < clinicalRoutes.length; i++) {
      expect(clinicalRoutes[i].order).toBeGreaterThanOrEqual(
        clinicalRoutes[i - 1].order
      );
    }
  });

  test("getGroupedRoutes returns all visible categories", () => {
    const grouped = getGroupedRoutes();
    expect(grouped.length).toBe(3); // clinical, ai_config, admin

    // Check each group has routes
    grouped.forEach((group) => {
      expect(group.routes.length).toBeGreaterThan(0);
      expect(group.category.label).toBeDefined();
    });
  });

  test("getVisibleRoutes excludes hidden routes", () => {
    const visible = getVisibleRoutes();
    const hasHidden = visible.some((route) => route.hidden);
    expect(hasHidden).toBe(false);
  });

  test("LLM Models route exists in ai_config category", () => {
    const aiRoutes = getRoutesByCategory("ai_config");
    const llmModels = aiRoutes.find((r) => r.id === "llm-models-admin");
    expect(llmModels).toBeDefined();
    expect(llmModels?.href).toBe("/admin/models");
  });
});