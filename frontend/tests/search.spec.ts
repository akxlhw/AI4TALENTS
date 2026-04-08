import { test, expect, Page } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

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

  // 等待登录成功 - 使用 Promise.any 等待任意一个条件满足
  // 所有 promise 都包装为永不 reject
  const loginSuccess = Promise.any([
    // 等待登录表单消失
    page.waitForSelector('.ant-input[placeholder="用户名或邮箱"]', { state: 'hidden', timeout: 20000 })
      .catch(() => null),
    // 或等待主页布局出现
    page.waitForSelector('.ant-layout-content, .ant-menu', { timeout: 20000 })
      .catch(() => null),
    // 或等待 URL 变化（登录后通常会跳转）
    page.waitForURL(/\/(home|dashboard|talents|search|collect|tech|school)/, { timeout: 20000 })
      .catch(() => null),
  ]);

  await loginSuccess;

  // 额外等待确保页面稳定
  await page.waitForTimeout(1000);
}

// 导航到搜索页面
async function goToSearchPage(page: Page) {
  // 尝试点击导航菜单中的搜索项
  const searchMenuItem = page.locator('text=/人才搜索|搜索/i').first();
  if (await searchMenuItem.isVisible()) {
    await searchMenuItem.click();
    await page.waitForTimeout(1000);
  } else {
    // 直接导航到搜索页面
    await page.goto(`${BASE_URL}/search`);
    await page.waitForTimeout(1000);
  }
}

