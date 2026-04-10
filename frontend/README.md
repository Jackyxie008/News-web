# 新闻世界地图可视化（Vue 3 + Leaflet + Tailwind）

三栏主页布局：左侧新闻列表（可滚动）联动中间世界地图 Marker/Popup；右侧展示分类饼图与趋势折线图。

## 本地运行

1. 安装依赖

```bash
npm install
```

2. 启动开发环境

```bash
npm run dev
```

浏览器打开 `http://localhost:5173/`。

## 代码规范

- ESLint（零警告）

```bash
npm run lint
```

- Prettier（零告警）

```bash
npm run format:check
```

- TypeScript 类型检查

```bash
npm run check
```

## 说明

- 地图底图使用 Google Maps 瓦片 URL（Leaflet TileLayer）。该方式不包含 API Key，但是否符合你的使用场景与许可条款需你自行确认。
- 当前数据为前端 mock（`src/lib/news.ts`），用于演示筛选、联动与图表统计；后续可替换为真实新闻 API。
