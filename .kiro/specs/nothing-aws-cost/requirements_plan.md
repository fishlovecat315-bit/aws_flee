# Nothing AWS费用网站 - 需求计划

## 计划步骤

- [x] 步骤1：澄清关键问题（功能性需求）
- [x] 步骤2：澄清非功能性需求
- [x] 步骤3：用户审查并批准计划（待补充问题Q10）
- [x] 步骤4：编写正式需求文档（requirements.md）
- [x] 步骤5：创建配置文件（.config.kiro）

---

## 澄清问题

### 功能性需求问题

[Question 1] 费用数据的时间维度：
- 用户希望查看的最小时间粒度是什么？（日/周/月）
- 是否需要支持自定义时间范围查询？
- 历史数据需要保留多久？（例如：12个月、24个月）

[Answer 1]
查看的最小粒度为日，但是需要按照月另外呈现
支持自定义时间范围查询
历史数据永久保留
---

[Question 2] AWS Tag 规范：
- 目前各业务（销售、AI、Smart、Phone、IT、community）在 AWS 上是否已经有统一的 Tag 规范？
- Tag 的 Key/Value 格式是什么？（例如：`business_unit: sales`）
- 是否存在一个资源同时属于多个业务的情况？

[Answer 2]
我们目前主要有三个子账号，分别为PLM 账号、主业务账号、国内账号。
各个账号状况如下：
PLM账号下业务模块和Tag对应关系如下：
OBA:OBA-app
Redshift DWH:CommonRedshift
EMS系统Aurora:ems-app-database
IPGuard:IPGuard
PowerBI门户:powerbi rds
日志服务:LogCollect
日志分析:DIS
CIT:CIT
其中：
OBA-app、CommonRedshift、ems-app-database、IPGuard、powerbi rds 归属IT
LogCollect、DIS归属Phone
CIT 归属销售
此外PLM账号除上述Tag外，其余费用归属到一类,名称为Public，由Phone和IT分摊，分摊规则为Phone:IT=2:1
主账号下业务模块和Tag对应关系如下：
埋点服务	DataCollection
看板	BI
账号中心	NAC
NewsReporter	NewsReporter
Nacos	Nacos
Feedback	Feedback
Nothing-x	nothing x
xservice	xservice
NothingOTA	NothingOTA
TTS	TTS
Mimi	Mimi
二维码服务	LinkJumping
社区	Nothing Community
essential-space	essential-space
cmf watch	Watch1
天气服务	NothingWeatherServer
AI Wallpaper	Wallpaper
BetaOTA	BetaOTA
SharedWidget	SharedWidget
社区微件	CommunityWidget
PushService	PushService
应用分类	APPClassification
ShortLink	ShortLink
Nothing-Preorder	Nothing-Preorder
问卷	Questionnaire
Camera盲测	BlindTest
IMEIServer	IMEI
生成式widgets	GenWidgets
其中DataCollection、BI、NAC、NewsReporter、Nacos、Feedback为多业务共用，名称为“共用”
分摊规则如下：
DataCollection: Phone:Smart:销售=7:2:1
BI： Phone:Smart:销售=4：3：3
NAC：Smart：Community:销售=1：1：1
NewsReporter：Phone:Smart=1：1
Nacos： AI:Phone:Smart=2:3:1
Feedback：Phone:Smart=1:1
nothing x、xservice、NothingOTA、TTS、Mimi、LinkJumping归属为Smart
Nothing Community归属为Community
essential-space 归属为AI
Watch1、NothingWeatherServer、Wallpaper、BetaOTA、SharedWidget、CommunityWidget、PushService、APPClassification、ShortLink、Nothing-Preorder、
Questionnaire、BlindTest、IMEI、GenWidgets 归属为Phone
此外其余部分归属给Public，由Phone、Smart、IT、community分摊。分摊规则后续再讲
国内账号业务模块和Tag对应关系如下：
Nothing-x中国区	NothingX
Mimi	Mini
埋点服务	DataCollection
Nothing-ota	OTA
feedback	feedback
账号中心-中国区	NAC
Common Cache	Common Cache
日志服务	LogCollect
Nacos	Nacos
其余费用部分归属到“其他”
国内账号整体费用归属为Smart
---

[Question 3] 费用分摊规则：
- 是否存在共享资源（如基础设施、网络等）需要按比例分摊到各业务？
- 如果有，分摊规则是固定比例还是按用量动态计算？
- 分摊规则由谁来维护和修改？

[Answer 3]
存在，详细的分摊规则见上述Question 2
分摊规则的维护可以采用单独界面来管控、分配
---

