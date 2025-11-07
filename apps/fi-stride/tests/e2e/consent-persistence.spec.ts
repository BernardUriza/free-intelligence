import { test, expect } from '@playwright/test'

test.describe('Consent Persistence', () => {
  test('should show consent form on first visit', async ({ page, context }) => {
    // Clear all storage to simulate first visit
    await context.clearCookies()
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })

    await page.goto('http://localhost:9050/')

    // Should see the privacy consent form
    await expect(page.locator('text=Privacidad y Consentimiento')).toBeVisible()
    await expect(page.locator('text=Política de Privacidad')).toBeVisible()
  })

  test('should skip consent form on subsequent visits after accepting', async ({ page, context }) => {
    // Set consent in localStorage to simulate previous acceptance
    await page.goto('http://localhost:9050/')

    await page.evaluate(() => {
      localStorage.setItem('fi-stride-consent-accepted', 'true')
      localStorage.setItem('fi-stride-consent-date', new Date().toISOString())
    })

    // Reload page to trigger fresh component mount
    await page.reload()

    // Should skip consent and go directly to permissions step
    await expect(page.locator('text=Privacidad y Consentimiento')).not.toBeVisible()
    await expect(page.locator('text=Permisos de Dispositivo')).toBeVisible()
  })

  test('should persist consent in localStorage after accepting all checkboxes', async ({ page }) => {
    // Clear storage
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })

    await page.goto('http://localhost:9050/')

    // Should see consent form
    await expect(page.locator('text=Privacidad y Consentimiento')).toBeVisible()

    // Check all consent checkboxes
    const checkboxes = page.locator('input[type="checkbox"]')
    const count = await checkboxes.count()

    for (let i = 0; i < count; i++) {
      await checkboxes.nth(i).check()
    }

    // Click next button
    await page.locator('button:has-text("Siguiente →")').click()

    // Verify localStorage was set
    const consentFlag = await page.evaluate(() => localStorage.getItem('fi-stride-consent-accepted'))
    expect(consentFlag).toBe('true')

    const consentDate = await page.evaluate(() => localStorage.getItem('fi-stride-consent-date'))
    expect(consentDate).toBeTruthy()
    expect(consentDate).toMatch(/\d{4}-\d{2}-\d{2}/) // ISO date format
  })

  test('should require all three consent checkboxes before allowing next', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })

    await page.goto('http://localhost:9050/')

    await expect(page.locator('text=Privacidad y Consentimiento')).toBeVisible()

    // Check only first checkbox
    const firstCheckbox = page.locator('input[type="checkbox"]').first()
    await firstCheckbox.check()

    // Next button should be disabled
    const nextButton = page.locator('button:has-text("Siguiente →")')
    await expect(nextButton).toHaveAttribute('disabled', '')

    // Check second checkbox
    const checkboxes = page.locator('input[type="checkbox"]')
    await checkboxes.nth(1).check()

    // Still disabled
    await expect(nextButton).toHaveAttribute('disabled', '')

    // Check third checkbox
    await checkboxes.nth(2).check()

    // Now enabled
    await expect(nextButton).not.toHaveAttribute('disabled', '')
  })

  test('should persist consent across page reloads and navigations', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.clear()
      sessionStorage.clear()
    })

    await page.goto('http://localhost:9050/')

    // Accept consent
    const checkboxes = page.locator('input[type="checkbox"]')
    const count = await checkboxes.count()
    for (let i = 0; i < count; i++) {
      await checkboxes.nth(i).check()
    }
    await page.locator('button:has-text("Siguiente →")').click()

    // Should be on permissions step now
    await expect(page.locator('text=Permisos de Dispositivo')).toBeVisible()

    // Reload page
    await page.reload()

    // Should still be on permissions (consent skipped)
    await expect(page.locator('text=Permisos de Dispositivo')).toBeVisible()
    await expect(page.locator('text=Privacidad y Consentimiento')).not.toBeVisible()
  })
})
