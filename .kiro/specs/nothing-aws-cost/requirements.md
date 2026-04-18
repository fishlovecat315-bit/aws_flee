# 需求文档：Nothing AWS 费用统计平台

## 产品概述

Nothing AWS 费用统计平台是一个面向 Nothing 公司内部的 Web 系统，用于统计和展示公司在 AWS 上各业务部门的费用情况及整体费用增长趋势。系统通过 AWS Cost Explorer API 每日同步费用数据，按照 Product Tag 归属规则和分摊规则，将费用分配到各业务部门，并提供多维度的可视化展示、费用预警和报表导出功能。

---

## 词汇表

- **业务部门**：销售、AI、Smart、Phone、IT、Community
- **业务归属**：业务所属的大类分组：共用、SmartProduct、Community、AI、Phone、Public
- **业务模块**：具体的业务名称，如 Nothing-x、埋点服务、看板等
- **标签信息（Tag）**：AWS 资源上 `Product` 标签的值，格式为 `{appname}:{aws_service}:{region}`
- **appname**：Product Tag 中冒号前的第一段，标识业务归属
- **子账号**：PLM 账号、主业务账号、国内账号
- **分摊规则**：将共用/Public 资源费用按比例分配给多个业务部门的计算规则
- **Public 资源**：无 Product Tag 或有 Tag 但未匹配到已知业务的资源

---

## 核心规则：Tag 匹配机制

### Tag 来源
- AWS 资源上的 `Product` 标签（Tag Key = `Product`）
- Tag Value 格式：`{appname}:{aws_service}:{region}`，但格式不完全标准化

### 匹配规则
1. **包含匹配**：对 Tag Value 去掉所有非字母数字字符并转小写后，检查是否包含已知业务关键词
2. **不区分大小写**：`Nothing-X`、`nothing-X`、`nothing x` 均匹配到 `nothingx`（Nothing-x 业务）
3. **长词优先**：匹配时按关键词长度降序排列，避免短词误匹配（如 `nothingweatherserver` 优先于 `nothing`）
4. **无 Product Tag**：`Product$`（空值）统一归为 Public 分摊
5. **未匹配 Tag**：有 Product Tag 但不包含任何已知关键词的，归为「其他」

### 示例
| 原始 Tag Value | 标准化后 | 匹配关键词 | 归属业务 |
|---|---|---|---|
| `DataCollection:S3:eu-west-3` | `datacollections3euwest3` | `datacollection` | 埋点服务 |
| `BI20:RDS:ap-south-1` | `bi20rdsapsouth1` | `bi` | 看板 |
| `Nothing-X:EC2:PR` | `nothingxec2pr` | `nothingx` | Nothing-x |
| `AIWallpaper:EC2:TKY` | `aiwallpaperc2tky` | `wallpaper` | AI Wallpaper |
| `xservice:CF:Global` | `xservicecfglobal` | `xservice` | xservice |
| `（无 Product Tag）` | — | — | Public 分摊 |

---

## 数据同步

### AWS 凭证配置
- 三个子账号（PLM / 主业务 / 国内）各自独立，拥有独立的 Access Key、Secret Key、Region 和 Account ID
- 凭证通过前端「AWS 凭证」页面配置，保存到数据库，运行时动态加载，无需重启
- 未配置凭证的账号自动跳过同步

### 同步策略
- 每日自动同步昨天的数据（APScheduler 定时任务，每日 02:00）
- 启动时检查昨日是否有成功同步记录，无则自动补拉
- 支持前端「历史补拉」功能，选择日期范围手动触发
- 历史数据关注范围：过去 12 个月

### AWS Cost Explorer API 调用
- GroupBy：仅按 `TAG: Product` 分组（不同时按 SERVICE 分组，避免返回行数截断）
- Granularity：DAILY
- Metrics：BlendedCost
- 分段请求：每次最多查询 7 天（避免 API 返回行数限制导致数据截断）
- 批量写入：每批 1000 条（避免 asyncpg 参数上限）

---

## 费用展示

### 当月视图（日粒度）
- 默认展示当月 1 日至昨天的每日费用
- 支持日期范围选择器
- 支持按部门、账号筛选
- 展示：每日费用明细表、趋势图、汇总统计

### 历史月份视图（月粒度）
- 展示过去 12 个月的月度汇总
- 只看月度总费用和按业务模块汇总，不展示日粒度明细
- 支持按部门、账号筛选

### 费用明细页面（核心展示）
按截图格式展示，表格结构：

| 列名 | 说明 |
|---|---|
| 业务归属 | 共用 / SmartProduct / Community / AI / Phone（同组行合并） |
| 业务模块 | 业务中文名称（如「埋点服务」「Nothing-x」） |
| 标签信息 | AWS Product Tag 值（如 `DataCollection`），Public 行显示「Public分摊」 |
| 各月费用 | 可选近 3/4/6/12 个月 |
| 较上月增加 | 环比变化（红涨绿降） |

- 同一业务模块的多个部门分摊合并为一行，费用显示合计
- 鼠标悬停可查看各部门分摊占比

#### 附加入口按钮
费用明细表格上方提供两个独立入口按钮：

1. **「Public分摊(未分类)」按钮**
   - 位置：表格上方，蓝色边框按钮，显示最新月份 Public 费用总额
   - 展示所有无 Product Tag 的资源费用明细
   - 点击后弹出弹窗，按分摊部门（Phone/Smart/IT/Community/AI/销售）分行展示
   - 底部有合计行

