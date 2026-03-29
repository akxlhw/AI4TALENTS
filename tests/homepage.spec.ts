import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';
const API_URL = 'http://localhost:8003';

test.describe('首页功能测试', () => {

  // 登录获取 token
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    // 登录获取 token
    const response = await request.post(`${API_URL}/api/v1/auth/login`, {
      data: {
        username: 'admin',
        password: 'admin123'
      }
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    authToken = data.access_token;
    console.log('✅ 登录成功，获取到 token');
  });

  test('1. 登录页面加载', async ({ page }) => {
    await page.goto(BASE_URL);

    // 验证登录页面元素
    await expect(page.locator('input[placeholder*="用户名"]')).toBeVisible();
    await expect(page.locator('input[placeholder*="密码"]')).toBeVisible();
    await expect(page.locator('button:has-text("登录")')).toBeVisible();

    console.log('✅ 登录页面加载正常');
  });

  test('2. 登录流程', async ({ page }) => {
    await page.goto(BASE_URL);

    // 输入登录信息
    await page.locator('input[placeholder*="用户名"]').fill('admin');
    await page.locator('input[placeholder*="密码"]').fill('admin123');
    await page.locator('button:has-text("登录")').click();

    // 等待跳转到首页
    await page.waitForURL(/.*\/|.*home/, { timeout: 10000 });

    // 验证已登录状态
    await expect(page.locator('text=首页')).toBeVisible({ timeout: 10000 });

    console.log('✅ 登录流程正常');
  });

  test('3. 首页基础统计展示', async ({ page }) => {
    // 先登录
    await page.goto(BASE_URL);
    await page.locator('input[placeholder*="用户名"]').fill('admin');
    await page.locator('input[placeholder*="密码"]').fill('admin123');
    await page.locator('button:has-text("登录")').click();
    await page.waitForURL(/.*\/|.*home/, { timeout: 10000 });

    // 等待统计数据加载
    await page.waitForTimeout(2000);

    // 截图保存
    await page.screenshot({ path: 'test-results/homepage-stats.png', fullPage: true });

    // 验证统计卡片存在
    const statCards = await page.locator('.ant-statistic, [class*="statistic"]').count();
    console.log(`📊 统计卡片数量: ${statCards}`);

    // 检查是否有数字统计
    const numbers = await page.locator('.ant-statistic-content-value, [class*="statistic"] .ant-typography').count();
    expect(numbers).toBeGreaterThan(0);

    console.log('✅ 基础统计展示正常');
  });

  test('4. 双主视角概要卡', async ({ page }) => {
    // 登录
    await page.goto(BASE_URL);
    await page.locator('input[placeholder*="用户名"]').fill('admin');
    await page.locator('input[placeholder*="密码"]').fill('admin123');
    await page.locator('button:has-text("登录")').click();
    await page.waitForURL(/.*\/|.*home/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    // 检查技术要素概要卡
    const techCard = await page.locator('text=技术要素').count();
    console.log(`🔍 技术要素相关元素: ${techCard}`);

    // 检查国家院校概要卡
    const countryCard = await page.locator('text=国家院校, text=院校').count();
    console.log(`🌍 国家院校相关元素: ${countryCard}`);

    // 截图
    await page.screenshot({ path: 'test-results/homepage-cards.png', fullPage: true });

    console.log('✅ 双主视角概要卡检查完成');
  });

  test('5. 热点标签区', async ({ page }) => {
    // 登录
    await page.goto(BASE_URL);
    await page.locator('input[placeholder*="用户名"]').fill('admin');
    await page.locator('input[placeholder*="密码"]').fill('admin123');
    await page.locator('button:has-text("登录")').click();
    await page.waitForURL(/.*\/|.*home/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    // 检查标签
    const tags = await page.locator('.ant-tag').count();
    console.log(`🏷️ 标签数量: ${tags}`);

    // 检查热门技术要素标签
    const hotTechTags = await page.locator('text=热门技术要素, text=重点国家, text=重点院校').count();
    console.log(`🔥 热点标签区元素: ${hotTechTags}`);

    await page.screenshot({ path: 'test-results/homepage-tags.png', fullPage: true });

    console.log('✅ 热点标签区检查完成');
  });

  test('6. 搜索功能', async ({ page }) => {
    // 登录
    await page.goto(BASE_URL);
    await page.locator('input[placeholder*="用户名"]').fill('admin');
    await page.locator('input[placeholder*="密码"]').fill('admin123');
    await page.locator('button:has-text("登录")').click();
    await page.waitForURL(/.*\/|.*home/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    // 查找搜索框
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="关键词"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('AI');

      // 点击搜索按钮
      const searchBtn = page.locator('button:has-text("搜索"), button[type="submit"]').first();
      if (await searchBtn.isVisible()) {
        await searchBtn.click();
        await page.waitForTimeout(2000);

        // 验证是否跳转到搜索页
        await page.screenshot({ path: 'test-results/homepage-search.png', fullPage: true });
        console.log('✅ 搜索功能可触发');
      }
    } else {
      console.log('⚠️ 未找到搜索框');
    }
  });

  test('7. 导航菜单', async ({ page }) => {
    // 登录
    await page.goto(BASE_URL);
    await page.locator('input[placeholder*="用户名"]').fill('admin');
    await page.locator('input[placeholder*="密码"]').fill('admin123');
    await page.locator('button:has-text("登录")').click();
    await page.waitForURL(/.*\/|.*home/, { timeout: 10000 });
    await page.waitForTimeout(2000);

    // 检查导航菜单项
    const menuItems = ['首页', '技术要素', '国家院校', '人才搜索', '我的收藏'];

    for (const item of menuItems) {
      const visible = await page.locator(`text=${item}`).isVisible().catch(() => false);
      console.log(`📌 导航项 "${item}": ${visible ? '✅ 可见' : '❌ 不可见'}`);
    }

    await page.screenshot({ path: 'test-results/homepage-navigation.png', fullPage: true });

    console.log('✅ 导航菜单检查完成');
  });

  test('8. 页面响应时间', async ({ page }) => {
    const startTime = Date.now();

    await page.goto(BASE_URL);
    await page.locator('input[placeholder*="用户名"]').fill('admin');
    await page.locator('input[placeholder*="密码"]').fill('admin123');
    await page.locator('button:has-text("登录")').click();
    await page.waitForURL(/.*\/|.*home/, { timeout: 10000 });

    // 等待页面稳定
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    console.log(`⏱️ 页面加载时间: ${loadTime}ms`);

    // 验证加载时间在合理范围内 (< 5秒)
    expect(loadTime).toBeLessThan(5000);

    console.log('✅ 页面响应时间正常');
  });
});
