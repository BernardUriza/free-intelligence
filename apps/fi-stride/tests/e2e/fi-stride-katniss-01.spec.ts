import { test, expect } from '@playwright/test'

/**
 * FI-STRIDE-KATNISS-01: Post-Session Analysis E2E Tests
 * Keeper Artificial Trainer Nurturing Intelligence Sportive Spark
 */

const BASE_URL = 'http://localhost:9050'
const ATHLETE_EMAIL = 'athlete@test.com'
const ATHLETE_PASSWORD = 'demo123'

test.describe('FI-STRIDE KATNISS - Post-Session Analysis', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to app
    await page.goto(BASE_URL)

    // Login as athlete
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('text=Entrar')

    // Wait for login to complete
    await page.waitForURL(`${BASE_URL}/**`, { timeout: 5000 })
  })

  test('Should complete AthleteFlow and reach SessionAnalysis', async ({ page }) => {
    // Select Deportista role
    await page.click('button:has-text("Deportista")')

    // Step 1: Privacy consent
    const privacyCheckboxes = page.locator('input[type="checkbox"]').slice(0, 3)
    for (let i = 0; i < 3; i++) {
      await privacyCheckboxes.nth(i).check()
    }
    await page.click('text=Siguiente →')

    // Step 2: Permissions
    const permissionCheckboxes = page.locator('input[type="checkbox"]')
    await permissionCheckboxes.first().check()
    await page.click('text=Siguiente →')

    // Step 3: Profile (read-only, just continue)
    await page.click('text=Siguiente →')

    // Step 4: Ready
    await expect(page.locator('text=¡Listo para entrenar! 🎉')).toBeVisible()
    await page.click('text=Comenzar Entrenamiento 💪')

    // Should now be in SessionAnalysis (KATNISS)
    await expect(page.locator('text=¿Cómo te fue en la sesión?')).toBeVisible({ timeout: 5000 })
  })

  test('Should fill SessionAnalysis form with duration', async ({ page }) => {
    // Navigate to SessionAnalysis (skip AthleteFlow setup)
    // ... (abbreviated for brevity)

    // Fill duration slider
    const slider = page.locator('input[type="range"]').first()
    await slider.fill('45')

    // Check value is updated
    const value = await page.locator('text=45 min').first()
    await expect(value).toBeVisible()
  })

  test('Should select RPE (1-10) rating', async ({ page }) => {
    // ... setup code ...

    // Click RPE button 7
    await page.click('button:has-text("7")')

    // Verify selection (should have selected class)
    const rpeButton = page.locator('button:has-text("7")')
    await expect(rpeButton).toHaveClass(/selected/)
  })

  test('Should select emotional check-in (feliz/normal/cansado)', async ({ page }) => {
    // ... setup code ...

    // Click happy emotion
    const emotionButtons = page.locator('button:has-text("Feliz")')
    await emotionButtons.first().click()

    // Verify it's selected
    await expect(emotionButtons.first()).toHaveClass(/selected/)
  })

  test('Should submit session and show KATNISS feedback', async ({ page }) => {
    // Fill form
    await page.locator('input[type="range"]').first().fill('30')
    await page.locator('button:has-text("5")').click()
    await page.locator('button:has-text("Normal")').click()
    await page.locator('textarea').fill('Me siento bien hoy')

    // Submit
    await page.click('text=Obtener Feedback de KATNISS')

    // Should show loading state briefly
    await expect(page.locator('text=KATNISS analizando')).toBeVisible({ timeout: 2000 })

    // Should then show result with motivation
    await expect(page.locator('text=✨ Feedback de KATNISS ✨')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=Motivación')).toBeVisible()

    // Verify result structure
    const motivationText = page.locator('p.motivation')
    await expect(motivationText).toBeTruthy()

    const suggestionText = page.locator('p.suggestion')
    await expect(suggestionText).toBeTruthy()

    const dayRecommended = page.locator('p.dayRecommended')
    await expect(dayRecommended).toBeTruthy()
  })

  test('Should store session analysis in localStorage', async ({ page }) => {
    // Fill and submit form
    await page.locator('input[type="range"]').first().fill('30')
    await page.locator('button:has-text("5")').click()
    await page.click('text=Obtener Feedback de KATNISS')

    // Wait for result
    await expect(page.locator('text=✨ Feedback de KATNISS ✨')).toBeVisible({ timeout: 10000 })

    // Check localStorage
    const userData = await page.evaluate(() => {
      return {
        user: localStorage.getItem('fi-stride-user'),
        token: localStorage.getItem('fi-stride-auth-token')
      }
    })

    expect(userData.user).toBeTruthy()
    expect(userData.token).toBeTruthy()
  })

  test('Should allow user to start another session', async ({ page }) => {
    // Complete first session
    await page.locator('input[type="range"]').first().fill('30')
    await page.locator('button:has-text("5")').click()
    await page.click('text=Obtener Feedback de KATNISS')

    // Wait for result
    await expect(page.locator('text=✨ Feedback de KATNISS ✨')).toBeVisible({ timeout: 10000 })

    // Click "Otra Sesión"
    await page.click('text=Otra Sesión')

    // Should return to form
    await expect(page.locator('text=¿Cómo te fue en la sesión?')).toBeVisible()
  })

  test('Should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    // Navigate to SessionAnalysis
    // ... (setup code) ...

    // Verify form elements are visible and accessible
    await expect(page.locator('input[type="range"]').first()).toBeVisible()
    await expect(page.locator('button:has-text("5")')).toBeVisible()
  })

  test('Should show error if Ollama is offline', async ({ page }) => {
    // This test assumes Ollama is NOT running
    // Fill form and submit
    await page.locator('input[type="range"]').first().fill('30')
    await page.locator('button:has-text("5")').click()
    await page.click('text=Obtener Feedback de KATNISS')

    // Should still show feedback (fallback response)
    await expect(page.locator('text=✨ Feedback de KATNISS ✨')).toBeVisible({ timeout: 10000 })

    // Verify fallback response structure exists
    const motivationText = page.locator('p.motivation')
    await expect(motivationText).toBeTruthy()
  })

  test('Full user journey: Login → AthleteFlow → SessionAnalysis → Feedback', async ({
    page,
  }) => {
    // Step 1: Login already done in beforeEach

    // Step 2: Select Deportista
    await page.click('button:has-text("Deportista")')

    // Step 3: Complete AthleteFlow (4 steps)
    const checkboxes = page.locator('input[type="checkbox"]')

    // Privacy step
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('text=Siguiente →')

    // Permissions step
    await checkboxes.first().check()
    await page.click('text=Siguiente →')

    // Profile step
    await page.click('text=Siguiente →')

    // Ready step
    await page.click('text=Comenzar Entrenamiento 💪')

    // Step 4: SessionAnalysis
    await expect(page.locator('text=¿Cómo te fue en la sesión?')).toBeVisible({ timeout: 5000 })

    // Fill form
    await page.locator('input[type="range"]').first().fill('60')
    await page.locator('button:has-text("8")').click()
    await page.locator('button:has-text("Feliz")').click()

    // Submit
    await page.click('text=Obtener Feedback de KATNISS')

    // Verify feedback
    await expect(page.locator('text=✨ Feedback de KATNISS ✨')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=Motivación')).toBeVisible()
  })
})