2. **「已打Tag未确定归属」按钮**
   - 位置：表格上方，与 Public 按钮并排，显示条目数和费用总额
   - 展示所有有 Product Tag 但未匹配到已知业务（共用/SmartProduct/Community/AI/Phone）的资源
   - 点击后弹出弹窗，按原始 Tag Value 展示各项费用
   - 方便管理员识别新增业务或需要补充归属规则的资源
   - 包含之前在主表格中显示为「其他」的所有资源（如 iast、common、ekscluster 等）

注意：主表格中不展示「其他」分类，所有未确定归属的 Tag 资源统一归入「已打Tag未确定归属」按钮中查看。

---

## 分摊规则

### 主业务账号

#### SmartProduct（100% Smart）
| 业务模块 | Tag 关键词 | 说明 |
|---|---|---|
| Nothing-x | nothingx | 包括 Nothing-X、nothing-X、nothing x 等变体 |
| xservice | xservice | |
| NothingOTA | nothingota | |
| TTS | tts, ttsproxy | 语音转文字服务，Ear 使用 |
| Mimi | mimi | 耳机听力补偿算法 |
| 二维码服务 | linkjumping | 耳机包装盒二维码 |

#### 共用（按比例分摊）
| 业务模块 | Tag 关键词 | 分摊比例 | 说明 |
|---|---|---|---|
| 埋点服务 | datacollection | Phone:Smart:销售 = 70%:20%:10% | 按使用方和使用频次分摊 |
| 看板 | bi | Phone:Smart:销售 = 40%:30%:30% | 按使用频次分摊 |
| 账号中心 | nac | Smart:Community:销售 = 33%:33%:33% | Nothing-X、社区、官网三者均摊 |
| NewsReporter | newsreporter | Phone:Smart = 50%:50% | Smart 耳机和手表均支持 |
| Nacos | nacos | AI:Smart:Phone = 33.3%:50%:16.6% | 配置管理中心 |
| Feedback | feedback | Phone:Smart = 50%:50% | 用户反馈服务 |

#### Community（100% Community）
| 业务模块 | Tag 关键词 |
|---|---|
| 社区 | nothingcommunity |

#### AI（100% AI）
| 业务模块 | Tag 关键词 |
|---|---|
| essential-space | essentialspace |

#### Phone
| 业务模块 | Tag 关键词 | 分摊比例 | 说明 |
|---|---|---|---|
| cmf watch | watch1 | Phone:100% | |
| 天气服务 | nothingweatherserver, weather | Phone:Smart = 9:1 | 按接口调用次数，Phone 占 87% |
| AI Wallpaper | wallpaper | Phone:100% | |
| BetaOTA | betaota | Phone:100% | |
| SharedWidget | sharedwidget, sharewidget | Phone:100% | |
| 社区微件 | communitywidget | Phone:100% | |
| PushService | pushservice | Phone:100% | |
| 应用分类 | appclassification | Phone:100% | |
| ShortLink | shortlink | Phone:100% | |
| Nothing-Preorder | nothingpreorder | Phone:100% | |
| 问卷 | questionnaire | Phone:100% | |
| Camera盲测 | blindtest | Phone:100% | |
| IMEIServer | imei | Phone:100% | |
| 生成式widgets | genwidgets | Phone:100% | |

#### Public（无 Product Tag 或未匹配）
- 无 Product Tag 的资源统一归为 Public 分摊
- 分摊到 Phone / SmartProduct / IT / Community
- 具体比例由 Software 每月通知各方实际使用金额确定
- 特殊规则：
  1. EFS → 按 Nacos 规则分摊
  2. ECS/EKS → nothing-x、share-widget、生成式widget、essential-space 四者均摊
  3. TTS 实例 → 100% Smart
  4. Athena & Glue → 按 BI 看板规则分摊
  5. ELB → 100% Smart（Nothing-X 使用）
  6. MongoDB → 基础费用 $2500 由 Nothing-x 和 SharedWidget 各 50% 分摊，超出部分 100% Nothing-x
  7. Redshift → 按 DataCollection 规则分摊

#### EKS 相关 Tag
- Tag 中包含 `eks` 或 `ecs` 的资源
- 分摊规则：Smart:Phone:AI = 1:2:1

### 国内账号（整体归属 Smart）
| 业务模块 | Tag 关键词 |
|---|---|
| Nothing-x中国区 | nothingx |
| Mimi | mini |
| 埋点服务 | datacollection |
| Nothing-ota | ota |
| feedback | feedback |
| 账号中心-中国区 | nac |
| Common Cache | commoncache |
| 日志服务 | logcollect |
| Nacos | nacos |
| 其余 | 归属「其他」 |

### PLM 账号
| Tag | 归属 |
|---|---|
| OBA-app, CommonRedshift, ems-app-database, IPGuard, powerbi rds | IT |
| LogCollect, DIS | Phone |
| CIT | 销售 |
| 其余（Public） | Phone:IT = 2:1 分摊 |

---

## 分摊规则管理页面

### 展示格式
按截图格式，表格结构：账号 → 业务归属 → 业务模块 → 标签信息 → 分摊比例 → 费用分摊说明

### 编辑功能
- 共用资源和 Public 资源的分摊比例可编辑
- 编辑后保存到数据库（DB 规则优先于硬编码规则）
- 费用分摊说明可编辑并持久化保存
- 支持触发历史数据重算

---

## 费用预警
- 支持为各业务部门设置月度费用预警阈值
- 超过阈值时通过钉钉机器人发送通知
- 通知内容包含：部门名称、当前费用、阈值

---

## 报表导出
- 支持 Excel（.xlsx）、CSV、PDF 格式
- 导出当前查询条件下的费用数据

---

## 非功能需求
- 部署在公司内网，Docker Compose 一键启动
- 支持 100 个并发用户
- 当前阶段不要求登录认证
- AWS 凭证通过前端页面配置，不硬编码在代码中
- 数据永久保留
