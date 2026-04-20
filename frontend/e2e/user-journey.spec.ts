import { test, expect } from '@playwright/test'
import { buildE2EUser, loginViaUi, logoutViaUi, registerViaApi, registerViaUi, uploadTextDocument } from './helpers'

test.describe('Complete User Journey', () => {
    test('completes registration, document upload, navigation, and logout', async ({ page }) => {
        const user = buildE2EUser('journey')

        await page.goto('/')
        await expect(page.locator('h1').first()).toBeVisible()

        await registerViaUi(page, user)

        await uploadTextDocument(page, 'journey-doc.txt', 'E2E journey document content')

        await expect(page.locator('text=journey-doc.txt')).toBeVisible({ timeout: 10000 })

        await page.goto('/chat')
        await expect(page).toHaveURL(/\/chat/)
        await expect(
            page.getByTestId('chat-input').or(page.getByTestId('chat-go-documents-link'))
        ).toBeVisible()

        await page.goto('/analytics')
        await expect(page.locator('[data-testid="analytics-stat-card"]')).toHaveCount(3)

        await page.goto('/settings')
        await expect(page.getByTestId('settings-username')).toHaveValue(user.username)

        await logoutViaUi(page)
    })

    test('navigates between protected pages after login', async ({ page, request }) => {
        const user = buildE2EUser('journey_nav')
        await registerViaApi(request, user)
        await loginViaUi(page, user.username, user.password)

        const routes = ['/dashboard', '/documents', '/chat', '/analytics', '/channels', '/settings']

        for (const route of routes) {
            await page.goto(route)
            await expect(page).toHaveURL(new RegExp(route))
        }
    })
})
