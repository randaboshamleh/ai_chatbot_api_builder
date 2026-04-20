import { test, expect } from '@playwright/test'

test.describe('Example Tests - Setup Verification', () => {
    test('@smoke loads the landing page', async ({ page }) => {
        await page.goto('/')

        await expect(page).toHaveTitle(/AI Chatbot/i)
        await expect(page.locator('h1').first()).toBeVisible()
    })

    test('has working auth navigation links', async ({ page }) => {
        await page.goto('/')

        await page.getByTestId('landing-login-link').click()
        await expect(page).toHaveURL(/\/login/)

        await page.goto('/')
        await page.getByTestId('landing-register-link').click()
        await expect(page).toHaveURL(/\/register/)
    })

    test('is responsive on desktop and mobile', async ({ page }) => {
        await page.setViewportSize({ width: 1920, height: 1080 })
        await page.goto('/')
        await expect(page.locator('body')).toBeVisible()

        await page.setViewportSize({ width: 375, height: 667 })
        await page.goto('/')
        await expect(page.locator('body')).toBeVisible()
    })
})
