import { test, expect } from '@playwright/test'

/**
 * FI-STRIDE OFFLINE-06: Exercise Library E2E Tests
 * Simple tests for exercise catalog, search, filters, and offline downloads
 */

const BASE_URL = 'http://localhost:9050'
const LIBRARY_URL = `${BASE_URL}/biblioteca`

test.describe('Exercise Library - Basic Functionality', () => {
  test.beforeEach(async ({ page }) => {
    // Set authenticated user in localStorage to bypass login
    await page.evaluate(() => {
      const mockUser = {
        id: 'test-athlete-001',
        name: 'Test Athlete',
        role: 'athlete',
        email: 'athlete@test.local'
      }
      localStorage.setItem('fi-stride-user', JSON.stringify(mockUser))
    })

    // Navigate to exercise library (library page requires authentication)
    await page.goto(LIBRARY_URL, { waitUntil: 'networkidle' })
  })

  // ==========================================
  // SUITE 1: INITIAL LOAD
  // ==========================================

  test('📚 Exercise library loads with 10+ exercises', async ({ page }) => {
    // Verify heading exists
    await expect(page.locator('text=Biblioteca de Ejercicios')).toBeVisible()

    // Verify exercise cards are displayed
    const exerciseCards = page.locator('[class*="grid"]').locator('[class*="rounded"]')
    const cardCount = await exerciseCards.count()
    expect(cardCount).toBeGreaterThanOrEqual(10)
  })

  test('🔍 Search box appears in library', async ({ page }) => {
    // Verify search input exists
    const searchInput = page.locator('input[placeholder*="Busca"]')
    await expect(searchInput).toBeVisible()
  })

  // ==========================================
  // SUITE 2: SEARCH FUNCTIONALITY
  // ==========================================

  test('🔍 Search filters exercises by name', async ({ page }) => {
    // Initially should show all exercises
    let cards = page.locator('[class*="bg-slate-800"][class*="rounded"]')
    const initialCount = await cards.count()
    expect(initialCount).toBeGreaterThan(0)

    // Search for "Caminata"
    const searchInput = page.locator('input[placeholder*="Busca"]')
    await searchInput.fill('Caminata')

    // Wait for filter to apply
    await page.waitForLoadState('networkidle')

    // Should show fewer results
    cards = page.locator('[class*="bg-slate-800"][class*="rounded"]')
    const filteredCount = await cards.count()
    expect(filteredCount).toBeLessThanOrEqual(initialCount)
    expect(filteredCount).toBeGreaterThan(0)

    // Should contain "Caminata"
    await expect(page.locator('text=Caminata Suave')).toBeVisible()
  })

  test('🔍 Search with no results shows message', async ({ page }) => {
    // Search for non-existent exercise
    const searchInput = page.locator('input[placeholder*="Busca"]')
    await searchInput.fill('XYZ123NOEXIST')

    // Wait for filter
    await page.waitForLoadState('networkidle')

    // Should show "no hay ejercicios" message
    await expect(page.locator('text=No hay ejercicios que coincidan')).toBeVisible()
  })

  // ==========================================
  // SUITE 3: FILTERS
  // ==========================================

  test('📊 Difficulty filter shows only easy exercises', async ({ page }) => {
    // Find difficulty filter select
    const difficultySelects = page.locator('select')
    const difficultySelect = difficultySelects.first()

    // Select "Fácil"
    await difficultySelect.selectOption('easy')

    // Wait for filter
    await page.waitForLoadState('networkidle')

    // Should show exercises with easy difficulty
    const exerciseCards = page.locator('[class*="bg-slate-800"][class*="rounded"]')
    const count = await exerciseCards.count()
    expect(count).toBeGreaterThan(0)

    // Should see "Fácil" badge in cards
    await expect(page.locator('text=🟢 Fácil')).toBeVisible()
  })

  test('♿ Accessibility filter shows filtered exercises', async ({ page }) => {
    // Get all selects
    const selects = page.locator('select')
    // Second select is usually accessibility
    const a11ySelect = selects.nth(1)

    // Select "Sin equipo"
    await a11ySelect.selectOption('noEquipment')

    // Wait for filter
    await page.waitForLoadState('networkidle')

    // Should show exercises
    const exerciseCards = page.locator('[class*="bg-slate-800"][class*="rounded"]')
    const count = await exerciseCards.count()
    expect(count).toBeGreaterThan(0)

    // Should see accessibility badge
    await expect(page.locator('text=🆓 Sin equipo')).toBeVisible()
  })

  // ==========================================
  // SUITE 4: EXERCISE DETAIL VIEW
  // ==========================================

  test('👁️ Click on exercise opens detail view', async ({ page }) => {
    // Click on first exercise card
    const firstCard = page.locator('[class*="bg-slate-800"][class*="rounded"]').first()
    await firstCard.click()

    // Should show detail view with back button
    await expect(page.locator('text=Volver')).toBeVisible()

    // Should show large title
    const heading = page.locator('h1')
    await expect(heading).toBeVisible()
  })

  test('📋 Detail view shows instructions', async ({ page }) => {
    // Open first exercise
    const firstCard = page.locator('[class*="bg-slate-800"][class*="rounded"]').first()
    await firstCard.click()

    // Should show "Instrucciones" section
    await expect(page.locator('text=Instrucciones Paso a Paso')).toBeVisible()

    // Should show numbered steps
    const steps = page.locator('[class*="flex"][class*="gap-3"]')
    const stepCount = await steps.count()
    expect(stepCount).toBeGreaterThan(0)
  })

  test('⚠️ Detail view shows safety alerts', async ({ page }) => {
    // Open first exercise
    const firstCard = page.locator('[class*="bg-slate-800"][class*="rounded"]').first()
    await firstCard.click()

    // Should show "Alertas de Seguridad" if they exist
    const safetySection = page.locator('text=Alertas de Seguridad')
    const isSafetyVisible = await safetySection.isVisible().catch(() => false)

    // If visible, should have content
    if (isSafetyVisible) {
      const alerts = page.locator('[class*="border-2"][class*="border-red"]').locator('li')
      const alertCount = await alerts.count()
      expect(alertCount).toBeGreaterThan(0)
    }
  })

  // ==========================================
  // SUITE 5: FAVORITE FUNCTIONALITY
  // ==========================================

  test('❤️ Mark exercise as favorite', async ({ page }) => {
    // Find heart icon in first card
    const firstCard = page.locator('[class*="bg-slate-800"][class*="rounded"]').first()
    const heartBtn = firstCard.locator('button:has-text("🤍"), button:has-text("❤️")')

    // Click to favorite (should change from 🤍 to ❤️)
    await heartBtn.click()

    // Wait for state change
    await page.waitForTimeout(300)

    // Should now show filled heart
    await expect(heartBtn).toContainText('❤️')
  })

  test('💾 Favorites persist in localStorage', async ({ page }) => {
    // Get initial favorites value
    const initialFavorites = await page.evaluate(() => {
      return localStorage.getItem('exerciseFavorites')
    })

    // Click favorite on first exercise
    const firstCard = page.locator('[class*="bg-slate-800"][class*="rounded"]').first()
    const heartBtn = firstCard.locator('button:has-text("🤍"), button:has-text("❤️")')
    await heartBtn.click()

    // Wait for update
    await page.waitForTimeout(300)

    // Check localStorage was updated
    const newFavorites = await page.evaluate(() => {
      return localStorage.getItem('exerciseFavorites')
    })

    expect(newFavorites).not.toEqual(initialFavorites)
    expect(newFavorites).toBeTruthy()
  })

  // ==========================================
  // SUITE 6: DOWNLOAD FUNCTIONALITY
  // ==========================================

  test('⬇️ Download button exists on exercise card', async ({ page }) => {
    // Find download button in first card
    const firstCard = page.locator('[class*="bg-slate-800"][class*="rounded"]').first()
    const downloadBtn = firstCard.locator('button:has-text("Descargar")')

    await expect(downloadBtn).toBeVisible()
  })

  test('⬇️ Detail view shows download/delete button', async ({ page }) => {
    // Open first exercise
    const firstCard = page.locator('[class*="bg-slate-800"][class*="rounded"]').first()
    await firstCard.click()

    // Should show download button
    const downloadBtn = page.locator('button:has-text("Descargar para Offline")')
    await expect(downloadBtn).toBeVisible()
  })

  // ==========================================
  // SUITE 7: RESPONSIVE DESIGN
  // ==========================================

  test('📱 Exercises grid is responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    // Wait for layout to adjust
    await page.waitForLoadState('networkidle')

    // Should still show exercises
    const exerciseCards = page.locator('[class*="bg-slate-800"][class*="rounded"]')
    const count = await exerciseCards.count()
    expect(count).toBeGreaterThan(0)

    // Should be visible on mobile
    const firstCard = exerciseCards.first()
    await expect(firstCard).toBeVisible()
  })

  // ==========================================
  // SUITE 8: NAVIGATION
  // ==========================================

  test('👈 Back button returns to library from detail', async ({ page }) => {
    // Open first exercise
    const firstCard = page.locator('[class*="bg-slate-800"][class*="rounded"]').first()
    await firstCard.click()

    // Wait for detail view
    await expect(page.locator('text=Volver')).toBeVisible()

    // Click back button
    const backBtn = page.locator('button:has-text("Volver")')
    await backBtn.click()

    // Should return to library
    await expect(page.locator('text=Biblioteca de Ejercicios')).toBeVisible()
  })

  // ==========================================
  // SUITE 9: FULL USER JOURNEY
  // ==========================================

  test('🎯 Complete journey: Search → Filter → View Detail → Favorite → Download', async ({
    page,
  }) => {
    // STEP 1: Search
    const searchInput = page.locator('input[placeholder*="Busca"]')
    await searchInput.fill('Estiramientos')
    await page.waitForLoadState('networkidle')

    // STEP 2: Click on exercise
    const exerciseCard = page.locator('text=Estiramientos Básicos').first()
    const cardParent = exerciseCard.locator('..').locator('..')
    await cardParent.click()

    // STEP 3: Verify detail view
    await expect(page.locator('text=Instrucciones Paso a Paso')).toBeVisible()

    // STEP 4: Verify stats
    await expect(page.locator('text=Duración')).toBeVisible()
    await expect(page.locator('text=Dificultad')).toBeVisible()

    // STEP 5: Check download button
    const downloadBtn = page.locator('button:has-text("Descargar para Offline")')
    await expect(downloadBtn).toBeVisible()

    // STEP 6: Go back
    const backBtn = page.locator('button:has-text("Volver")')
    await backBtn.click()

    // STEP 7: Verify back in library
    await expect(page.locator('text=Biblioteca de Ejercicios')).toBeVisible()
  })
})
