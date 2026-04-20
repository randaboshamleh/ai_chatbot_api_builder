import { test, expect } from '@playwright/test'
import { buildE2EUser, loginViaUi, registerViaApi } from './helpers'

test.describe('Settings Page', () => {
    test.beforeEach(async ({ page, request }) => {
        const user = buildE2EUser('settings')
        await registerViaApi(request, user)
        await loginViaUi(page, user.username, user.password)
    })

    test('opens settings page', async ({ page }) => {
        await page.goto('/settings')

        await expect(page).toHaveURL(/\/settings/)
        await expect(page.getByTestId('settings-username')).toBeVisible()
        await expect(page.getByTestId('settings-email')).toBeVisible()
        await expect(page.getByTestId('settings-tenant-name')).toBeVisible()
    })

    test('settings fields are read-only', async ({ page }) => {
        await page.goto('/settings')

        await expect(page.getByTestId('settings-username')).toBeDisabled()
        await expect(page.getByTestId('settings-email')).toBeDisabled()
        await expect(page.getByTestId('settings-tenant-name')).toBeDisabled()
    })
})
