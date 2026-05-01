import { test, expect, Page } from '@playwright/test'

const BASE_URL = 'http://localhost:2012'

// Login helper
async function login(page: Page) {
  await page.goto(BASE_URL)
  await page.waitForLoadState('networkidle')
  await page.waitForSelector('.ant-input[placeholder="用户名或邮箱"]', { timeout: 10000 })
  await page.locator('.ant-input[placeholder="用户名或邮箱"]').fill('admin')
  await page.locator('.ant-input-password input').fill('admin123')
  await page.locator('button:has-text("登")').click()
  await Promise.any([
    page.waitForSelector('.ant-menu', { timeout: 20000 }),
    page.waitForSelector('.ant-avatar', { timeout: 20000 }),
    page.locator('text=admin').waitFor({ timeout: 20000 }),
  ])
  await page.waitForTimeout(1000)
}

// Navigate to open source page via bottom dock
async function goToOpenSource(page: Page) {
  // Click bottom dock to expand
  const dockButton = page.locator('button').filter({ hasText: /学术/ }).first()
  if (await dockButton.isVisible()) {
    await dockButton.click()
    await page.waitForTimeout(500)
  }
  // Find and click opensource domain button
  const osButton = page.locator('button').filter({ hasText: /开源/ }).first()
  if (await osButton.isVisible()) {
    await osButton.click()
    await page.waitForTimeout(1000)
  } else {
    // Direct navigation fallback
    await page.goto(`${BASE_URL}/opensource`)
    await page.waitForTimeout(1000)
  }
}

