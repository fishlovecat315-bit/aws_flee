# 需求文档：Nothing AWS 费用统计平台

## 产品概述

Nothing AWS 费用统计平台（以下简称"费用平台"）是一个面向 Nothing 公司内部的 Web 系统，用于统计和展示公司在 AWS 上各业务部门的费用情况及整体费用增长趋势。系统通过 AWS Cost Explorer API 每日同步费用数据，按照预定义的 Tag 归属规则和分摊规则，将费用分配到各业务部门，并提供多维度的可视化展示、费用预警和报表导出功能。

---

## 词汇表

- **费用平台**：本系统，即 Nothing AWS 费用统计平台
- **业务部门**：Nothing 公司内部的六个业务单元：销售、AI、Smart、Phone、IT、Community
- **业务模块**：AWS 资源上打的 Tag 所对应的具体业务，如 Nothing-x、TTS、DataCollection 等
- **子账号**：Nothing 公司在 AWS 下的三个账号：PLM 账号、主业务账号、国内账号
- **Tag**：AWS 资源上的标签，用于标识资源所属业务模块
- **分摊规则**：将共用资源费用按比例分配给多个业务部门的计算规则
- **Public 资源**：账号中无明确业务归属的资源，需按规则分摊
- **Cost Explorer API**：AWS 提供的费用查询 API，数据存在约 24 小时延迟
- **管理员**：负责维护分摊规则的内部用户
- **普通用户**：查看费用数据的内部用户

---

## 用户故事

### 普通用户

- 作为普通用户，我希望查看各业务部门的 AWS 费用，以便了解各部门的云资源消耗情况。
- 作为普通用户，我希望按日粒度和月粒度查看费用数据，以便进行短期和长期的费用分析。
- 作为普通用户，我希望自定义查询时间范围，以便灵活分析特定时段的费用。
- 作为普通用户，我希望通过折线图、柱状图、饼图等多种图表查看费用趋势和占比，以便直观理解费用结构。
- 作为普通用户，我希望导出费用报表为 Excel、CSV 或 PDF 格式，以便在系统外进行进一步分析或汇报。

### 管理员

- 作为管理员，我希望通过独立界面维护 Tag 与业务部门的归属规则，以便在业务调整时及时更新费用分配逻辑。
- 作为管理员，我希望设置各业务部门的费用预警阈值，以便在费用异常时及时收到通知。

---

## 功能需求

### 需求 1：AWS 费用数据同步

**用户故事：** 作为普通用户，我希望系统每天自动同步最新的 AWS 费用数据，以便查看到最新的费用情况。

#### 验收标准

1. THE 费用平台 SHALL 每天执行一次 AWS Cost Explorer API 数据同步任务。
2. WHEN 数据同步任务执行时，THE 费用平台 SHALL 从三个子账号（PLM 账号、主业务账号、国内账号）分别拉取费用数据。
3. THE 费用平台 SHALL 永久保留所有历史费用数据，不设数据过期策略。
4. WHEN AWS Cost Explorer API 返回数据时，THE 费用平台 SHALL 接受最长 24 小时的数据延迟。
5. IF 数据同步任务失败，THEN THE 费用平台 SHALL 记录错误日志并在下次同步时重试。
6. WHEN 数据同步完成时，THE 费用平台 SHALL 按照 Tag 归属规则和分摊规则自动计算各业务部门的费用。

---

### 需求 2：费用展示与查询

**用户故事：** 作为普通用户，我希望以多种维度查看 AWS 费用数据，以便全面了解费用分布。

#### 验收标准

1. THE 费用平台 SHALL 支持以日为最小粒度展示费用数据。
2. THE 费用平台 SHALL 提供月度汇总视图，将日粒度数据聚合为月度费用。
3. THE 费用平台 SHALL 支持用户自定义查询时间范围。
4. THE 费用平台 SHALL 支持按业务部门维度展示费用（销售、AI、Smart、Phone、IT、Community）。
5. THE 费用平台 SHALL 支持按 AWS 子账号维度展示费用（PLM 账号、主业务账号、国内账号）。
6. THE 费用平台 SHALL 支持按业务模块（Tag）维度展示费用。
7. WHEN 用户查询费用数据时，THE 费用平台 SHALL 在合理时间内返回查询结果。

---