[Question 4] 用户权限与数据可见范围：
- 不同角色（业务开发、业务负责人、部门负责人）看到的数据范围是否不同？
  - 例如：业务开发只能看自己业务的费用，部门负责人可以看所有业务？
- 是否需要登录认证？如果需要，使用什么方式（SSO/企业账号/其他）？

[Answer 4]
不用，不需要区分数据范围
先不用采用登录认证，后续再考虑采用登录认证
---

[Question 5] 图表与展示需求：
- 需要哪些类型的图表？（折线图趋势、柱状图对比、饼图占比等）
- 是否需要费用预警功能？（例如：某业务费用超过阈值时发送通知）
- 是否需要导出报表功能？（PDF/Excel）

[Answer 5]
折线图、柱状图、饼图等可以自主选择
需要费用预警功能
需要有导出报表功能
---

### 非功能性需求问题

[Question 6] 数据刷新频率：
- 费用数据需要多实时？（实时/每小时/每天同步一次）
- AWS Cost Explorer API 有一定延迟（通常24小时），这个延迟是否可以接受？

[Answer 6]
每天同步一次即可
可以接受
---

[Question 7] 访问方式与部署：
- 这个网站是内部系统，部署在哪里？（AWS 内网/公司内网/公网+认证）
- 预计同时使用的用户数量大概是多少？
- 是否有特定的技术栈偏好？（前端框架、后端语言等）

[Answer 7]
内部系统，会部署在内网
用户数不多，100以内
无特殊技术栈偏好
---

[Question 8] 安全与合规：
- AWS 账号的访问凭证如何管理？（IAM Role/Access Key）
- 费用数据是否属于敏感信息，是否有数据访问审计要求？

[Answer 8]
暂时不需要
费用数据属于敏感信息，有数据访问审计
---

---

## 补充澄清问题

[Question 9] 主业务账号 Public 分摊规则（待确认）：

在 Answer 2 中提到，主业务账号除已明确归属的 Tag 外，其余费用归属为 **Public**，由 Phone、Smart、IT、Community 分摊，但分摊规则"后续再讲"。

请确认以下内容：

1. **分摊方式**：是固定比例分摊，还是按某种动态指标（如各业务资源用量、收入占比等）计算？
2. **固定比例（如适用）**：Phone : Smart : IT : Community 的比例是多少？（例如 4:3:2:1）
3. **"共用"部分的分摊**：DataCollection、BI、NAC、NewsReporter、Nacos、Feedback 这些"共用"资源的费用，是否也需要分摊到各业务？如果是，分摊规则是什么？
4. **分摊计算时机**：分摊是在数据同步时预先计算好，还是在前端展示时实时计算？

[Answer 9]
主业务账号Public部分包括两部分：已打Tag但无法确定业务方和无Tag资源。
无Tag资源中:
- MongoDB Atlas基础费用$2500分摊给Nothing-x、SharedWidget，其余归属为Nothing-x业务
- Athena归属到BI业务
- Elastic Load Balancing归属到Nothing-x业务
- Redshift归属到DataCollection业务
- 可以罗列这部分详细资源
有Tag但无业务归属部分：
- EKS开头的资源由nothing-x、share-widget、Gen-widget、essential-space 4个业务平均分摊
- TTSProxy开头的资源归属到TTS业务
---

---

## 补充澄清问题（第二轮）

[Question 10] 以下几个细节需要确认，以确保需求文档完整：

**10.1 MongoDB Atlas 基础费用分摊比例**
主业务账号 Public 中，MongoDB Atlas 基础费用 $2500 分摊给 Nothing-x 和 SharedWidget，请确认两者的分摊比例是多少？（例如 1:1 平均分摊，或其他比例）
1：1
**10.2 费用预警通知方式**
费用预警触发后，通知通过什么渠道发送？
- [ *] 钉钉机器人
- [ ] 邮件
- [ ] 企业微信
- [ ] 页面内弹窗/消息中心
- [ ] 其他：___

**10.3 导出报表格式**
导出报表支持哪些格式？
- [ *] Excel（.xlsx）
- [* ] CSV
- [* ] PDF
- [ ] 其他：___

**10.4 数据访问审计要求**
费用数据有审计要求，请确认审计的具体内容：
- 审计对象：记录谁访问了哪些数据？还是只记录导出操作？
- 审计日志保留时长：多久？
- 审计日志查看方式：是否需要在系统内提供审计日志查询界面？

[Answer 10]
（请填写）
先去除数据审计
---

## 用户审批

请补充 Answer 10 后告知批准，我将开始编写正式需求文档。
