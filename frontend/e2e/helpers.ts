import { APIRequestContext, expect, Page } from '@playwright/test'

export interface E2EUser {
    username: string
    email: string
    password: string
    companyName: string
    subdomain: string
    firstName: string
    lastName: string
}

export function buildE2EUser(prefix: string = 'e2e'): E2EUser {
    const nonce = `${Date.now()}${Math.floor(Math.random() * 1000)}`
    const username = `${prefix}_${nonce}`
    return {
        username,
        email: `${username}@example.com`,
        password: 'TestPass123!',
        companyName: `Company ${nonce}`,
        subdomain: `${prefix}${nonce}`.toLowerCase(),
        firstName: 'E2E',
        lastName: 'Tester',
    }
}

export async function registerViaApi(request: APIRequestContext, user: E2EUser) {
    const response = await request.post('http://127.0.0.1:8000/api/v1/auth/register/', {
        data: {
            company_name: user.companyName,
            slug: user.subdomain,
            username: user.username,
            email: user.email,
            password: user.password,
        },
    })

    if (!response.ok()) {
        const body = await response.text()
        throw new Error(`Register API failed (${response.status()}): ${body}`)
    }
}

export async function registerViaUi(page: Page, user: E2EUser) {
    await page.goto('/register')
    await page.getByTestId('register-first-name').fill(user.firstName)
    await page.getByTestId('register-last-name').fill(user.lastName)
    await page.getByTestId('register-email').fill(user.email)
    await page.getByTestId('register-password').fill(user.password)
    await page.getByTestId('register-confirm-password').fill(user.password)
    await page.getByTestId('register-tenant-name').fill(user.companyName)
    await page.getByTestId('register-subdomain').fill(user.subdomain)
    await page.getByTestId('register-submit').click()
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 })
}

export async function loginViaUi(page: Page, username: string, password: string) {
    await page.goto('/login')
    await page.getByTestId('login-username').fill(username)
    await page.getByTestId('login-password').fill(password)
    await page.getByTestId('login-submit').click()
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 })
}

export async function logoutViaUi(page: Page) {
    await page.getByTestId('logout-button').click()
    await expect(page).toHaveURL(/\/login/)
}

export async function uploadTextDocument(page: Page, fileName: string, content: string) {
    await page.goto('/documents')

    await page.getByTestId('document-file-input').setInputFiles({
        name: fileName,
        mimeType: 'text/plain',
        buffer: Buffer.from(content),
    })

    const uploadPromise = page.waitForResponse((res) => {
        return res.url().includes('/api/v1/documents/upload/') && res.request().method() === 'POST'
    })

    await page.getByTestId('document-upload-button').click()
    const uploadResponse = await uploadPromise

    expect([201, 202]).toContain(uploadResponse.status())
}
