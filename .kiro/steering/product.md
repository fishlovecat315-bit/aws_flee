# Product: Nothing AWS Cost Platform

An internal AWS cost management and allocation platform. It pulls cost data from AWS Cost Explorer, allocates expenses to business departments and modules using configurable rules, and presents the data through a web dashboard.

## Core Concepts

- **Accounts**: Three AWS accounts are tracked — `主业务` (main business), `PLM`, and `国内` (China)
- **Allocation**: Raw AWS costs are split across departments (`Smart`, `Phone`, `AI`, `Community`, `IT`, `销售`, `Public`) based on resource tags (`appname` tag) and service type
- **Business Modules**: Tagged resources map to named business modules (e.g., NothingX, NothingOTA, essential-space) via a normalized tag lookup (`BIZ_META`)
- **Rules**: Allocation rules can be hardcoded in `AllocationEngine` or overridden via DB-stored `AllocationRule` records (DB rules take priority)
- **Alerts**: Monthly spend thresholds per department trigger DingTalk webhook notifications
- **Sync**: AWS cost data is synced daily via APScheduler; historical backfill is supported via API trigger

## Departments
`Smart`, `Phone`, `AI`, `Community`, `IT`, `销售`, `Public`, `其他`, `未分类`
