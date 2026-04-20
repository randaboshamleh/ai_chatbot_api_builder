import { test, expect } from '@playwright/test'
import { buildE2EUser, loginViaUi, logoutViaUi, registerViaApi, registerViaUi } from './helpers'

test.describe('Authentication Flow', () => {
    test('registers a new user from UI and lands on dashboard', async ({ page }) => {
        const user = buildE2EUser('auth_ui')

        await registerViaUi(page, user)

        await expect(page.getByTestId('nav-dashboard')).toBeVisible()
        await expect(page.getByTestId('logout-button')).toBeVisible()
    })

    test('logs in with an existing user', async ({ page, request }) => {
        const user = buildE2EUser('auth_login')
        await registerViaApi(request, user)

        await loginViaUi(page, user.username, user.password)

        await expect(page.getByTestId('nav-dashboard')).toBeVisible()
    })

    test('shows an error for invalid credentials', async ({ page }) => {
        await page.goto('/login')

        await page.getByTestId('login-username').fill('non_existing_user')
        await page.getByTestId('login-password').fill('wrong_password')
        await page.getByTestId('login-submit').click()

        await expect(page).toHaveURL(/\/login/)
        await expect(page.getByTestId('auth-error')).toBeVisible()
    })

    test('logs out successfully', async ({ page, request }) => {
        const user = buildE2EUser('auth_logout')
        await registerViaApi(request, user)

        await loginViaUi(page, user.username, user.password)
        await logoutViaUi(page)

        await expect(page.getByTestId('login-form')).toBeVisible()
    })
})
