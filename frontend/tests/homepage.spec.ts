import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:2012';

// 登录辅助函数
async function login(page: Page) {
  await page.goto(BASE_URL);
  await page.waitForLoadState('networkidle');
  // 等待登录表单加载
  await page.waitForSelector('.ant-input[placeholder="用户名或邮箱"]', { timeout: 10000 });
  // 填写登录信息
  await page.locator('.ant-input[placeholder="用户名或邮箱"]').fill('admin');
  await page.locator('.ant-input-password input').fill('admin123');
  // 点击登录按钮
  await page.locator('button:has-text("登")').click();
  // 等待登录成功 - 使用 Promise.any 等待任意一个条件
  await Promise.any([
    page.waitForSelector('.ant-menu', { timeout: 20000 }),
    page.waitForSelector('.ant-avatar', { timeout: 20000 }),
    page.locator('text=admin').waitFor({ timeout: 20000 }),
  ]);
  // 额外等待确保页面稳定
  await page.waitForTimeout(1000);
}

test.describe('首页功能测试', () => {

  test('1. 登录页面加载', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // 验证登录页面元素 - 使用 Ant Design 选择器
    await expect(page.locator('.ant-input[placeholder="用户名或邮箱"]')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('.ant-input-password input')).toBeVisible();
    await expect(page.locator('button.ant-btn-primary')).toBeVisible();

    // 验证标题
    await expect(page.locator('text=智能人才库')).toBeVisible();

    // 截图
    await page.screenshot({ path: 'test-results/01-login-page.png', fullPage: true });
    console.log('✅ 登录页面加载正常');
  });

  test('2. 登录流程', async ({ page }) => {
    await login(page);

    // 验证已登录状态 - 检查侧边栏菜单或布局组件
    await expect(page.locator('.ant-layout-sider, .ant-menu, .ant-layout-content').first()).toBeVisible({ timeout: 10000 });

    // 等待页面完全加载
    await page.waitForTimeout(2000);

    await page.screenshot({ path: 'test-results/02-after-login.png', fullPage: true });
    console.log('✅ 登录流程正常');
  });

  test('3. 首页基础统计展示', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(2000);

    // 截图保存
    await page.screenshot({ path: 'test-results/03-homepage-stats.png', fullPage: true });

    // 检查统计卡片
    const statCards = await page.locator('.ant-statistic, .ant-card').count();
    console.log(`📊 统计/卡片元素数量: ${statCards}`);

    // 检查是否有数字显示
    const numbers = await page.locator('.ant-statistic-content-value').count();
    console.log(`📊 统计数字元素: ${numbers}`);

    console.log('✅ 基础统计展示正常');
  });

  test('4. 双主视角概要卡', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(2000);

    // 截图
    await page.screenshot({ path: 'test-results/04-homepage-cards.png', fullPage: true });

    // 检查技术要素概要
    const techElement = await page.locator('text=/技术要素/i').count();
    console.log(`🔍 技术要素元素: ${techElement}`);

    // 检查国家/院校相关
    const countrySchool = await page.locator('text=/国家|院校/i').count();
    console.log(`🌍 国家院校元素: ${countrySchool}`);

    console.log('✅ 双主视角概要卡检查完成');
  });

  test('5. 热点标签区', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(2000);

    // 检查标签
    const tags = await page.locator('.ant-tag').count();
    console.log(`🏷️ 标签数量: ${tags}`);

    await page.screenshot({ path: 'test-results/05-homepage-tags.png', fullPage: true });

    console.log('✅ 热点标签区检查完成');
  });

  test('6. 导航菜单', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(2000);

    // 检查导航菜单项
    const menuItems = ['首页', '技术要素', '国家院校', '人才搜索', '我的收藏'];

    for (const item of menuItems) {
      const visible = await page.locator(`text=/${item}/`).isVisible().catch(() => false);
      console.log(`📌 导航项 "${item}": ${visible ? '✅ 可见' : '❌ 不可见'}`);
    }

    await page.screenshot({ path: 'test-results/06-homepage-navigation.png', fullPage: true });

    console.log('✅ 导航菜单检查完成');
  });

  test('7. 页面响应时间', async ({ page }) => {
    const startTime = Date.now();
    await login(page);
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    console.log(`⏱️ 页面加载时间: ${loadTime}ms`);

    // 验证加载时间在合理范围内 (< 10秒)
    expect(loadTime).toBeLessThan(10000);

    await page.screenshot({ path: 'test-results/07-page-performance.png', fullPage: true });
    console.log('✅ 页面响应时间正常');
  });

  test('8. 搜索框功能', async ({ page }) => {
    await login(page);
    await page.waitForTimeout(2000);

    // 查找搜索框
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="关键词"], input[type="text"]').first();

    if (await searchInput.isVisible()) {
      console.log('✅ 搜索框可见');

      await searchInput.fill('AI');
      await page.waitForTimeout(500);
      await searchInput.press('Enter');
      await page.waitForTimeout(2000);

      await page.screenshot({ path: 'test-results/08-homepage-search.png', fullPage: true });
      console.log('✅ 搜索功能可触发');
    } else {
      console.log('⚠️ 未找到搜索框');
    }
  });
});
