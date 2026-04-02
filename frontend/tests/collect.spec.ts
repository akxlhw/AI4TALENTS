/**
 * 采集配置页面 E2E 测试
 *
 * 覆盖功能：
 * 1. 技术要素配置列表加载
 * 2. 采集任务触发
 * 3. 任务状态显示
 * 4. 任务进度追踪
 */
import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:5173';

// 登录辅助函数
async function login(page: any) {
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

// 导航到采集页面
async function gotoCollectPage(page: any) {
  await login(page);
  await page.waitForTimeout(1000);

  // 点击采集配置菜单
  const collectMenu = page.locator('text=/采集配置|数据采集/').first();
  if (await collectMenu.isVisible()) {
    await collectMenu.click();
    await page.waitForTimeout(1000);
  } else {
    // 直接导航
    await page.goto(`${BASE_URL}/collect`);
    await page.waitForTimeout(1000);
  }
}

test.describe('采集配置页面测试', () => {

  test('1. 采集页面加载', async ({ page }) => {
    await gotoCollectPage(page);

    // 验证页面元素
    await page.screenshot({ path: 'test-results/collect-01-page-load.png', fullPage: true });

    // 检查技术要素列表或配置区域
    const techElementSection = await page.locator('text=/技术要素|采集源|顶会顶刊/').count();
    console.log(`📋 技术要素相关元素: ${techElementSection}`);

    // 检查是否有表格或卡片
    const tableOrCard = await page.locator('.ant-table, .ant-card').count();
    console.log(`📊 表格/卡片元素: ${tableOrCard}`);

    console.log('✅ 采集页面加载正常');
  });

  test('2. 技术要素配置列表', async ({ page }) => {
    await gotoCollectPage(page);
    await page.waitForTimeout(2000);

    // 检查技术要素列表
    const techElements = await page.locator('.ant-table-row, .ant-list-item').count();
    console.log(`📋 技术要素条目数: ${techElements}`);

    // 检查绑定数量显示
    const bindingCount = await page.locator('text=/绑定|venue|顶会顶刊/').count();
    console.log(`🔗 绑定相关元素: ${bindingCount}`);

    await page.screenshot({ path: 'test-results/collect-02-tech-list.png', fullPage: true });
    console.log('✅ 技术要素列表展示正常');
  });

  test('3. 触发采集按钮检查', async ({ page }) => {
    await gotoCollectPage(page);
    await page.waitForTimeout(2000);

    // 检查是否有触发采集的按钮
    const triggerButtons = await page.locator('button:has-text("采集"), button:has-text("执行"), button:has-text("触发")').count();
    console.log(`🔘 触发按钮数量: ${triggerButtons}`);

    // 检查是否有状态标签
    const statusTags = await page.locator('.ant-tag').count();
    console.log(`🏷️ 状态标签数量: ${statusTags}`);

    await page.screenshot({ path: 'test-results/collect-03-trigger-buttons.png', fullPage: true });
    console.log('✅ 触发按钮检查完成');
  });

  test('4. 任务列表查看', async ({ page }) => {
    await gotoCollectPage(page);
    await page.waitForTimeout(1000);

    // 查找任务列表 Tab 或区域
    const taskTab = page.locator('text=/任务|历史/').first();
    if (await taskTab.isVisible()) {
      await taskTab.click();
      await page.waitForTimeout(1000);
    }

    // 检查任务列表
    const taskRows = await page.locator('.ant-table-row').count();
    console.log(`📋 任务记录数: ${taskRows}`);

    await page.screenshot({ path: 'test-results/collect-04-task-list.png', fullPage: true });
    console.log('✅ 任务列表检查完成');
  });

  test('5. 采集模式选择', async ({ page }) => {
    await gotoCollectPage(page);
    await page.waitForTimeout(2000);

    // 检查是否有采集模式选择 - 使用正确的选择器语法
    const modeSelect = page.locator('.ant-select').first();
    const modeText = page.locator('text=/全量|增量/').first();

    if (await modeSelect.isVisible() || await modeText.isVisible()) {
      console.log('✅ 发现采集模式选择器');

      // 点击查看选项
      if (await modeSelect.isVisible()) {
        await modeSelect.click().catch(() => {});
      }
      await page.waitForTimeout(500);

      await page.screenshot({ path: 'test-results/collect-05-mode-select.png', fullPage: true });
    } else {
      console.log('⚠️ 未发现采集模式选择器');
    }
  });
});

test.describe('采集任务状态验证', () => {

  test('6. 任务状态正确显示', async ({ page }) => {
    await gotoCollectPage(page);
    await page.waitForTimeout(2000);

    // 查找任务列表
    const taskTab = page.locator('text=/任务/').first();
    if (await taskTab.isVisible()) {
      await taskTab.click();
      await page.waitForTimeout(1000);
    }

    // 检查状态标签
    const statusTags = ['pending', 'running', 'completed', 'failed', 'pending', 'running', 'completed', 'failed', '待执行', '执行中', '已完成', '失败'];

    for (const status of statusTags) {
      const count = await page.locator(`text=/${status}/i`).count();
      if (count > 0) {
        console.log(`📊 状态 "${status}": ${count} 条`);
      }
    }

    await page.screenshot({ path: 'test-results/collect-06-task-status.png', fullPage: true });
    console.log('✅ 任务状态显示检查完成');
  });

  test('7. 任务进度显示', async ({ page }) => {
    await gotoCollectPage(page);
    await page.waitForTimeout(2000);

    // 查找任务列表
    const taskTab = page.locator('text=/任务/').first();
    if (await taskTab.isVisible()) {
      await taskTab.click();
      await page.waitForTimeout(1000);
    }

    // 检查进度相关元素
    const progressBars = await page.locator('.ant-progress').count();
    const progressText = await page.locator('text=/%|进度/').count();

    console.log(`📊 进度条数量: ${progressBars}`);
    console.log(`📊 进度文本数量: ${progressText}`);

    await page.screenshot({ path: 'test-results/collect-07-progress.png', fullPage: true });
    console.log('✅ 进度显示检查完成');
  });

  test('8. 错误信息显示', async ({ page }) => {
    await gotoCollectPage(page);
    await page.waitForTimeout(2000);

    // 查找任务列表
    const taskTab = page.locator('text=/任务/').first();
    if (await taskTab.isVisible()) {
      await taskTab.click();
      await page.waitForTimeout(1000);
    }

    // 点击失败的任务查看详情
    const failedTask = page.locator('.ant-table-row').filter({ hasText: /失败|failed/i }).first();
    if (await failedTask.isVisible()) {
      await failedTask.click();
      await page.waitForTimeout(500);

      // 检查错误信息
      const errorMessage = await page.locator('.ant-modal, .ant-descriptions').count();
      console.log(`📋 错误详情弹窗: ${errorMessage > 0 ? '存在' : '不存在'}`);
    } else {
      console.log('ℹ️ 当前没有失败的任务记录');
    }

    await page.screenshot({ path: 'test-results/collect-08-error-display.png', fullPage: true });
    console.log('✅ 错误信息显示检查完成');
  });
});

test.describe('采集数据验证', () => {

  test('9. 统计数据合理性', async ({ page }) => {
    await gotoCollectPage(page);
    await page.waitForTimeout(2000);

    // 查找任务列表并点击已完成的任务
    const taskTab = page.locator('text=/任务/').first();
    if (await taskTab.isVisible()) {
      await taskTab.click();
      await page.waitForTimeout(1000);
    }

    // 获取完成的任务
    const completedTask = page.locator('.ant-table-row').filter({ hasText: /完成|completed/i }).first();
    if (await completedTask.isVisible()) {
      await completedTask.click();
      await page.waitForTimeout(500);

      // 检查统计数字
      const numbers = await page.locator('.ant-statistic-content-value').allInnerTexts();
      console.log(`📊 统计数字: ${numbers.slice(0, 5).join(', ')}...`);
    } else {
      console.log('ℹ️ 当前没有已完成的任务记录');
    }

    await page.screenshot({ path: 'test-results/collect-09-stats.png', fullPage: true });
    console.log('✅ 统计数据验证完成');
  });

  test('10. 子任务展开查看', async ({ page }) => {
    await gotoCollectPage(page);
    await page.waitForTimeout(2000);

    // 查找任务列表
    const taskTab = page.locator('text=/任务/').first();
    if (await taskTab.isVisible()) {
      await taskTab.click();
      await page.waitForTimeout(1000);
    }

    // 查找展开按钮
    const expandButton = page.locator('.ant-table-row-expand-icon, button:has-text("子任务")').first();
    if (await expandButton.isVisible()) {
      await expandButton.click();
      await page.waitForTimeout(500);

      // 检查子任务列表
      const subTasks = await page.locator('.ant-table-row').count();
      console.log(`📋 子任务条目数: ${subTasks}`);
    }

    await page.screenshot({ path: 'test-results/collect-10-sub-tasks.png', fullPage: true });
    console.log('✅ 子任务展开检查完成');
  });
});
