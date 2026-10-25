# REA 研究记录

## 1. 选题

本次选择 Lovable，原因是它把“描述想法”与“得到可运行软件”连接起来，产品闭环容易通过一个轻量 DEMO 表达，也能清楚展示 AI 产品的核心交互设计。

官方融资公告：<https://lovable.dev/blog/series-c>

官方产品入口：<https://lovable.dev/>

截至 2026-10-25，官方公告显示：Lovable 于 2026-08-12 宣布完成 4 亿美元 Series C，投后估值 133 亿美元。公告同时描述了自然语言创建软件、项目持续迭代、发布、集成和安全治理等产品方向。

## 2. 产品逆向观察

从公开产品页面和公告中，提取出下面的可观察行为：

| 观察到的能力 | DEMO 中的对应设计 | 实现方式 |
| --- | --- | --- |
| 用自然语言描述想法 | 中央 Prompt 输入框 | `textarea#prompt` 接收输入 |
| 快速开始常见类型 | Landing page / Dashboard / Mobile app | 点击 chip 自动填入示例提示词 |
| 生成过程给出即时反馈 | Build 按钮和状态条 | `app.js` 用前端状态模拟生成反馈 |
| 多项目持续管理 | Recent projects 卡片 | 静态数据呈现项目缩略图、名称和编辑时间 |
| 工作区上下文 | Founder Lab 侧栏 | 纯 CSS 和 HTML 绘制导航结构 |

## 3. DEMO 范围

`index.html`、`styles.css` 和 `app.js` 共同实现一个无需后端的可运行原型。用户可以：

1. 输入产品想法并点击 Build；
2. 点击三个快捷场景填入提示词；
3. 看到生成状态从准备中切换到完成；
4. 浏览最近项目卡片和工作区导航。

该实现聚焦公开可观察的交互流程，使用原创名称 `Forgeflow`、原创视觉样式和原创代码。它不复制 Lovable 的源代码、商标素材或私有接口，也不声称真的生成应用代码。

## 4. 本地演示

```powershell
cd rea-lovable-demo
python -m http.server 5173
```

浏览器打开 <http://localhost:5173>，在输入框写入：

```text
Build a landing page for a sustainable coffee subscription
```

点击 `Build` 即可看到交互反馈。

## 5. 验证记录

- `git diff --check`：通过
- `node --check app.js`：通过
- 本地 HTTP 服务：`index.html`、`app.js`、`styles.css` 均返回 HTTP 200
- GitHub 提交：见仓库提交记录 `d0173c0`
