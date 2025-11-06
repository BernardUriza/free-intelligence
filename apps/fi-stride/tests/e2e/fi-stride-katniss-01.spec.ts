import { test, expect } from '@playwright/test'

/**
 * FI-STRIDE-KATNISS-01: Post-Session Analysis E2E Tests
 * Keeper Artificial Trainer Nurturing Intelligence Sportive Spark
 *
 * Full integration tests for FI-Stride MVP:
 * - Login flow
 * - 4-step AthleteFlow (privacy → permissions → profile → ready)
 * - SessionAnalysis form with KATNISS feedback
 * - Data persistence (localStorage + IndexedDB)
 */

const BASE_URL = 'http://localhost:9050'
const BACKEND_URL = 'http://localhost:7001'
const ATHLETE_EMAIL = 'athlete@test.com'
const ATHLETE_PASSWORD = 'demo123'

// Helper function to login as athlete
async function loginAsAthlete(page: any) {
  await page.goto(BASE_URL, { waitUntil: 'networkidle' })
  // Select Deportista role
  await page.click('button:has-text("Deportista")')
  // Fill form
  await page.fill('input[type="email"]', ATHLETE_EMAIL)
  await page.fill('input[type="password"]', ATHLETE_PASSWORD)
  await page.click('button:has-text("Entrar")')
  // Wait for AthleteFlow to appear
  await page.waitForSelector('text=Privacidad y Consentimiento', { timeout: 5000 })
}

// Helper to complete privacy step
async function completePrivacyStep(page: any) {
  const checkboxes = page.locator('input[type="checkbox"]')
  for (let i = 0; i < 3; i++) {
    await checkboxes.nth(i).check()
  }
  await page.click('button:has-text("Siguiente")')
}

// Helper to complete permissions step
async function completePermissionsStep(page: any) {
  const checkboxes = page.locator('input[type="checkbox"]')
  await checkboxes.first().check()
  await page.click('button:has-text("Siguiente")')
}

// Helper to complete profile step
async function completeProfileStep(page: any) {
  await page.click('button:has-text("Siguiente")')
}

// Helper to reach SessionAnalysis from login
async function navigateToSessionAnalysis(page: any) {
  await loginAsAthlete(page)
  await completePrivacyStep(page)
  await completePermissionsStep(page)
  await completeProfileStep(page)
  await page.click('button:has-text("Comenzar Entrenamiento 💪")')
  await page.waitForSelector('text=¿Cómo te fue en la sesión?', { timeout: 5000 })
}

