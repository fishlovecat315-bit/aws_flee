# 实现计划：Nothing AWS 费用统计平台

## 概述

按照"基础设施 → 数据层 → 后端服务 → API → 前端"的顺序逐步实现，每个阶段完成后通过测试验证，确保增量可运行。

## 任务列表

- [x] 1. 搭建项目基础设施
  - [x] 1.1 创建项目目录结构与配置文件
    - 创建 `backend/`、`frontend/`、`docker/` 目录结构
    - 创建 `backend/app/`（api、services、models、schemas、core）子目录
    - 创建 `backend/requirements.txt`，包含 fastapi、uvicorn、sqlalchemy、asyncpg、redis、boto3、apscheduler、openpyxl、weasyprint、hypothesis、pytest、testcontainers、moto、responses 等依赖
    - 创建 `backend/app/core/config.py`，使用 pydantic-settings 从环境变量读取数据库 URL、Redis URL、AWS 凭证、钉钉 Webhook URL
    - _需求：非功能需求-安全 1_

  - [x] 1.2 创建 Docker Compose 配置
    - 编写 `docker-compose.yml`，包含 postgres、redis、backend、frontend 四个服务
    - 编写 `docker/postgres/init.sql` 占位文件（后续由迁移脚本填充）
    - 编写 `backend/Dockerfile` 和 `frontend/Dockerfile`
    - _需求：非功能需求-访问与权限 1_

  - [x] 1.3 初始化 FastAPI 应用入口
    - 创建 `backend/app/main.py`，注册路由前缀 `/api/v1`，配置 CORS（仅内网）
    - 创建 `backend/app/core/database.py`，使用 SQLAlchemy async engine 连接 PostgreSQL
    - 创建 `backend/app/core/redis_client.py`，初始化 Redis 连接
    - _需求：非功能需求-访问与权限 4_

- [x] 2. 实现数据库模型与迁移
  - [x] 2.1 定义 SQLAlchemy ORM 模型
    - 在 `backend/app/models/` 下创建六张表的 ORM 模型：`RawCostRecord`、`AllocatedCostRecord`、`AllocationRule`、`AllocationRuleHistory`、`AlertThreshold`、`SyncLog`
    - 按设计文档中的字段定义添加列类型、约束、索引（`idx_allocated_date`、`idx_allocated_dept`）
    - _需求：1.3、4.1、4.2、5.2_

  - [x] 2.2 创建数据库迁移脚本
    - 使用 Alembic 初始化迁移环境（`backend/alembic/`）
    - 生成初始迁移文件，包含六张表的 DDL
    - 在 `docker/postgres/init.sql` 中引用或直接写入建表 SQL
    - _需求：1.3_

- [x] 3. 实现 AWS 费用数据同步服务
  - [x] 3.1 实现 CostSyncService 核心逻辑
    - 创建 `backend/app/services/cost_sync.py`
    - 实现 `sync_account(account_id, account_name, start_date, end_date)` 方法，调用 boto3 `get_cost_and_usage`，按 Tag 分组，日粒度
    - 实现 UPSERT 逻辑将结果写入 `raw_cost_records`（唯一键：account_id + date + service + tag_key + tag_value）
    - 实现 `sync_all()` 方法，依次同步三个子账号，写入 `sync_logs`
    - 实现同步失败时更新 `sync_logs.status = 'failed'` 并记录 `error_message`
    - _需求：1.1、1.2、1.5_

  - [x] 3.2 配置 APScheduler 定时任务
    - 在 `backend/app/core/scheduler.py` 中配置 APScheduler，每日 02:00 触发 `sync_all()`
    - 在 FastAPI 启动事件中启动调度器
    - 实现补同步逻辑：启动时检查昨日是否有成功同步记录，若无则触发补同步
    - _需求：1.1、1.5_

  - [ ]* 3.3 编写属性测试：属性 1（数据同步覆盖所有账号）
    - **属性 1：数据同步覆盖所有账号**
    - 使用 Hypothesis 生成随机日期范围，Mock boto3 返回数据，验证同步后 `raw_cost_records` 中存在来自三个子账号的记录
    - 注释格式：`# Feature: nothing-aws-cost, Property 1: 数据同步覆盖所有账号`
    - **验证需求：1.2**

  - [ ]* 3.4 编写属性测试：属性 2（同步后自动触发分摊计算）
    - **属性 2：同步后自动触发分摊计算**
    - 生成随机费用数据，执行同步流程，验证 `allocated_cost_records` 中存在对应日期的记录
    - 注释格式：`# Feature: nothing-aws-cost, Property 2: 同步后自动触发分摊计算`
    - **验证需求：1.6**

