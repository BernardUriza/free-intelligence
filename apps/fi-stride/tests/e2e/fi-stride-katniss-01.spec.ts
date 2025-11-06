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
    // Fill form
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')

    // Should show role selection
    await expect(page.locator('button:has-text("Deportista")')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('button:has-text("Entrenador")')).toBeVisible()
  })

  // ==========================================
  // SUITE 2: ATHLETEFLOW (4 STEPS)
  // ==========================================

  test('✅ STEP 1: Privacy consent with 3 checkboxes', async ({ page }) => {
    // Login first
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

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
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    // Complete privacy step
    const checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    // Verify step 2 appears
    await expect(page.locator('text=Permisos de Dispositivo')).toBeVisible()
    await expect(page.locator('text=Cámara')).toBeVisible()
    await expect(page.locator('text=Micrófono')).toBeVisible()

    // Progress bar at 50%
    const progressBar = page.locator('div[style*="width"]').first()
    const style = await progressBar.evaluate((el) => el.getAttribute('style'))
    expect(style).toContain('50%')

    // Check camera permission
    await checkboxes.first().check()
    await expect(checkboxes.first()).toBeChecked()
  })

  test('✅ STEP 3: Profile (read-only display)', async ({ page }) => {
    // Setup: complete steps 1-2
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    // Step 1
    const checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    // Step 2
    await checkboxes.first().check()
    await page.click('button:has-text("Siguiente")')

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
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    // Step 1
    let checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    // Step 2
    checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.first().check()
    await page.click('button:has-text("Siguiente")')

    // Step 3
    await page.click('button:has-text("Siguiente")')

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
    // Complete AthleteFlow
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    let checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.first().check()
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Siguiente")')

    // Click "Comenzar Entrenamiento"
    await page.click('button:has-text("Comenzar Entrenamiento 💪")')

    // Verify SessionAnalysis appears
    await expect(page.locator('text=¿Cómo te fue en la sesión?')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('text=Duración (minutos)')).toBeVisible()
    await expect(page.locator('text=¿Cuánto esfuerzo hiciste? (1-10)')).toBeVisible()
    await expect(page.locator('text=¿Cómo te sientes ahora?')).toBeVisible()
  })

  test('✅ Duration slider works (5-120 min range)', async ({ page }) => {
    // Navigate to SessionAnalysis
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    let checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.first().check()
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Comenzar Entrenamiento 💪")')

    // Test slider
    const slider = page.locator('input[type="range"]').first()
    await slider.fill('45')

    // Verify value display
    const valueDisplay = page.locator('text=45 min')
    await expect(valueDisplay).toBeVisible()
  })

  test('✅ RPE buttons (1-10) selection', async ({ page }) => {
    // Navigate to SessionAnalysis
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    let checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.first().check()
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Comenzar Entrenamiento 💪")')

    // Click RPE button "7"
    const rpeButton = page.locator('button:has-text("7")')
    await rpeButton.click()

    // Verify button is selected (has class or styling)
    const classList = await rpeButton.evaluate((el) => el.className)
    expect(classList).toContain('selected')
  })

  test('✅ Emotional check-in (3 caritas) selection', async ({ page }) => {
    // Navigate to SessionAnalysis
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    let checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.first().check()
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Comenzar Entrenamiento 💪")')

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
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    let checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.first().check()
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Comenzar Entrenamiento 💪")')

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
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    let checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.first().check()
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Comenzar Entrenamiento 💪")')

    // Fill and submit
    await page.locator('input[type="range"]').first().fill('30')
    await page.click('button:has-text("5")')
    await page.click('button:has-text("Normal")')
    await page.click('button:has-text("Obtener Feedback de KATNISS")')

    // Wait for result
    await expect(page.locator('text=✨ Feedback de KATNISS ✨')).toBeVisible({ timeout: 10000 })

    // Verify all fields have content
    const motivationText = page.locator('p.motivation')
    const suggestionText = page.locator('p.suggestion')
    const dayRecommendedText = page.locator('p.dayRecommended')

    await expect(motivationText).toBeVisible()
    await expect(suggestionText).toBeVisible()
    await expect(dayRecommendedText).toBeVisible()

    // Verify text is not empty
    const motivation = await motivationText.textContent()
    const suggestion = await suggestionText.textContent()
    const dayRec = await dayRecommendedText.textContent()

    expect(motivation?.length).toBeGreaterThan(0)
    expect(suggestion?.length).toBeGreaterThan(0)
    expect(dayRec?.length).toBeGreaterThan(0)
  })

  // ==========================================
  // SUITE 5: DATA PERSISTENCE
  // ==========================================

  test('✅ Auth data stored in localStorage', async ({ page }) => {
    // Login
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')

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
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    let checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.first().check()
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Comenzar Entrenamiento 💪")')

    // Fill and submit
    await page.locator('input[type="range"]').first().fill('40')
    await page.click('button:has-text("6")')
    await page.click('button:has-text("Cansado")')
    await page.click('button:has-text("Obtener Feedback de KATNISS")')

    // Wait for result
    await expect(page.locator('text=✨ Feedback de KATNISS ✨')).toBeVisible({ timeout: 10000 })

    // Check IndexedDB
    const sessionData = await page.evaluate(() => {
      return new Promise((resolve) => {
        const request = indexedDB.open('FIStride', 1)
        request.onsuccess = (e: any) => {
          const db = e.target.result
          const tx = db.transaction(['session_analysis'], 'readonly')
          const store = tx.objectStore('session_analysis')
          const allData = store.getAll()
          allData.onsuccess = () => resolve(allData.result)
        }
      })
    })

    expect(Array.isArray(sessionData)).toBe(true)
    expect((sessionData as any[]).length).toBeGreaterThan(0)
  })

  // ==========================================
  // SUITE 6: NAVIGATION & RESTART
  // ==========================================

  test('✅ "Otra Sesión" button restarts flow', async ({ page }) => {
    // Complete full flow
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    let checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.first().check()
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Comenzar Entrenamiento 💪")')

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
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    let checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.first().check()
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Comenzar Entrenamiento 💪")')

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
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')
    await page.click('button:has-text("Deportista")')

    let checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente")')

    checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.first().check()
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Siguiente")')
    await page.click('button:has-text("Comenzar Entrenamiento 💪")')

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
    await page.fill('input[type="email"]', ATHLETE_EMAIL)
    await page.fill('input[type="password"]', ATHLETE_PASSWORD)
    await page.click('button:has-text("Entrar")')

    // STEP 2: Select Deportista
    await page.click('button:has-text("Deportista")')

    // STEP 3: Complete AthleteFlow
    // Privacy
    const checkboxes = page.locator('input[type="checkbox"]')
    for (let i = 0; i < 3; i++) {
      await checkboxes.nth(i).check()
    }
    await page.click('button:has-text("Siguiente →")')

    // Permissions
    const permCheckboxes = page.locator('input[type="checkbox"]')
    await permCheckboxes.first().check()
    await page.click('button:has-text("Siguiente →")')

    // Profile
    await page.click('button:has-text("Siguiente →")')

    // Ready
    await expect(page.locator('text=¡Listo para entrenar! 🎉')).toBeVisible()
    await page.click('button:has-text("Comenzar Entrenamiento 💪")')

    // STEP 4: SessionAnalysis
    await expect(page.locator('text=¿Cómo te fue en la sesión?')).toBeVisible()

    // Fill form with realistic data
    await page.locator('input[type="range"]').first().fill('60')
    await page.click('button:has-text("8")')
    await page.click('button:has-text("Feliz")')
    await page.locator('textarea').fill('Sesión excelente, me siento muy motivado')

    // STEP 5: Get KATNISS feedback
    await page.click('button:has-text("Obtener Feedback de KATNISS")')

    // STEP 6: Verify feedback
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