### 需求 3：图表可视化

**用户故事：** 作为普通用户，我希望通过多种图表类型直观查看费用数据，以便快速理解费用趋势和结构。

#### 验收标准

1. THE 费用平台 SHALL 支持折线图展示费用随时间的变化趋势。
2. THE 费用平台 SHALL 支持柱状图展示不同维度之间的费用对比。
3. THE 费用平台 SHALL 支持饼图展示各业务部门或业务模块的费用占比。
4. WHEN 用户选择图表类型时，THE 费用平台 SHALL 在不刷新页面的情况下切换图表展示形式。

---

### 需求 4：费用分摊计算

**用户故事：** 作为普通用户，我希望系统自动按预定义规则计算各业务部门的分摊费用，以便准确了解各部门实际承担的云资源成本。

#### 验收标准

1. THE 费用平台 SHALL 按照数据字典中定义的 Tag 归属规则，将各业务模块费用归属到对应业务部门。
2. THE 费用平台 SHALL 按照数据字典中定义的分摊规则，将共用资源费用按比例分配到各业务部门。
3. THE 费用平台 SHALL 按照 Public 资源处理规则，对无 Tag 或无明确归属的资源进行费用分配。
4. WHEN 分摊规则发生变更时，THE 费用平台 SHALL 支持对历史数据重新计算分摊结果。

---

### 需求 5：分摊规则管理

**用户故事：** 作为管理员，我希望通过独立界面维护分摊规则，以便在业务调整时灵活更新费用分配逻辑。

#### 验收标准

1. THE 费用平台 SHALL 提供独立的分摊规则管理界面。
2. WHEN 管理员修改分摊规则时，THE 费用平台 SHALL 保存新规则并在下次数据计算时生效。
3. THE 费用平台 SHALL 支持管理员查看当前所有 Tag 的业务归属配置。
4. THE 费用平台 SHALL 支持管理员修改共用资源的分摊比例。

---

### 需求 6：费用预警

**用户故事：** 作为管理员，我希望设置费用预警阈值并在超出时收到通知，以便及时发现和处理费用异常。

#### 验收标准

1. THE 费用平台 SHALL 支持管理员为各业务部门设置费用预警阈值。
2. WHEN 某业务部门的费用超过预设阈值时，THE 费用平台 SHALL 通过钉钉机器人发送预警通知。
3. THE 费用平台 SHALL 在预警通知中包含触发预警的业务部门名称、当前费用金额和阈值。

---

### 需求 7：报表导出

**用户故事：** 作为普通用户，我希望将费用数据导出为常用格式，以便在系统外进行进一步分析或汇报。

#### 验收标准

1. THE 费用平台 SHALL 支持将费用数据导出为 Excel（.xlsx）格式。
2. THE 费用平台 SHALL 支持将费用数据导出为 CSV 格式。
3. THE 费用平台 SHALL 支持将费用数据导出为 PDF 格式。
4. WHEN 用户触发导出操作时，THE 费用平台 SHALL 导出当前查询条件下的费用数据。

---

## 非功能需求

### 访问与权限

1. THE 费用平台 SHALL 部署在公司内网，不对外网开放。
2. THE 费用平台 SHALL 在当前阶段不要求用户登录认证。
3. THE 费用平台 SHALL 允许所有内部用户查看全部业务部门的费用数据，不设数据范围限制。
4. THE 费用平台 SHALL 支持不少于 100 个并发用户同时访问。

### 性能

1. THE 费用平台 SHALL 每天执行一次数据同步，同步时间窗口在业务低峰期执行。
2. WHEN 用户发起页面查询请求时，THE 费用平台 SHALL 在合理时间内完成响应。

### 安全

1. THE 费用平台 SHALL 通过配置文件或环境变量管理 AWS 账号访问凭证，不在代码中硬编码。

---

## 数据字典：Tag 与业务归属映射

### PLM 账号

| Tag | 业务模块名称 | 归属业务部门 |
|-----|------------|------------|
| OBA-app | OBA | IT |
| CommonRedshift | Redshift DWH | IT |
| ems-app-database | EMS 系统 Aurora | IT |
| IPGuard | IPGuard | IT |
| powerbi rds | PowerBI 门户 | IT |
| LogCollect | 日志服务 | Phone |
| DIS | 日志分析 | Phone |
| CIT | CIT | 销售 |
| Public（其余费用） | — | Phone : IT = 2 : 1 分摊 |