- [x] 4. 实现费用分摊计算引擎
  - [x] 4.1 实现 AllocationEngine 核心分摊逻辑
    - 创建 `backend/app/services/allocation_engine.py`
    - 实现规则优先级处理：明确 Tag 归属 → 共用资源分摊 → Public 规则
    - 实现 PLM 账号分摊逻辑（直接归属 + Phone:IT=2:1 Public 分摊）
    - 实现主业务账号分摊逻辑（直接归属、共用比例分摊、EKS 四业务平均、TTSProxy 归 TTS）
    - 实现国内账号分摊逻辑（全部归 Smart，其余归"其他"）
    - 实现 `allocate_date_range(start_date, end_date)` 方法，支持历史重算
    - 无匹配规则时将费用归入"未分类"并记录警告日志
    - _需求：4.1、4.2、4.3、4.4_

  - [x] 4.2 实现 MongoDB Atlas 特殊分摊规则
    - 在 AllocationEngine 中实现 `allocate_mongodb(total_amount)` 函数
    - 基础费用 $2500 由 Nothing-x 和 SharedWidget 各 50%；超出部分全归 Nothing-x
    - _需求：4.1、4.3_

  - [ ]* 4.3 编写属性测试：属性 3（分摊费用守恒）
    - **属性 3：分摊费用守恒**
    - 使用 `st.decimals(min_value=0, max_value=100000)` 生成随机费用金额和规则，验证分摊后各部门金额之和等于原始金额（误差 ≤ $0.01）
    - 注释格式：`# Feature: nothing-aws-cost, Property 3: 分摊费用守恒`
    - **验证需求：4.2、4.3**

  - [ ]* 4.4 编写属性测试：属性 11（历史重算结果一致）
    - **属性 11：历史重算结果与新规则一致**
    - 使用 `st.lists()` + `st.fixed_dictionaries()` 生成随机历史数据和新规则，验证重算后结果与直接用新规则计算一致
    - 注释格式：`# Feature: nothing-aws-cost, Property 11: 历史重算结果一致`
    - **验证需求：4.4**

- [x] 5. 检查点 —— 确保所有测试通过
  - 确保所有测试通过，如有问题请向用户反馈。

- [x] 6. 实现费用查询 API
  - [x] 6.1 实现费用查询数据访问层
    - 创建 `backend/app/repositories/cost_repository.py`
    - 实现 `get_daily_costs(start_date, end_date, department, account_name, tag_value)` 查询方法
    - 实现 `get_monthly_costs(year, month, department, account_name)` 聚合查询方法
    - 实现 `get_summary(start_date, end_date)` 多维度汇总方法（按部门、按账号、按 Tag）
    - _需求：2.1、2.2、2.3、2.4、2.5、2.6_

  - [x] 6.2 实现费用查询 API 路由
    - 创建 `backend/app/api/costs.py`，注册路由：
      - `GET /costs/daily`
      - `GET /costs/monthly`
      - `GET /costs/summary`
    - 定义 Pydantic 响应 Schema（`backend/app/schemas/cost.py`）
    - 实现 Redis 缓存层：相同查询参数命中缓存直接返回
    - _需求：2.1、2.2、2.3、2.7_

  - [ ]* 6.3 编写属性测试：属性 4（月度汇总等于日粒度之和）
    - **属性 4：月度汇总等于日粒度之和**
    - 使用 `st.dates()` + `st.decimals()` 生成随机月份数据，验证月度聚合结果等于该月所有日粒度之和
    - 注释格式：`# Feature: nothing-aws-cost, Property 4: 月度汇总等于日粒度之和`
    - **验证需求：2.2**

  - [ ]* 6.4 编写属性测试：属性 5（查询结果在时间范围内）
    - **属性 5：查询结果在时间范围内**
    - 使用 `st.dates()` 生成随机时间范围，验证返回的所有记录日期均在 [start_date, end_date] 内
    - 注释格式：`# Feature: nothing-aws-cost, Property 5: 查询结果在时间范围内`
    - **验证需求：2.3**

  - [ ]* 6.5 编写属性测试：属性 6（查询结果包含必要维度字段）
    - **属性 6：查询结果包含必要维度字段**
    - 验证每条查询结果记录均包含 date、department、account_name、tag_value、amount_usd 字段
    - 注释格式：`# Feature: nothing-aws-cost, Property 6: 查询结果包含必要维度字段`
    - **验证需求：2.4、2.5、2.6**

