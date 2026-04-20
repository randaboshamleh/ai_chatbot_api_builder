import { test, expect } from '@playwright/test'
import { buildE2EUser, loginViaUi, registerViaApi, uploadTextDocument } from './helpers'

test.describe('Document Management', () => {
    test.beforeEach(async ({ page, request }) => {
        const user = buildE2EUser('docs')
        await registerViaApi(request, user)
        await loginViaUi(page, user.username, user.password)
    })

    test('opens the documents page with upload controls', async ({ page }) => {
        await page.goto('/documents')

        await expect(page.getByTestId('document-file-input')).toBeAttached()
        await expect(page.getByTestId('document-upload-button')).toBeVisible()
    })

    test('uploads a text document successfully', async ({ page }) => {
        await uploadTextDocument(page, 'upload-test.txt', 'upload test content')

        await expect(page.locator('text=upload-test.txt')).toBeVisible({ timeout: 10000 })
    })

    test('shows uploaded documents in the list', async ({ page }) => {
        await uploadTextDocument(page, 'list-test.txt', 'list test content')

        await expect(page.locator('[data-testid^="document-card-"]')).toHaveCount(1)
    })

    test('deletes an uploaded document', async ({ page }) => {
        await uploadTextDocument(page, 'delete-test.txt', 'delete test content')

        const deleteButton = page.locator('[data-testid^="document-delete-"]').first()
        await expect(deleteButton).toBeVisible()

        const deletePromise = page.waitForResponse((res) => {
            return res.url().includes('/api/v1/documents/') && res.request().method() === 'DELETE'
        })

        await deleteButton.click()
        const deleteResponse = await deletePromise

        expect(deleteResponse.status()).toBe(204)
        await expect(page.locator('[data-testid^="document-card-"]')).toHaveCount(0)
    })
})