### 主业务账号 — 共用资源（按比例分摊）

| Tag | 业务模块名称 | 分摊规则 |
|-----|------------|--------|
| DataCollection | 埋点服务 | Phone : Smart : 销售 = 7 : 2 : 1 |
| BI | 看板 | Phone : Smart : 销售 = 4 : 3 : 3 |
| NAC | 账号中心 | Smart : Community : 销售 = 1 : 1 : 1 |
| NewsReporter | NewsReporter | Phone : Smart = 1 : 1 |
| Nacos | Nacos | AI : Phone : Smart = 2 : 3 : 1 |
| Feedback | Feedback | Phone : Smart = 1 : 1 |

### 主业务账号 — 明确归属资源

| Tag | 业务模块名称 | 归属业务部门 |
|-----|------------|------------|
| nothing x | Nothing-x | Smart |
| xservice | xservice | Smart |
| NothingOTA | NothingOTA | Smart |
| TTS | TTS | Smart |
| Mimi | Mimi | Smart |
| LinkJumping | 二维码服务 | Smart |
| Nothing Community | 社区 | Community |
| essential-space | essential-space | AI |
| Watch1 | cmf watch | Phone |
| NothingWeatherServer | 天气服务 | Phone |
| Wallpaper | AI Wallpaper | Phone |
| BetaOTA | BetaOTA | Phone |
| SharedWidget | SharedWidget | Phone |
| CommunityWidget | 社区微件 | Phone |
| PushService | PushService | Phone |
| APPClassification | 应用分类 | Phone |
| ShortLink | ShortLink | Phone |
| Nothing-Preorder | Nothing-Preorder | Phone |
| Questionnaire | 问卷 | Phone |
| BlindTest | Camera 盲测 | Phone |
| IMEI | IMEIServer | Phone |
| GenWidgets | 生成式 widgets | Phone |

### 主业务账号 — Public 资源处理规则

#### 无 Tag 资源

| 资源类型 | 处理规则 |
|--------|--------|
| MongoDB Atlas | 基础费用 $2500 由 Nothing-x 和 SharedWidget 按 1:1 平均分摊；超出 $2500 的部分全部归属 Nothing-x |
| Athena | 归属 BI 业务 |
| Elastic Load Balancing | 归属 Nothing-x 业务 |
| Redshift | 归属 DataCollection 业务 |

> 系统需在界面中罗列上述无 Tag 资源的详细费用明细。

#### 有 Tag 但无明确业务归属资源

| Tag 前缀 | 处理规则 |
|---------|--------|
| EKS 开头 | 由 nothing-x、SharedWidget、GenWidgets、essential-space 四个业务平均分摊（各 25%） |
| TTSProxy 开头 | 归属 TTS 业务 |

### 国内账号

| Tag | 业务模块名称 | 归属业务部门 |
|-----|------------|------------|
| NothingX | Nothing-x 中国区 | Smart |
| Mini | Mimi | Smart |
| DataCollection | 埋点服务 | Smart |
| OTA | Nothing-OTA | Smart |
| feedback | Feedback | Smart |
| NAC | 账号中心（中国区） | Smart |
| Common Cache | Common Cache | Smart |
| LogCollect | 日志服务 | Smart |
| Nacos | Nacos | Smart |
| 其余费用 | — | 其他 |

> 国内账号整体费用归属为 Smart 业务部门。

---

## 分摊规则说明

### 规则优先级

1. 明确 Tag 归属规则（最高优先级）：资源有 Tag 且 Tag 有明确业务归属，直接归属对应业务部门。
2. 共用资源分摊规则：资源有 Tag 且属于共用资源，按预定义比例分摊到多个业务部门。
3. Public 资源处理规则：资源无 Tag 或有 Tag 但无明确归属，按 Public 规则处理。

### 分摊计算方式

- 分摊在数据同步完成后自动计算，结果持久化存储。
- 分摊规则变更后，支持对历史数据重新触发计算。
- 分摊结果精确到小数点后两位（美元）。

### 规则维护

- 管理员可通过分摊规则管理界面修改各 Tag 的业务归属和分摊比例。
- 规则变更记录需保留，以便追溯历史计算依据。
