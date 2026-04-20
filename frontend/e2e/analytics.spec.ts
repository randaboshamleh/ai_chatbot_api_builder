import { test, expect } from '@playwright/test'
import { buildE2EUser, loginViaUi, registerViaApi } from './helpers'

test.describe('Analytics Dashboard', () => {
    test.beforeEach(async ({ page, request }) => {
        const user = buildE2EUser('analytics')
        await registerViaApi(request, user)
        await loginViaUi(page, user.username, user.password)
    })

    test('opens analytics page', async ({ page }) => {
        await page.goto('/analytics')

        await expect(page).toHaveURL(/\/analytics/)
        await expect(page.locator('[data-testid="analytics-stat-card"]')).toHaveCount(3)
    })

    test('shows recent queries section', async ({ page }) => {
        await page.goto('/analytics')

        await expect(page.locator('[data-testid="analytics-recent-queries"]')).toBeVisible()
    })
})