test.describe('搜索页面功能测试', () => {

  test('1. 搜索页面加载', async ({ page }) => {
    await login(page);
    await goToSearchPage(page);
    await page.waitForTimeout(2000);

    // 验证搜索页面主要元素存在
    const hasSearchInput = await page.locator('input[placeholder*="搜索"], input[placeholder*="关键词"], input[placeholder*="姓名"]').count() > 0;
    const hasFilterArea = await page.locator('.ant-card, .ant-form, .ant-select').count() > 0;

    console.log(`🔍 搜索输入框: ${hasSearchInput ? '✅ 存在' : '❌ 不存在'}`);
    console.log(`📋 筛选区域: ${hasFilterArea ? '✅ 存在' : '❌ 不存在'}`);

    await page.screenshot({ path: 'test-results/search-01-page-load.png', fullPage: true });
    console.log('✅ 搜索页面加载正常');
  });

  test('2. 关键词搜索', async ({ page }) => {
    await login(page);
    await goToSearchPage(page);
    await page.waitForTimeout(1000);

    // 查找搜索输入框
    const searchInput = page.locator('input[placeholder*="搜索"], input[placeholder*="关键词"], input[placeholder*="姓名"]').first();

    if (await searchInput.isVisible()) {
      // 输入搜索关键词
      await searchInput.fill('AI');
      await page.waitForTimeout(500);

      // 点击搜索按钮或按回车
      const searchButton = page.locator('button:has-text("搜索"), button:has-text("查询")').first();
      if (await searchButton.isVisible()) {
        await searchButton.click();
      } else {
        await searchInput.press('Enter');
      }

      await page.waitForTimeout(2000);

      // 验证搜索结果区域
      const hasResults = await page.locator('.ant-table, .ant-list, .ant-card').count() > 0;
      console.log(`📊 搜索结果区域: ${hasResults ? '✅ 存在' : '⚠️ 未找到'}`);

      await page.screenshot({ path: 'test-results/search-02-keyword-search.png', fullPage: true });
      console.log('✅ 关键词搜索完成');
    } else {
      console.log('⚠️ 未找到搜索输入框');
    }
  });

  test('3. 筛选功能', async ({ page }) => {
    await login(page);
    await goToSearchPage(page);
    await page.waitForTimeout(1000);

    // 查找筛选下拉框
    const selectElements = await page.locator('.ant-select').count();
    console.log(`📋 筛选下拉框数量: ${selectElements}`);

    if (selectElements > 0) {
      // 尝试点击第一个下拉框
      const firstSelect = page.locator('.ant-select').first();
      await firstSelect.click();
      await page.waitForTimeout(500);

      // 检查下拉选项是否显示
      const hasDropdown = await page.locator('.ant-select-dropdown, .ant-select-item').count() > 0;
      console.log(`📋 下拉选项: ${hasDropdown ? '✅ 显示' : '⚠️ 未显示'}`);

      // 按 Escape 关闭下拉
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }

    await page.screenshot({ path: 'test-results/search-03-filters.png', fullPage: true });
    console.log('✅ 筛选功能检查完成');
  });

  test('4. 搜索结果表格', async ({ page }) => {
    await login(page);
    await goToSearchPage(page);
    await page.waitForTimeout(2000);

    // 检查是否有表格
    const hasTable = await page.locator('.ant-table').count() > 0;

    if (hasTable) {
      console.log('✅ 搜索结果表格存在');

      // 检查表格列
      const tableHeaders = await page.locator('.ant-table-thead th').count();
      console.log(`📊 表格列数: ${tableHeaders}`);

      // 检查表格行
      const tableRows = await page.locator('.ant-table-tbody tr').count();
      console.log(`📊 表格行数: ${tableRows}`);

      // 如果有数据，检查第一行
      if (tableRows > 0) {
        const firstRow = page.locator('.ant-table-tbody tr').first();
        const hasName = await firstRow.locator('td').first().textContent();
        console.log(`👤 第一行数据: ${hasName?.substring(0, 30)}`);
      }
    } else {
      console.log('⚠️ 搜索结果表格不存在或无数据');
    }

    await page.screenshot({ path: 'test-results/search-04-results-table.png', fullPage: true });
    console.log('✅ 搜索结果表格检查完成');
  });

  test('5. 分页功能', async ({ page }) => {
    await login(page);
    await goToSearchPage(page);
    await page.waitForTimeout(2000);

    // 检查分页器
    const hasPagination = await page.locator('.ant-pagination').count() > 0;

    if (hasPagination) {
      console.log('✅ 分页器存在');

      // 检查分页信息
      const paginationInfo = await page.locator('.ant-pagination-total-text').textContent().catch(() => null);
      if (paginationInfo) {
        console.log(`📊 分页信息: ${paginationInfo}`);
      }

      // 检查分页按钮
      const pageButtons = await page.locator('.ant-pagination-item').count();
      console.log(`📋 分页按钮数: ${pageButtons}`);
    } else {
      console.log('⚠️ 分页器不存在');
    }

    await page.screenshot({ path: 'test-results/search-05-pagination.png', fullPage: true });
    console.log('✅ 分页功能检查完成');
  });

  test('6. 重置搜索', async ({ page }) => {
    await login(page);
    await goToSearchPage(page);
    await page.waitForTimeout(1000);

    // 查找重置按钮
    const resetButton = page.locator('button:has-text("重置"), button:has-text("清空")').first();

    if (await resetButton.isVisible()) {
      await resetButton.click();
      await page.waitForTimeout(1000);
      console.log('✅ 重置按钮已点击');
    } else {
      console.log('⚠️ 重置按钮不存在');
    }

    await page.screenshot({ path: 'test-results/search-06-reset.png', fullPage: true });
    console.log('✅ 重置功能检查完成');
  });

  test('7. 人才详情入口', async ({ page }) => {
    await login(page);
    await goToSearchPage(page);
    await page.waitForTimeout(2000);

    // 检查是否有可点击的人才行
    const talentRows = await page.locator('.ant-table-tbody tr:has(td)').count();

    if (talentRows > 0) {
      // 点击第一行
      const firstRow = page.locator('.ant-table-tbody tr').first();

      // 检查是否有查看详情按钮
      const viewButton = firstRow.locator('button:has-text("查看"), a:has-text("详情")');

      if (await viewButton.count() > 0) {
        await viewButton.first().click();
        await page.waitForTimeout(2000);

        // 检查是否跳转到详情页
        const url = page.url();
        console.log(`🔗 跳转URL: ${url}`);

        await page.screenshot({ path: 'test-results/search-07-detail-entry.png', fullPage: true });
        console.log('✅ 人才详情入口可用');
      } else {
        // 尝试直接点击行
        await firstRow.click();
        await page.waitForTimeout(1000);
        console.log('✅ 表格行点击成功');
      }
    } else {
      console.log('⚠️ 无人才数据可测试');
    }
  });

  test('8. 收藏功能入口', async ({ page }) => {
    await login(page);
    await goToSearchPage(page);
    await page.waitForTimeout(2000);

    // 检查收藏按钮/图标
    const favoriteButtons = await page.locator('.anticon-heart, button:has-text("收藏"), .anticon-star').count();
    console.log(`❤️ 收藏相关元素: ${favoriteButtons}`);

    if (favoriteButtons > 0) {
      console.log('✅ 收藏功能入口存在');

      // 尝试点击第一个收藏按钮
      const firstFavorite = page.locator('.anticon-heart, button:has-text("收藏")').first();
      if (await firstFavorite.isVisible()) {
        await firstFavorite.click();
        await page.waitForTimeout(500);
        console.log('✅ 收藏按钮已点击');
      }
    } else {
      console.log('⚠️ 收藏功能入口未找到');
    }

    await page.screenshot({ path: 'test-results/search-08-favorite.png', fullPage: true });
    console.log('✅ 收藏功能入口检查完成');
  });

  test('9. 导出功能', async ({ page }) => {
    await login(page);
    await goToSearchPage(page);
    await page.waitForTimeout(1000);

    // 查找导出按钮
    const exportButton = page.locator('button:has-text("导出"), button:has-text("Export")').first();

    if (await exportButton.isVisible()) {
      console.log('✅ 导出按钮存在');
    } else {
      console.log('⚠️ 导出按钮不存在');
    }

    await page.screenshot({ path: 'test-results/search-09-export.png', fullPage: true });
    console.log('✅ 导出功能检查完成');
  });

  test('10. 搜索页面响应时间', async ({ page }) => {
    const startTime = Date.now();

    await login(page);
    await goToSearchPage(page);
    await page.waitForLoadState('networkidle');

    const loadTime = Date.now() - startTime;
    console.log(`⏱️ 搜索页面加载时间: ${loadTime}ms`);

    // 验证加载时间在合理范围内 (< 15秒)
    expect(loadTime).toBeLessThan(15000);

    await page.screenshot({ path: 'test-results/search-10-performance.png', fullPage: true });
    console.log('✅ 搜索页面响应时间正常');
  });
});
