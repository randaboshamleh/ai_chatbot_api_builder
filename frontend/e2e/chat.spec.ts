import { test, expect } from '@playwright/test'
import { buildE2EUser, loginViaUi, registerViaApi, uploadTextDocument } from './helpers'

test.describe('Chat Functionality', () => {
    test.beforeEach(async ({ page, request }) => {
        const user = buildE2EUser('chat')
        await registerViaApi(request, user)
        await loginViaUi(page, user.username, user.password)
    })

    test('opens chat page', async ({ page }) => {
        await page.goto('/chat')
        await expect(page).toHaveURL(/\/chat/)
    })

    test('shows guidance state when there are no indexed documents', async ({ page }) => {
        await page.goto('/chat')

        await expect(page.getByTestId('chat-go-documents-link')).toBeVisible()
    })

    test('keeps chat page functional after uploading a document', async ({ page }) => {
        await uploadTextDocument(page, 'chat-source.txt', 'content for chat source')

        await page.goto('/chat')

        await expect(
            page.getByTestId('chat-input').or(page.getByTestId('chat-go-documents-link'))
        ).toBeVisible()
    })
})
