import { test, expect } from '@playwright/test'
import { buildE2EUser, loginViaUi, registerViaApi } from './helpers'

test.describe('Channel Management', () => {
    test.beforeEach(async ({ page, request }) => {
        const user = buildE2EUser('channels')
        await registerViaApi(request, user)
        await loginViaUi(page, user.username, user.password)
    })

    test('opens channels page', async ({ page }) => {
        await page.goto('/channels')

        await expect(page).toHaveURL(/\/channels/)
        await expect(page.getByRole('heading', { name: 'Telegram' })).toBeVisible()
        await expect(page.getByRole('heading', { name: 'WhatsApp' })).toBeVisible()
    })

    test('opens Telegram connection form', async ({ page }) => {
        await page.goto('/channels')

        await page.getByTestId('telegram-start-connect').click()
        await expect(page.getByTestId('telegram-token-input')).toBeVisible()
    })

    test('opens WhatsApp connection form', async ({ page }) => {
        await page.goto('/channels')

        await page.getByTestId('whatsapp-start-connect').click()
        await expect(page.getByTestId('whatsapp-token-input')).toBeVisible()
        await expect(page.getByTestId('whatsapp-phone-id-input')).toBeVisible()
    })
})