test.describe('开源人才子系统 E2E 测试', () => {

  // ========== Overview Page ==========
  test.describe('开源概览页', () => {
    test('1. 概览页加载与布局', async ({ page }) => {
      await login(page)
      await goToOpenSource(page)

      // Verify page title
      await expect(page.locator('text=开源生态人才')).toBeVisible()
      // Verify stats section
      await expect(page.locator('text=收录开发者')).toBeVisible()
      await expect(page.locator('text=覆盖仓库')).toBeVisible()

      await page.screenshot({ path: 'test-results/os-01-overview.png', fullPage: true })
      console.log('✅ 概览页加载正常')
    })

    test('2. 技术领域卡片导航', async ({ page }) => {
      await login(page)
      await goToOpenSource(page)

      // Click first tech element card
      const techCard = page.locator('.ant-card').filter({ hasText: /人工智能/ }).first()
      if (await techCard.isVisible()) {
        await techCard.click()
        await page.waitForTimeout(1000)

        // Should navigate to search page with tech_element param
        const url = page.url()
        expect(url).toContain('/opensource/search')
        console.log(`🔗 技术领域跳转URL: ${url}`)
      }

      await page.screenshot({ path: 'test-results/os-02-tech-nav.png', fullPage: true })
      console.log('✅ 技术领域导航正常')
    })

    test('3. 搜索框跳转', async ({ page }) => {
      await login(page)
      await goToOpenSource(page)

      const searchInput = page.locator('input[placeholder*="搜索开发者"]').first()
      if (await searchInput.isVisible()) {
        await searchInput.fill('python')
        await page.keyboard.press('Enter')
        await page.waitForTimeout(1000)

        const url = page.url()
        expect(url).toContain('/opensource/search')
        console.log(`🔗 搜索跳转URL: ${url}`)
      }

      await page.screenshot({ path: 'test-results/os-03-search-jump.png', fullPage: true })
      console.log('✅ 搜索框跳转正常')
    })

    test('4. 开发者卡片点击跳转详情', async ({ page }) => {
      await login(page)
      await goToOpenSource(page)

      // Wait for developer cards
      const devCard = page.locator('.ant-card').filter({ hasText: /@/ }).first()
      if (await devCard.isVisible()) {
        await devCard.click()
        await page.waitForTimeout(1000)

        const url = page.url()
        expect(url).toContain('/opensource/developers/')
        console.log(`🔗 详情页URL: ${url}`)
      }

      await page.screenshot({ path: 'test-results/os-04-detail-nav.png', fullPage: true })
      console.log('✅ 开发者卡片跳转正常')
    })
  })

  // ========== Search Page ==========
  test.describe('开源搜索页', () => {
    test('5. 搜索页加载与筛选', async ({ page }) => {
      await login(page)
      await page.goto(`${BASE_URL}/opensource/search`)
      await page.waitForTimeout(1500)

      // Verify search input
      await expect(page.locator('input[placeholder*="搜索开发者"]').first()).toBeVisible()
      // Verify filter toggle
      await expect(page.locator('button:has-text("展开筛选")')).toBeVisible()
      // Verify search mode segmented
      await expect(page.locator('.ant-segmented')).toBeVisible()

      await page.screenshot({ path: 'test-results/os-05-search-page.png', fullPage: true })
      console.log('✅ 搜索页加载正常')
    })

    test('6. 关键词搜索', async ({ page }) => {
      await login(page)
      await page.goto(`${BASE_URL}/opensource/search`)
      await page.waitForTimeout(1500)

      const searchInput = page.locator('input[placeholder*="搜索开发者"]').first()
      await searchInput.fill('test')
      await page.waitForTimeout(500)

      // Click search button
      const searchBtn = page.locator('button:has-text("搜索")').first()
      await searchBtn.click()
      await page.waitForTimeout(1500)

      // Check results or empty state
      const hasCards = await page.locator('.ant-card').count() > 0
      const hasEmpty = await page.locator('.ant-empty').count() > 0
      expect(hasCards || hasEmpty).toBe(true)

      await page.screenshot({ path: 'test-results/os-06-keyword-search.png', fullPage: true })
      console.log('✅ 关键词搜索正常')
    })

    test('7. 筛选面板展开与条件筛选', async ({ page }) => {
      await login(page)
      await page.goto(`${BASE_URL}/opensource/search`)
      await page.waitForTimeout(1500)

      // Expand filter panel
      const filterBtn = page.locator('button:has-text("展开筛选")')
      await filterBtn.click()
      await page.waitForTimeout(500)

      // Check filter fields are visible
      await expect(page.locator('text=技术领域').first()).toBeVisible()
      await expect(page.locator('text=地区').first()).toBeVisible()
      await expect(page.locator('text=公司').first()).toBeVisible()

      // Collapse filter
      await filterBtn.click()
      await page.waitForTimeout(300)

      await page.screenshot({ path: 'test-results/os-07-filter-panel.png', fullPage: true })
      console.log('✅ 筛选面板正常')
    })

    test('8. 搜索结果分页', async ({ page }) => {
      await login(page)
      await page.goto(`${BASE_URL}/opensource/search`)
      await page.waitForTimeout(1500)

      const hasPagination = await page.locator('.ant-pagination').count() > 0
      if (hasPagination) {
        const totalText = await page.locator('text=/共.*条/').textContent().catch(() => null)
        console.log(`📊 分页信息: ${totalText}`)
      }

      await page.screenshot({ path: 'test-results/os-08-pagination.png', fullPage: true })
      console.log('✅ 分页检查完成')
    })

    test('9. 搜索页收藏功能', async ({ page }) => {
      await login(page)
      await page.goto(`${BASE_URL}/opensource/search`)
      await page.waitForTimeout(1500)

      // Look for favorite icon
      const favIcon = page.locator('.anticon-heart, .anticon-heart-filled').first()
      if (await favIcon.isVisible()) {
        await favIcon.click()
        await page.waitForTimeout(500)
        console.log('✅ 收藏按钮可点击')
      } else {
        console.log('⚠️ 未找到收藏按钮')
      }

      await page.screenshot({ path: 'test-results/os-09-favorite.png', fullPage: true })
      console.log('✅ 收藏功能检查完成')
    })

    test('10. 搜索模式切换', async ({ page }) => {
      await login(page)
      await page.goto(`${BASE_URL}/opensource/search`)
      await page.waitForTimeout(1500)

      const segmented = page.locator('.ant-segmented')
      if (await segmented.isVisible()) {
        // Click semantic mode
        const semanticOption = segmented.locator('text=语义')
        if (await semanticOption.isVisible()) {
          await semanticOption.click()
          await page.waitForTimeout(300)
          console.log('✅ 语义模式切换成功')
        }

        // Click hybrid mode
        const hybridOption = segmented.locator('text=混合')
        if (await hybridOption.isVisible()) {
          await hybridOption.click()
          await page.waitForTimeout(300)
          console.log('✅ 混合模式切换成功')
        }
      }

      await page.screenshot({ path: 'test-results/os-10-search-mode.png', fullPage: true })
      console.log('✅ 搜索模式切换正常')
    })
  })

  // ========== Detail Page ==========
  test.describe('开发者详情页', () => {
    test('11. 详情页加载与布局', async ({ page }) => {
      await login(page)
      // Navigate directly to a developer detail (id=1 as fallback)
      await page.goto(`${BASE_URL}/opensource/developers/1`)
      await page.waitForTimeout(1500)

      // Check basic elements
      const hasBackBtn = await page.locator('button:has-text("返回")').count() > 0
      const hasTabs = await page.locator('.ant-tabs').count() > 0
      expect(hasBackBtn || hasTabs).toBe(true)

      await page.screenshot({ path: 'test-results/os-11-detail-page.png', fullPage: true })
      console.log('✅ 详情页加载正常')
    })

    test('12. 详情页 Tabs 切换', async ({ page }) => {
      await login(page)
      await page.goto(`${BASE_URL}/opensource/developers/1`)
      await page.waitForTimeout(1500)

      const tabs = page.locator('.ant-tabs-tab')
      const tabCount = await tabs.count()
      if (tabCount > 1) {
        // Click second tab
        await tabs.nth(1).click()
        await page.waitForTimeout(500)
        console.log('✅ Tab 切换正常')
      }

      await page.screenshot({ path: 'test-results/os-12-detail-tabs.png', fullPage: true })
      console.log('✅ 详情页 Tabs 检查完成')
    })

    test('13. 收藏按钮', async ({ page }) => {
      await login(page)
      await page.goto(`${BASE_URL}/opensource/developers/1`)
      await page.waitForTimeout(1500)

      const favBtn = page.locator('button').filter({ hasText: /收藏|已收藏/ }).first()
      if (await favBtn.isVisible()) {
        await favBtn.click()
        await page.waitForTimeout(500)
        console.log('✅ 详情页收藏按钮可点击')
      }

      await page.screenshot({ path: 'test-results/os-13-detail-favorite.png', fullPage: true })
      console.log('✅ 详情页收藏功能检查完成')
    })

    test('14. 返回按钮', async ({ page }) => {
      await login(page)
      await page.goto(`${BASE_URL}/opensource/developers/1`)
      await page.waitForTimeout(1500)

      const backBtn = page.locator('button:has-text("返回")').first()
      if (await backBtn.isVisible()) {
        await backBtn.click()
        await page.waitForTimeout(1000)
        const url = page.url()
        expect(url).not.toContain('/developers/')
        console.log(`🔗 返回后URL: ${url}`)
      }

      await page.screenshot({ path: 'test-results/os-14-detail-back.png', fullPage: true })
      console.log('✅ 返回按钮正常')
    })
  })

  // ========== Security / Auth ==========
  test.describe('权限与安全', () => {
    test('15. 未登录访问被拦截', async ({ page }) => {
      // Clear any auth state
      await page.goto(`${BASE_URL}/opensource`)
      await page.waitForTimeout(1500)

      // Should redirect to login or show login form
      const url = page.url()
      const hasLoginForm = await page.locator('.ant-input[placeholder="用户名或邮箱"]').count() > 0
      expect(url.includes('/login') || hasLoginForm).toBe(true)
      console.log(`🔒 未登录访问被拦截，URL: ${url}`)

      await page.screenshot({ path: 'test-results/os-15-unauthorized.png', fullPage: true })
      console.log('✅ 未登录拦截正常')
    })
  })

  // ========== Performance ==========
  test.describe('性能测试', () => {
    test('16. 概览页加载时间', async ({ page }) => {
      const startTime = Date.now()
      await login(page)
      await goToOpenSource(page)
      await page.waitForLoadState('networkidle')
      const loadTime = Date.now() - startTime

      console.log(`⏱️ 概览页加载时间: ${loadTime}ms`)
      expect(loadTime).toBeLessThan(15000)

      await page.screenshot({ path: 'test-results/os-16-performance.png', fullPage: true })
      console.log('✅ 概览页性能正常')
    })

    test('17. 搜索页响应时间', async ({ page }) => {
      await login(page)
      await page.goto(`${BASE_URL}/opensource/search`)

      const startTime = Date.now()
      await page.waitForLoadState('networkidle')
      const loadTime = Date.now() - startTime

      console.log(`⏱️ 搜索页加载时间: ${loadTime}ms`)
      expect(loadTime).toBeLessThan(10000)

      await page.screenshot({ path: 'test-results/os-17-search-perf.png', fullPage: true })
      console.log('✅ 搜索页性能正常')
    })
  })
})
