import { test, expect } from '@playwright/test'

test.describe('Language Switching', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/')
    })

    test('toggles layout direction to RTL and back to LTR', async ({ page }) => {
        await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')

        await page.getByTestId('language-toggle').click()
        await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')

        await page.getByTestId('language-toggle').click()
        await expect(page.locator('html')).toHaveAttribute('dir', 'ltr')
    })

    test('persists selected language after reload', async ({ page }) => {
        await page.getByTestId('language-toggle').click()
        await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')

        await page.reload()

        await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
    })
})
