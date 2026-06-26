# 投资组合回测分析工具

基于本地年度数据的资产组合回测与分析工具，提供图形化交互界面：自由选择资产组合、配置权重、选择回测区间与再平衡模式，查看组合净值曲线与风险指标。定位为「分析 / 回测」工具，非实盘交易系统。

## 环境准备

所有命令在 conda 环境 `invest` 中运行。首次需先创建该环境，再安装依赖；环境建好后请勿另建新环境或中途切换。

```bash
conda create -n invest python=3.13 -y                       # 首次创建环境
conda install -n invest streamlit plotly pandas pytest -y   # 安装依赖
```

## 启动应用

首选方式：用 `run_app.py` 启动，自动分配一个空闲端口，无需关心端口占用。

```bash
conda run -n invest python run_app.py
```

`run_app.py` 先由操作系统分配一个空闲端口，再传给 `streamlit run app.py`，并原样透传额外参数（如 `--server.headless true`）。启动后浏览器访问终端打印的实际地址。

也可直接用 Streamlit 启动（默认固定 http://localhost:8501，端口被占用时会直接报错退出）：

```bash
conda run -n invest streamlit run app.py
```

在左侧边栏选择资产、配置权重（合计需为 100%）、选择再平衡模式，主区域选择回测区间；参数变化即自动刷新组合净值曲线与指标。

## 运行测试

```bash
conda run -n invest pytest
```

## 打包成 Windows 桌面程序并分发

面向「把工具发给没有 Python 环境的同事」的场景，可用 [`streamlit-desktop-app`](https://github.com/ohtaman/streamlit-desktop-app) 把应用打包：它底层是 PyInstaller，外加一个 pywebview 原生窗口——双击启动、关窗口即自动结束后台进程，无浏览器标签、无残留控制台。

采用 **onedir（目录）模式**：产物是一个文件夹 `dist/InvestBacktest/`，内含 `InvestBacktest.exe` 与 `_internal/`（Python 运行时、DLL、数据）。相比单文件 onefile，**没有每次启动解压到临时目录的开销，启动快很多**；代价是产物为文件夹而非单文件——分发时打包成 zip 即可。

### 构建

首次需安装打包依赖（仅构建机需要，使用者不需要）：

```bash
conda run -n invest python -m pip install streamlit-desktop-app
```

在仓库根目录运行构建脚本：

```bash
conda run -n invest python build_exe.py
```

产物为 `dist/InvestBacktest/` 文件夹。脚本已固定好关键参数：把 `src/` 加入导入路径、整包收集 `invest_analysis` 与 `plotly`、并将 `data/processed` 打进产物（运行时由 `data_loader.py` 经 `sys._MEIPASS` 定位，onedir 下指向 `_internal/`）。

说明：

- **体积约数百 MB**（带着 pandas / plotly / streamlit）；onedir 启动**无解压、几乎瞬时**。
- **数据已内嵌**：所有年度 CSV 打进 `_internal/data/processed/`，使用者无需附带 `data/` 目录。
- **整个文件夹是一个整体**：`InvestBacktest.exe` 必须和同级的 `_internal/` 待在一起，不能只拷 exe。
- `build/`、`dist/`、`*.spec` 均已在 `.gitignore` 中，**不提交进仓库**。

### 首次运行的 SmartScreen 提示

未做代码签名的 exe，Windows 会弹「Windows 已保护你的电脑 / 未知发布者」。点 **更多信息 → 仍要运行** 即可。彻底消除需购买代码签名证书，小范围内部分发一般不必。

### 分发：打包成 zip，经 GitHub Releases 发布

构建产物不该进 git（撑大历史）。先把整个文件夹压成 zip，再作为 **Release 附件**上传（单附件上限 2GB）：

```bash
# 1) 把 dist/InvestBacktest/ 整个文件夹压成 zip（PowerShell）：
powershell -Command "Compress-Archive -Path dist/InvestBacktest/* -DestinationPath dist/InvestBacktest-v1.0.0-win64.zip -Force"

# 2) gh 首次需登录一次（交互式，浏览器授权）：
conda run -n invest gh auth login

# 3) 打 tag 并发布，上传 zip：
conda run -n invest gh release create v1.0.0 dist/InvestBacktest-v1.0.0-win64.zip \
  --title "投资组合回测 v1.0.0" --notes "Windows 版，解压后双击 InvestBacktest.exe 运行，无需 Python。"
```

使用者从仓库 **Releases 页面**下载 zip，**解压到任意目录后双击 `InvestBacktest.exe`** 即可（注意保持 `exe` 与 `_internal/` 在一起）。

## 当前支持的资产

| 资产 | 数据列 | 起始年份 |
|---|---|---|
| 黄金 | `price_usd_per_troy_oz` | 1926 |
| 标普 500 | `index_level` | 1926 |
| 纳斯达克 100 | `index_level` | 1985 |
| 上证指数 | `index_level` | 1990 |
| 沪深 300 | `index_level` | 2005 |
| 美国 10 年期国债总回报指数 | `index_level` | 1928 |
| 中国国债指数 | `index_level` | 2003 |

多资产组合自动按**共同年份取交集**对齐（inner join），净值统一归一化为起点 = 1。

## V1 已知限制

- **数据频率为年度**：当前所有数据为年度数据。回测全链路基于年度数据构建。
- **月度 / 季度再平衡为接口级近似**：在年度数据下，月度与季度再平衡都退化为「每个年度节点调回目标权重」，二者结果相同。待引入更高频数据后才精确生效（届时仅替换加载层与再平衡频率处理，计算接口不变）。
- **美国国债使用 10 年期国债总回报累计指数**（Damodaran 数据），而非收益率，作为资产表现曲线。
- **未处理汇率**：数值为原始指数点位 / 价格 / 总回报指数，跨币种资产未做汇率换算。
- **暂不含**：定投模拟、XIRR / TWR、多策略对比、登录鉴权、实时行情。

## 架构

算法层与 UI 层硬隔离：

- `src/invest_analysis/` — 纯计算层，**不依赖 streamlit**。
  - `assets.py` — 资产元数据目录（路径、展示名、数值列）。
  - `data_loader.py` — 加载、按年份对齐、区间切片、归一化。
  - `portfolio.py` — 权重校验与组合回测（买入持有 / 月度 / 季度再平衡）。
  - `metrics.py` — 累计收益、年化收益、年化波动率、最大回撤、夏普比率。
- `app.py` — Streamlit 交互界面，仅采集参数 → 调用算法层 → 绘图。
- `tests/` — 覆盖三层核心计算的自动化测试。

## 已验证组合（V1 端到端）

下列组合均已验证可跑通（自动取共同年份、净值从 1 开始、指标非空、最大回撤 ≤ 0），结果为买入持有口径：

| 组合 | 年份 | 年化收益 | 最大回撤 |
|---|---|---|---|
| 25% 纳斯达克100 + 75% 美国10年期国债总回报指数 | 1985–2025 | 10.48% | -44.99% |
| 50% 沪深300 + 50% 中国国债指数 | 2005–2025 | 6.52% | -54.68% |
| 40% 黄金 + 60% 标普500 | 1926–2025 | 6.13% | -55.41% |