- [x] 7. 实现分摊规则管理 API
  - [x] 7.1 实现规则管理数据访问层与 API 路由
    - 创建 `backend/app/repositories/rule_repository.py`，实现规则的查询和更新方法
    - 规则更新时自动写入 `allocation_rule_history` 表
    - 创建 `backend/app/api/rules.py`，注册路由：
      - `GET /rules`
      - `PUT /rules/{id}`
      - `POST /rules/{id}/recalculate`（触发历史重算，接收 start_date、end_date）
    - 定义 Pydantic Schema（`backend/app/schemas/rule.py`）
    - 后端校验 `ratios` 字段总和是否等于 1.0，不满足时返回 400 错误
    - _需求：5.1、5.2、5.3、5.4、4.4_

  - [ ]* 7.2 编写属性测试：属性 7（规则修改 Round-trip）
    - **属性 7：规则修改后查询返回新规则**
    - 使用 `st.fixed_dictionaries()` 生成随机规则配置，保存后立即查询，验证返回值与保存值一致
    - 注释格式：`# Feature: nothing-aws-cost, Property 7: 规则修改 Round-trip`
    - **验证需求：5.2**

  - [ ]* 7.3 编写属性测试：属性 8（分摊比例之和为 100%）
    - **属性 8：分摊比例之和为 100%**
    - 使用 `st.floats()` 生成随机比例配置，验证后端校验逻辑正确拒绝总和不等于 1.0 的规则
    - 注释格式：`# Feature: nothing-aws-cost, Property 8: 分摊比例之和为 100%`
    - **验证需求：5.4**

- [x] 8. 实现费用预警服务
  - [x] 8.1 实现 AlertService 与钉钉通知
    - 创建 `backend/app/services/alert_service.py`
    - 实现 `check_and_alert()` 方法：汇总各部门当月累计费用，与 `alert_thresholds` 对比
    - 实现钉钉 Webhook 调用，按设计文档中的 Markdown 消息格式构造消息体
    - Webhook 调用失败时记录错误日志，不中断主流程
    - 在 AllocationEngine 计算完成后调用 `check_and_alert()`
    - _需求：6.1、6.2、6.3_

  - [x] 8.2 实现预警阈值管理 API
    - 创建 `backend/app/api/alerts.py`，注册路由：
      - `GET /alerts/thresholds`
      - `PUT /alerts/thresholds/{dept}`
    - 定义 Pydantic Schema（`backend/app/schemas/alert.py`）
    - _需求：6.1_

  - [ ]* 8.3 编写属性测试：属性 9（超阈值时发送包含完整信息的通知）
    - **属性 9：超阈值时发送包含完整信息的通知**
    - 使用 `st.decimals()` 生成随机部门费用和阈值，Mock 钉钉 Webhook，验证通知消息包含 department、current_amount、threshold 三个字段
    - 注释格式：`# Feature: nothing-aws-cost, Property 9: 超阈值时发送包含完整信息的通知`
    - **验证需求：6.2、6.3**

- [x] 9. 实现报表导出服务
  - [x] 9.1 实现 ExportService 与导出 API
    - 创建 `backend/app/services/export_service.py`
    - 实现 `export_excel(data)` 使用 openpyxl 生成 .xlsx 文件
    - 实现 `export_csv(data)` 使用 csv 模块生成 .csv 文件
    - 实现 `export_pdf(data)` 使用 WeasyPrint 生成 .pdf 文件
    - 创建 `backend/app/api/export.py`，注册路由 `GET /export`，接收 format、start_date、end_date、department、account_name 参数
    - 以流式响应返回文件，设置 `Content-Disposition: attachment`
    - _需求：7.1、7.2、7.3、7.4_

  - [ ]* 9.2 编写属性测试：属性 10（导出数据与查询结果一致）
    - **属性 10：导出数据与查询结果一致**
    - 使用 `st.dates()` + `st.sampled_from()` 生成随机查询条件，对比 API 查询结果与导出文件（xlsx/csv）中的数据行数和金额
    - 注释格式：`# Feature: nothing-aws-cost, Property 10: 导出数据与查询结果一致`
    - **验证需求：7.1、7.2、7.4**

- [x] 10. 实现同步管理 API
  - [x] 10.1 实现同步日志查询与手动触发接口
    - 创建 `backend/app/api/sync.py`，注册路由：
      - `GET /sync/logs`（返回同步日志列表）
      - `POST /sync/trigger`（手动触发同步，管理员用）
    - 定义 Pydantic Schema（`backend/app/schemas/sync.py`）
    - 在 `main.py` 中注册所有路由模块
    - _需求：1.1、1.5_

- [x] 11. 检查点 —— 确保所有后端测试通过
  - 确保所有测试通过，如有问题请向用户反馈。

