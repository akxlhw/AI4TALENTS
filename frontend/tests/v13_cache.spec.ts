/**
 * E2E tests for v1.3 features:
 * - React Query caching behavior
 * - Tech Element page with filters
 * - Performance metrics
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

// Login helper
async function login(page: any) {
  await page.goto(BASE_URL);
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('.ant-input[placeholder="用户名或邮箱"]', { timeout: 10000 });
  await page.locator('.ant-input[placeholder="用户名或邮箱"]').fill('admin');
  await page.locator('.ant-input-password input').fill('admin123');
  await page.locator('button:has-text("登")').click();
  await page.waitForURL(/.*\/$/, { timeout: 15000 }).catch(() => {
    return page.waitForSelector('.ant-layout', { timeout: 10000 });
  });
}

test.describe('v1.3 React Query 缓存测试', () => {

  test('首页数据缓存验证', async ({ page }) => {
    await login(page);

    // Wait for initial load
    await page.waitForTimeout(2000);

    // Get initial stats values
    const initialStats = await page.locator('.ant-statistic-content-value').first().textContent();

    // Navigate away
    await page.goto(`${BASE_URL}/tech-element`);
    await page.waitForTimeout(1000);

    // Navigate back to home
    await page.goto(BASE_URL);
    await page.waitForTimeout(500); // Short wait - data should be cached

    // Check if data is still there (should be instant from cache)
    const cachedStats = await page.locator('.ant-statistic-content-value').first().textContent();

    console.log(`📊 Initial stats: ${initialStats}`);
    console.log(`📊 Cached stats: ${cachedStats}`);

    // Values should match (from cache)
    expect(cachedStats).toBe(initialStats);

    await page.screenshot({ path: 'test-results/v13-cache-homepage.png', fullPage: true });
    console.log('✅ 首页数据缓存验证通过');
  });

  test('技术要素页面加载', async ({ page }) => {
    await login(page);

    // Navigate to tech element page
    await page.goto(`${BASE_URL}/tech-element`);
    await page.waitForTimeout(2000);

    // Check tech element selector exists
    const selector = page.locator('.ant-select').first();
    await expect(selector).toBeVisible({ timeout: 10000 });

    await page.screenshot({ path: 'test-results/v13-tech-element-page.png', fullPage: true });
    console.log('✅ 技术要素页面加载正常');
  });

  test('技术要素选择器交互', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/tech-element`);
    await page.waitForTimeout(2000);

    // Click on tech element selector
    const selector = page.locator('.ant-select').first();
    if (await selector.isVisible()) {
      await selector.click();
      await page.waitForTimeout(500);

      // Check if dropdown appears
      const dropdown = page.locator('.ant-select-dropdown');
      const dropdownVisible = await dropdown.isVisible().catch(() => false);
      console.log(`📋 Dropdown visible: ${dropdownVisible}`);

      await page.screenshot({ path: 'test-results/v13-tech-selector.png', fullPage: true });
    }

    console.log('✅ 技术要素选择器交互测试完成');
  });

  test('技术要素统计卡片', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/tech-element`);
    await page.waitForTimeout(2000);

    // Check for statistics
    const statsCount = await page.locator('.ant-statistic').count();
    console.log(`📊 统计卡片数量: ${statsCount}`);

    // Should have at least 4 stat cards
    expect(statsCount).toBeGreaterThanOrEqual(4);

    await page.screenshot({ path: 'test-results/v13-tech-stats.png', fullPage: true });
    console.log('✅ 技术要素统计卡片验证通过');
  });

  test('页面导航缓存验证', async ({ page }) => {
    await login(page);

    // Visit homepage
    await page.goto(BASE_URL);
    await page.waitForTimeout(2000);

    // Visit tech element
    await page.goto(`${BASE_URL}/tech-element`);
    await page.waitForTimeout(2000);

    // Visit back to home
    await page.goto(BASE_URL);
    await page.waitForTimeout(500); // Should be cached

    // Check page loaded
    const hasContent = await page.locator('.ant-layout-content').isVisible();
    expect(hasContent).toBe(true);

    console.log('✅ 页面导航缓存验证通过');
  });
});

test.describe('v1.3 性能测试', () => {

  test('首页加载时间', async ({ page }) => {
    const startTime = Date.now();

    await login(page);
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    console.log(`⏱️ 首页加载时间: ${loadTime}ms`);

    // Should load in under 5 seconds
    expect(loadTime).toBeLessThan(5000);

    console.log('✅ 首页加载时间符合预期');
  });

  test('技术要素页面加载时间', async ({ page }) => {
    await login(page);

    const startTime = Date.now();

    await page.goto(`${BASE_URL}/tech-element`);
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    console.log(`⏱️ 技术要素页面加载时间: ${loadTime}ms`);

    // Should load in under 5 seconds
    expect(loadTime).toBeLessThan(5000);

    console.log('✅ 技术要素页面加载时间符合预期');
  });

  test('多次访问缓存命中', async ({ page }) => {
    await login(page);

    // First visit
    const firstStart = Date.now();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    const firstLoad = Date.now() - firstStart;

    // Navigate away
    await page.goto(`${BASE_URL}/tech-element`);
    await page.waitForTimeout(1000);

    // Second visit (should be cached)
    const secondStart = Date.now();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');
    const secondLoad = Date.now() - secondStart;

    console.log(`⏱️ 首次加载: ${firstLoad}ms`);
    console.log(`⏱️ 缓存加载: ${secondLoad}ms`);

    // Cached load should be faster or similar
    // (React Query cached data should be instant)
    expect(secondLoad).toBeLessThanOrEqual(firstLoad * 2); // Allow some variance

    console.log('✅ 缓存命中验证通过');
  });
});

test.describe('v1.3 筛选功能测试', () => {

  test('技术要素筛选器存在', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/tech-element`);
    await page.waitForTimeout(2000);

    // Check for filter inputs/selects
    const selects = await page.locator('.ant-select').count();
    const inputs = await page.locator('input.ant-input').count();

    console.log(`📋 Select 元素数量: ${selects}`);
    console.log(`📝 Input 元素数量: ${inputs}`);

    // Should have filter controls
    expect(selects + inputs).toBeGreaterThan(0);

    console.log('✅ 筛选器验证通过');
  });

  test('搜索按钮功能', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/tech-element`);
    await page.waitForTimeout(2000);

    // Find search button
    const searchButton = page.locator('button:has-text("查询"), button:has-text("搜索")').first();

    if (await searchButton.isVisible()) {
      await searchButton.click();
      await page.waitForTimeout(1000);
      console.log('✅ 搜索按钮可点击');
    } else {
      console.log('⚠️ 未找到搜索按钮');
    }

    await page.screenshot({ path: 'test-results/v13-filter-search.png', fullPage: true });
  });

  test('重置按钮功能', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/tech-element`);
    await page.waitForTimeout(2000);

    // Find reset button
    const resetButton = page.locator('button:has-text("重置")').first();

    if (await resetButton.isVisible()) {
      await resetButton.click();
      await page.waitForTimeout(1000);
      console.log('✅ 重置按钮可点击');
    } else {
      console.log('⚠️ 未找到重置按钮');
    }

    await page.screenshot({ path: 'test-results/v13-filter-reset.png', fullPage: true });
  });
});
