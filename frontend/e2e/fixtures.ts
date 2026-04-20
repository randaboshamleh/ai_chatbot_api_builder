import { test as base } from '@playwright/test'
import { buildE2EUser, loginViaUi, registerViaApi } from './helpers'

type TestFixtures = {
    authenticatedPage: any
}

export const test = base.extend<TestFixtures>({
    authenticatedPage: async ({ page, request }, use) => {
        const user = buildE2EUser('fixture')
        await registerViaApi(request, user)
        await loginViaUi(page, user.username, user.password)
        await use(page)
    },
})

export { expect } from '@playwright/test'