- [x] 12. 搭建前端项目结构
  - [x] 12.1 初始化 React + TypeScript 前端项目
    - 使用 Vite 创建 `frontend/` 项目，配置 TypeScript
    - 安装依赖：react-router-dom、echarts-for-react、axios、antd（或 shadcn/ui）
    - 创建目录结构：`src/pages/`、`src/components/`、`src/api/`、`src/types/`
    - 创建 `src/api/client.ts`，封装 axios 实例，统一设置 baseURL 为 `/api/v1`
    - 创建 `src/types/index.ts`，定义前端数据类型（与后端 Schema 对应）
    - 创建 `src/App.tsx`，配置 react-router-dom 路由：`/dashboard`、`/costs`、`/rules`、`/alerts`
    - 创建 `src/components/Layout.tsx`，实现顶部导航 + 侧边栏布局
    - _需求：3.4_

- [x] 13. 实现前端费用总览页（Dashboard）
  - [x] 13.1 实现 Dashboard 页面组件
    - 创建 `src/pages/Dashboard.tsx`
    - 实现时间范围选择器（日/月粒度切换）
    - 实现维度筛选器（部门/账号/Tag 下拉选择）
    - 调用 `GET /costs/daily` 和 `GET /costs/monthly` 接口获取数据
    - _需求：2.1、2.2、2.3、2.4、2.5、2.6_

  - [x] 13.2 实现 ECharts 图表组件
    - 创建 `src/components/CostChart.tsx`，封装 ECharts 折线图/柱状图/饼图切换逻辑
    - 图表类型切换时不刷新页面（状态驱动）
    - 创建 `src/components/CostSummaryTable.tsx`，展示费用汇总数据表格
    - _需求：3.1、3.2、3.3、3.4_

- [x] 14. 实现前端费用明细页
  - [x] 14.1 实现费用明细页组件
    - 创建 `src/pages/CostDetail.tsx`
    - 实现高级筛选面板（日期范围、部门、账号、Tag 多条件筛选）
    - 实现分页数据表格，调用 `GET /costs/daily` 接口
    - 实现导出按钮（xlsx/csv/pdf），调用 `GET /export` 接口并触发浏览器下载
    - _需求：2.3、2.4、2.5、2.6、7.1、7.2、7.3、7.4_

- [x] 15. 实现前端分摊规则管理页
  - [x] 15.1 实现规则管理页组件
    - 创建 `src/pages/RulesManagement.tsx`
    - 实现规则列表，按账号分组展示（PLM 账号、主业务账号、国内账号）
    - 实现规则编辑表单，比例输入时实时校验总和是否等于 100%，不满足时禁用保存按钮
    - 调用 `GET /rules`、`PUT /rules/{id}`、`POST /rules/{id}/recalculate` 接口
    - _需求：5.1、5.2、5.3、5.4、4.4_

- [x] 16. 实现前端预警设置页
  - [x] 16.1 实现预警设置页组件
    - 创建 `src/pages/AlertSettings.tsx`
    - 实现各业务部门阈值设置表单（六个部门：销售、AI、Smart、Phone、IT、Community）
    - 调用 `GET /alerts/thresholds`、`PUT /alerts/thresholds/{dept}` 接口
    - _需求：6.1_

- [x] 17. 编写集成测试
  - [x] 17.1 实现完整同步→分摊→预警流程集成测试
    - 创建 `backend/tests/integration/test_full_flow.py`
    - 使用 `testcontainers` 启动真实 PostgreSQL 实例
    - 使用 `moto` Mock AWS Cost Explorer API，返回三个账号的模拟费用数据
    - 使用 `responses` Mock 钉钉 Webhook
    - 测试完整流程：触发同步 → 验证 `raw_cost_records` → 验证 `allocated_cost_records` → 验证预警通知
    - _需求：1.1、1.2、1.6、6.2、6.3_

  - [x] 17.2 实现 API 端到端集成测试
    - 创建 `backend/tests/integration/test_api.py`
    - 使用 FastAPI `TestClient` 测试所有 API 端点的请求/响应格式
    - 覆盖费用查询、规则管理、预警阈值、导出接口
    - _需求：2.1、2.2、5.2、7.1、7.2、7.3_

- [x] 18. 最终检查点 —— 确保所有测试通过
  - 确保所有单元测试、属性测试和集成测试通过，如有问题请向用户反馈。

## 备注

- 标有 `*` 的子任务为可选测试任务，可在 MVP 阶段跳过以加快交付
- 每个任务均引用了具体需求条款，便于追溯
- 属性测试文件统一放在 `backend/tests/property/` 目录下
- 集成测试文件放在 `backend/tests/integration/` 目录下
- 单元测试文件放在 `backend/tests/unit/` 目录下
- 属性测试注释格式：`# Feature: nothing-aws-cost, Property {N}: {属性描述}`