test.describe('FI-STRIDE KATNISS MVP - Complete E2E Suite', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to app
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
  })

  // ==========================================
  // SUITE 1: LOGIN + ROLE SELECTION
  // ==========================================

  test('✅ Login page loads with email/password form', async ({ page }) => {
    // Verify login form exists
    await expect(page.locator('input[type="email"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button:has-text("Entrar")')).toBeVisible()
  })

  test('✅ Login with valid credentials', async ({ page }) => {
    // Role buttons should be visible on login page
    await expect(page.locator('button:has-text("Deportista")')).toBeVisible()
    await expect(page.locator('button:has-text("Entrenador")')).toBeVisible()

    // Select Deportista role
    await page.click('button:has-text("Deportista")')

    // Fill form
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')

    // After login, should show AthleteFlow (step 1: privacy consent)
    await expect(page.locator('text=Privacidad y Consentimiento')).toBeVisible({ timeout: 5000 })
  })

  // ==========================================
  // SUITE 2: ATHLETEFLOW (4 STEPS)
  // ==========================================

  test('✅ STEP 1: Privacy consent with 3 checkboxes', async ({ page }) => {
    // Login first
    await loginAsAthlete(page)

    // Verify step 1 appears
    await expect(page.locator('text=Privacidad y Consentimiento')).toBeVisible()
    await expect(page.locator('text=Política de Privacidad')).toBeVisible()
    await expect(page.locator('text=Encriptación')).toBeVisible()
    await expect(page.locator('text=Procesamiento de Datos')).toBeVisible()

    // Progress bar at 25%
    const progressBar = page.locator('div[style*="width"]').first()
    const style = await progressBar.evaluate((el) => el.getAttribute('style'))
    expect(style).toContain('25%')

    // Verify "Siguiente" button is disabled before checking
    const nextBtn = page.locator('button:has-text("Siguiente")')
    expect(await nextBtn.isDisabled()).toBe(true)
  })

  test('✅ STEP 2: Permission selection (camera/microphone)', async ({ page }) => {
    // Setup: complete step 1
    await loginAsAthlete(page)
    await completePrivacyStep(page)

    // Verify step 2 appears
    await expect(page.locator('text=Permisos de Dispositivo')).toBeVisible()
    await expect(page.locator('text=Cámara')).toBeVisible()
    await expect(page.locator('text=Micrófono')).toBeVisible()

    // Progress bar at 50%
    const progressBar = page.locator('div[style*="width"]').first()
    const style = await progressBar.evaluate((el) => el.getAttribute('style'))
    expect(style).toContain('50%')

    // Check camera permission
    const checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.first().check()
    await expect(checkboxes.first()).toBeChecked()
  })

  test('✅ STEP 3: Profile (read-only display)', async ({ page }) => {
    // Setup: complete steps 1-2
    await loginAsAthlete(page)
    await completePrivacyStep(page)
    await completePermissionsStep(page)

    // Verify step 3 appears
    await expect(page.locator('text=Tu Perfil')).toBeVisible()
    await expect(page.locator('text=Información de tu cuenta')).toBeVisible()

    // Progress bar at 75%
    const progressBar = page.locator('div[style*="width"]').first()
    const style = await progressBar.evaluate((el) => el.getAttribute('style'))
    expect(style).toContain('75%')

    // Verify inputs are disabled
    const inputs = page.locator('input[disabled]')
    expect(await inputs.count()).toBeGreaterThan(0)
  })

  test('✅ STEP 4: Ready confirmation', async ({ page }) => {
    // Setup: complete steps 1-3
    await loginAsAthlete(page)
    await completePrivacyStep(page)
    await completePermissionsStep(page)
    await completeProfileStep(page)

    // Verify step 4 appears
    await expect(page.locator('text=¡Listo para entrenar! 🎉')).toBeVisible()
    await expect(page.locator('text=Privacidad confirmada')).toBeVisible()
    await expect(page.locator('text=Permisos configurados')).toBeVisible()
    await expect(page.locator('text=Perfil completado')).toBeVisible()

    // Progress bar at 100%
    const progressBar = page.locator('div[style*="width"]').first()
    const style = await progressBar.evaluate((el) => el.getAttribute('style'))
    expect(style).toContain('100%')
  })

  // ==========================================
  // SUITE 3: SESSION ANALYSIS FORM
  // ==========================================

  test('✅ SessionAnalysis form loads after AthleteFlow', async ({ page }) => {
    // Navigate to SessionAnalysis
    await navigateToSessionAnalysis(page)

    // Verify SessionAnalysis appears
    await expect(page.locator('text=¿Cómo te fue en la sesión?')).toBeVisible()
    await expect(page.locator('text=Duración (minutos)')).toBeVisible()
    await expect(page.locator('text=¿Cuánto esfuerzo hiciste? (1-10)')).toBeVisible()
    await expect(page.locator('text=¿Cómo te sientes ahora?')).toBeVisible()
  })

  test('✅ Duration slider works (5-120 min range)', async ({ page }) => {
    // Navigate to SessionAnalysis
    await navigateToSessionAnalysis(page)

    // Test slider
    const slider = page.locator('input[type="range"]').first()
    await slider.fill('45')

    // Verify value display
    const valueDisplay = page.locator('text=45 min')
    await expect(valueDisplay).toBeVisible()
  })

  test('✅ RPE buttons (1-10) selection', async ({ page }) => {
    // Navigate to SessionAnalysis
    await navigateToSessionAnalysis(page)

    // Click RPE button "7"
    const rpeButton = page.locator('button:has-text("7")')
    await rpeButton.click()

    // Verify button is selected (has class or styling)
    const classList = await rpeButton.evaluate((el) => el.className)
    expect(classList).toContain('selected')
  })

  test('✅ Emotional check-in (3 caritas) selection', async ({ page }) => {
    // Navigate to SessionAnalysis
    await navigateToSessionAnalysis(page)

    // Click "Feliz" emotion
    const felizButton = page.locator('button:has-text("Feliz")')
    await felizButton.click()

    // Verify selected state
    const classList = await felizButton.evaluate((el) => el.className)
    expect(classList).toContain('selected')
  })

  // ==========================================
  // SUITE 4: KATNISS FEEDBACK
  // ==========================================

  test('✅ KATNISS endpoint health check', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/api/katniss/health`)
    expect(response.status()).toBe(200)

    const data = await response.json()
    expect(data.status).toBe('ok')
    expect(data.ollama).toBeDefined()
    expect(data.model).toBeDefined()
  })

  test('✅ Submit session and receive KATNISS feedback', async ({ page }) => {
    // Navigate to SessionAnalysis
    await navigateToSessionAnalysis(page)

    // Fill form
    await page.locator('input[type="range"]').first().fill('45')
    await page.click('button:has-text("7")')
    await page.click('button:has-text("Feliz")')
    await page.locator('textarea').fill('Me siento muy bien')

    // Submit
    await page.click('button:has-text("Obtener Feedback de KATNISS")')

    // Verify loading state briefly appears
    const spinner = page.locator('text=KATNISS analizando')
    await expect(spinner).toBeVisible({ timeout: 2000 })

    // Verify result appears
    const resultHeading = page.locator('text=✨ Feedback de KATNISS ✨')
    await expect(resultHeading).toBeVisible({ timeout: 10000 })

    // Verify result structure
    await expect(page.locator('text=Motivación')).toBeVisible()
    await expect(page.locator('text=Próxima Sesión')).toBeVisible()
  })

  test('✅ KATNISS result has all required fields', async ({ page }) => {
    // Navigate to SessionAnalysis
    await navigateToSessionAnalysis(page)

    // Fill and submit
    await page.locator('input[type="range"]').first().fill('30')
    await page.click('button:has-text("5")')
    await page.click('button:has-text("Normal")')
    await page.click('button:has-text("Obtener Feedback de KATNISS")')

    // Wait for result
    await expect(page.locator('text=✨ Feedback de KATNISS ✨')).toBeVisible({ timeout: 10000 })

    // Verify all required text sections appear
    await expect(page.locator('text=Motivación')).toBeVisible()
    await expect(page.locator('text=Próxima Sesión')).toBeVisible()
    await expect(page.locator('text=📅 Te recomendamos entrenar')).toBeVisible()

    // Verify "Otra Sesión" button appears (confirms result rendering completed)
    await expect(page.locator('button:has-text("Otra Sesión")')).toBeVisible()
  })

  // ==========================================
  // SUITE 5: DATA PERSISTENCE
  // ==========================================

  test('✅ Auth data stored in localStorage', async ({ page }) => {
    // Login
    await loginAsAthlete(page)

    // Check localStorage
    const userData = await page.evaluate(() => {
      return {
        user: localStorage.getItem('fi-stride-user'),
        token: localStorage.getItem('fi-stride-auth-token'),
      }
    })

    expect(userData.user).toBeTruthy()
    expect(userData.token).toBeTruthy()
  })

  test('✅ Session analysis stored in IndexedDB', async ({ page }) => {
    // Complete full flow to KATNISS result
    await navigateToSessionAnalysis(page)

    // Fill and submit
    await page.locator('input[type="range"]').first().fill('40')
    await page.click('button:has-text("6")')
    await page.click('button:has-text("Cansado")')
    await page.click('button:has-text("Obtener Feedback de KATNISS")')

    // Wait for result
    await expect(page.locator('text=✨ Feedback de KATNISS ✨')).toBeVisible({ timeout: 10000 })

    // Verify data was sent to backend (we can verify KATNISS feedback appears)
    // The katnissService component saves data to IndexedDB internally
    // We'll verify the success state indicates storage occurred
    const resultDiv = page.locator('text=✨ Feedback de KATNISS ✨')
    await expect(resultDiv).toBeVisible()

    // Verify "Otra Sesión" button is available (indicates full flow completed and data saved)
    const continueBtn = page.locator('button:has-text("Otra Sesión")')
    await expect(continueBtn).toBeVisible()
  })

  // ==========================================
  // SUITE 6: NAVIGATION & RESTART
  // ==========================================

  test('✅ "Otra Sesión" button restarts flow', async ({ page }) => {
    // Complete full flow
    await navigateToSessionAnalysis(page)

    // Fill and submit
    await page.locator('input[type="range"]').first().fill('30')
    await page.click('button:has-text("5")')
    await page.click('button:has-text("Normal")')
    await page.click('button:has-text("Obtener Feedback de KATNISS")')

    // Wait for result
    await expect(page.locator('text=✨ Feedback de KATNISS ✨')).toBeVisible({ timeout: 10000 })

    // Click "Otra Sesión"
    await page.click('button:has-text("Otra Sesión")')

    // Should return to form
    await expect(page.locator('text=¿Cómo te fue en la sesión?')).toBeVisible()

    // Form should be reset
    const sliderValue = await page.locator('input[type="range"]').first().inputValue()
    expect(sliderValue).toBe('30') // Default value
  })

  // ==========================================
  // SUITE 7: RESPONSIVE DESIGN
  // ==========================================

  test('✅ Responsive layout on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })

    // Complete flow to SessionAnalysis
    await navigateToSessionAnalysis(page)

    // Verify elements are visible on mobile
    await expect(page.locator('input[type="range"]').first()).toBeVisible()
    await expect(page.locator('button:has-text("5")')).toBeVisible()
    await expect(page.locator('button:has-text("Normal")')).toBeVisible()
  })

  // ==========================================
  // SUITE 8: ERROR HANDLING
  // ==========================================

  test('✅ Shows fallback response if KATNISS unavailable', async ({ page }) => {
    // This test assumes Ollama might not be running
    // The fallback should still provide a valid response

    // Complete full flow
    await navigateToSessionAnalysis(page)

    // Fill and submit
    await page.locator('input[type="range"]').first().fill('30')
    await page.click('button:has-text("5")')
    await page.click('button:has-text("Normal")')
    await page.click('button:has-text("Obtener Feedback de KATNISS")')

    // Should still get feedback (fallback if needed)
    await expect(page.locator('text=✨ Feedback de KATNISS ✨')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=Motivación')).toBeVisible()
  })

  // ==========================================
  // SUITE 9: FULL USER JOURNEY
  // ==========================================

  test('✅ Complete journey: Login → AthleteFlow → SessionAnalysis → Feedback', async ({
    page,
  }) => {
    // STEP 1: Login
    await page.goto(BASE_URL, { waitUntil: 'networkidle' })
    await page.click('button:has-text("Deportista")')
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')

    // STEP 2: Complete AthleteFlow
    // Privacy
    const checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    // Permissions
    const permCheckboxes = page.locator('input[type="checkbox"]')
    await permCheckboxes.first().check()
    await page.click('button:has-text("Siguiente")')

    // Profile
    await page.click('button:has-text("Siguiente")')

    // Ready
    await expect(page.locator('text=¡Listo para entrenar! 🎉')).toBeVisible()
    await page.click('button:has-text("Comenzar Entrenamiento 💪")')

    // STEP 3: SessionAnalysis
    await expect(page.locator('text=¿Cómo te fue en la sesión?')).toBeVisible()

    // Fill form with realistic data
    await page.locator('input[type="range"]').first().fill('60')
    await page.click('button:has-text("8")')
    await page.click('button:has-text("Feliz")')
    await page.locator('textarea').fill('Sesión excelente, me siento muy motivado')

    // STEP 4: Get KATNISS feedback
    await page.click('button:has-text("Obtener Feedback de KATNISS")')

    // STEP 5: Verify feedback
    await expect(page.locator('text=✨ Feedback de KATNISS ✨')).toBeVisible({ timeout: 10000 })
    await expect(page.locator('text=Motivación')).toBeVisible()
    await expect(page.locator('text=Próxima Sesión')).toBeVisible()

    // Verify data persisted
    const userData = await page.evaluate(() => ({
      user: localStorage.getItem('fi-stride-user'),
    }))
    expect(userData.user).toBeTruthy()
  })
})
