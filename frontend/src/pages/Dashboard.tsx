import { useState, useEffect } from 'react'
import {
  Select, DatePicker, Table, Spin, Alert, Card, Row, Col,
  Statistic, Space, Button, Modal, message, Tabs, Tag,
} from 'antd'
import { SyncOutlined, HistoryOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs, { Dayjs } from 'dayjs'
import client from '../api/client'
import type { DailyCostItem, MonthlyCostItem, SummaryResponse } from '../types'
import CostChart from '../components/CostChart'
import CostSummaryTable from '../components/CostSummaryTable'

const DEPARTMENTS = ['all', '销售', 'AI', 'Smart', 'Phone', 'IT', 'Community', '未分类']
const ACCOUNTS = ['all', 'PLM', '主业务', '国内']

const now = dayjs()
const currentYear = now.year()
const currentMonth = now.month() + 1

// 生成过去 12 个月的选项（不含当月）
const historyMonthOptions = Array.from({ length: 12 }, (_, i) => {
  const d = now.subtract(i + 1, 'month')
  return { label: `${d.year()} 年 ${d.month() + 1} 月`, value: `${d.year()}-${d.month() + 1}` }
})

const dailyColumns: ColumnsType<DailyCostItem> = [
  { title: '日期', dataIndex: 'date', key: 'date', width: 110,
    sorter: (a, b) => a.date.localeCompare(b.date) },
  { title: '部门', dataIndex: 'department', key: 'department', width: 90 },
  { title: '账号', dataIndex: 'account_name', key: 'account_name', width: 90 },
  { title: '业务模块', dataIndex: 'tag_value', key: 'tag_value', width: 160,
    render: (v: string | null) => v ?? '-' },
  { title: '费用 (USD)', dataIndex: 'amount_usd', key: 'amount_usd', width: 120,
    render: (v: number) => `$${Number(v).toFixed(2)}`,
    sorter: (a, b) => a.amount_usd - b.amount_usd },
]

const monthlyColumns: ColumnsType<MonthlyCostItem> = [
  { title: '年月', dataIndex: 'year_month', key: 'year_month', width: 100,
    sorter: (a, b) => a.year_month.localeCompare(b.year_month) },
  { title: '部门', dataIndex: 'department', key: 'department', width: 90 },
  { title: '费用 (USD)', dataIndex: 'amount_usd', key: 'amount_usd', width: 120,
    render: (v: number) => `$${Number(v).toFixed(2)}`,
    sorter: (a, b) => a.amount_usd - b.amount_usd },
]

export default function Dashboard() {
  // 当月视图
  const [dailyDateRange, setDailyDateRange] = useState<[Dayjs, Dayjs]>([
    now.startOf('month'), now.subtract(1, 'day'),
  ])
  const [dailyDept, setDailyDept] = useState('all')
  const [dailyAccount, setDailyAccount] = useState('all')
  const [dailyData, setDailyData] = useState<DailyCostItem[]>([])
  const [dailySummary, setDailySummary] = useState<SummaryResponse | null>(null)
  const [dailyLoading, setDailyLoading] = useState(false)

  // 历史月份视图
  const [histMonth, setHistMonth] = useState(historyMonthOptions[0].value)
  const [histDept, setHistDept] = useState('all')
  const [histAccount, setHistAccount] = useState('all')
  const [histData, setHistData] = useState<MonthlyCostItem[]>([])
  const [histSummary, setHistSummary] = useState<SummaryResponse | null>(null)
  const [histLoading, setHistLoading] = useState(false)

  const [error, setError] = useState<string | null>(null)

  // 补拉弹窗
  const [backfillVisible, setBackfillVisible] = useState(false)
  const [backfillRange, setBackfillRange] = useState<[Dayjs, Dayjs]>([
    now.subtract(1, 'month').startOf('month'),
    now.subtract(1, 'month').endOf('month'),
  ])
  const [backfilling, setBackfilling] = useState(false)

  // 当月数据加载
  useEffect(() => {
    loadCurrentMonth()
  }, [dailyDateRange, dailyDept, dailyAccount])

  // 历史月份数据加载
  useEffect(() => {
    loadHistoryMonth()
  }, [histMonth, histDept, histAccount])

  async function loadCurrentMonth() {
    setDailyLoading(true)
    setError(null)
    try {
      const params: Record<string, string> = {
        start_date: dailyDateRange[0].format('YYYY-MM-DD'),
        end_date: dailyDateRange[1].format('YYYY-MM-DD'),
      }
      if (dailyDept !== 'all') params.department = dailyDept
      if (dailyAccount !== 'all') params.account_name = dailyAccount
      const [dataRes, summaryRes] = await Promise.all([
        client.get('/costs/daily', { params }),
        client.get('/costs/summary', { params: { start_date: params.start_date, end_date: params.end_date } }),
      ])
      setDailyData(dataRes.data.data ?? [])
      setDailySummary(summaryRes.data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '数据加载失败')
    } finally {
      setDailyLoading(false)
    }
  }

  async function loadHistoryMonth() {
    setHistLoading(true)
    setError(null)
    try {
      const [y, m] = histMonth.split('-').map(Number)
      const startDate = `${y}-${String(m).padStart(2, '0')}-01`
      const endDate = dayjs(`${y}-${m}-01`).endOf('month').format('YYYY-MM-DD')
      const params: Record<string, string | number> = { year: y, month: m }
      if (histDept !== 'all') params.department = histDept
      if (histAccount !== 'all') params.account_name = histAccount
      const [dataRes, summaryRes] = await Promise.all([
        client.get('/costs/monthly', { params }),
        client.get('/costs/summary', { params: { start_date: startDate, end_date: endDate } }),
      ])
      setHistData(dataRes.data.data ?? [])
      setHistSummary(summaryRes.data)
    } catch (e) {
      setError(e instanceof Error ? e.message : '数据加载失败')
    } finally {
      setHistLoading(false)
    }
  }

  const triggerBackfill = async () => {
    setBackfilling(true)
    try {
      const start = backfillRange[0].format('YYYY-MM-DD')
      const end = backfillRange[1].format('YYYY-MM-DD')
      await client.post(`/sync/trigger?start_date=${start}&end_date=${end}`)
      message.success(`已触发 ${start} ~ ${end} 历史数据补拉，完成后刷新页面查看`)
      setBackfillVisible(false)
    } catch {
      message.error('触发失败')
    } finally {
      setBackfilling(false)
    }
  }

  const dailyTotal = dailyData.reduce((s, r) => s + Number(r.amount_usd), 0)
  const histTotal = histData.reduce((s, r) => s + Number(r.amount_usd), 0)

  const filterBar = (
    dept: string, setDept: (v: string) => void,
    account: string, setAccount: (v: string) => void,
  ) => (
    <Space wrap>
      <Select value={dept} onChange={setDept} style={{ width: 120 }}
        options={DEPARTMENTS.map(d => ({ label: d === 'all' ? '全部部门' : d, value: d }))} />
      <Select value={account} onChange={setAccount} style={{ width: 120 }}
        options={ACCOUNTS.map(a => ({ label: a === 'all' ? '全部账号' : a, value: a }))} />
    </Space>
  )

  return (
    <div style={{ padding: 24 }}>
      {error && (
        <Alert type="error" message={error} style={{ marginBottom: 16 }} showIcon closable onClose={() => setError(null)} />
      )}

      <Tabs
        defaultActiveKey="current"
        tabBarExtraContent={
          <Button icon={<HistoryOutlined />} onClick={() => setBackfillVisible(true)}>
            历史补拉
          </Button>
        }
        items={[
          {
            key: 'current',
            label: <span><Tag color="blue">{currentYear} 年 {currentMonth} 月</Tag>当月费用</span>,
            children: (
              <Spin spinning={dailyLoading}>
                {/* 当月工具栏 */}
                <Card style={{ marginBottom: 16 }}>
                  <Space wrap>
                    <DatePicker.RangePicker
                      value={dailyDateRange}
                      onChange={(vals) => {
                        if (vals?.[0] && vals?.[1]) setDailyDateRange([vals[0], vals[1]])
                      }}
                      allowClear={false}
                      disabledDate={(d) => d.isAfter(now) || d.isBefore(now.startOf('month').subtract(1, 'day'))}
                    />
                    {filterBar(dailyDept, setDailyDept, dailyAccount, setDailyAccount)}
                    <Button icon={<SyncOutlined />} onClick={loadCurrentMonth}>刷新</Button>
                  </Space>
                </Card>

                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={8}>
                    <Card><Statistic title="当月累计费用" value={dailyTotal} precision={2} prefix="$" /></Card>
                  </Col>
                  <Col span={8}>
                    <Card><Statistic title="数据天数" value={new Set(dailyData.map(r => r.date)).size} suffix="天" /></Card>
                  </Col>
                </Row>

                <CostChart data={dailyData} granularity="daily" />
                {dailySummary && <CostSummaryTable summary={dailySummary} />}

                <Card title="每日费用明细" style={{ marginTop: 16 }}>
                  <Table<DailyCostItem>
                    rowKey={(r) => `${r.date}-${r.department}-${r.account_name}-${r.tag_value}`}
                    columns={dailyColumns}
                    dataSource={dailyData}
                    pagination={{ pageSize: 20, showSizeChanger: true }}
                    size="small"
                  />
                </Card>
              </Spin>
            ),
          },
          {
            key: 'history',
            label: <span><HistoryOutlined /> 历史月份</span>,
            children: (
              <Spin spinning={histLoading}>
                {/* 历史工具栏 */}
                <Card style={{ marginBottom: 16 }}>
                  <Space wrap>
                    <Select
                      value={histMonth}
                      onChange={setHistMonth}
                      style={{ width: 160 }}
                      options={historyMonthOptions}
                    />
                    {filterBar(histDept, setHistDept, histAccount, setHistAccount)}
                    <Button icon={<SyncOutlined />} onClick={loadHistoryMonth}>刷新</Button>
                  </Space>
                </Card>

                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={8}>
                    <Card><Statistic title="月度总费用" value={histTotal} precision={2} prefix="$" /></Card>
                  </Col>
                </Row>

                {/* 历史只看月度汇总和业务费用，不看日粒度明细 */}
                <CostChart data={histData} granularity="monthly" />
                {histSummary && <CostSummaryTable summary={histSummary} />}

                <Card title="月度费用汇总（按部门）" style={{ marginTop: 16 }}>
                  <Table<MonthlyCostItem>
                    rowKey={(r) => `${r.year_month}-${r.department}`}
                    columns={monthlyColumns}
                    dataSource={histData}
                    pagination={{ pageSize: 20, showSizeChanger: true }}
                    size="small"
                  />
                </Card>
              </Spin>
            ),
          },
        ]}
      />

      {/* 历史补拉弹窗，限制在过去 12 个月 */}
      <Modal
        title="历史费用数据补拉"
        open={backfillVisible}
        onCancel={() => setBackfillVisible(false)}
        onOk={triggerBackfill}
        okText="开始补拉"
        cancelText="取消"
        confirmLoading={backfilling}
      >
        <p style={{ color: '#666', marginBottom: 12 }}>
          选择需要补拉的日期范围（最多过去 12 个月），系统将从 AWS 重新拉取该范围内的费用数据。
        </p>
        <DatePicker.RangePicker
          value={backfillRange}
          onChange={(vals) => {
            if (vals?.[0] && vals?.[1]) setBackfillRange([vals[0], vals[1]])
          }}
          style={{ width: '100%' }}
          disabledDate={(d) =>
            d.isAfter(now.subtract(1, 'day')) ||
            d.isBefore(now.subtract(12, 'month').startOf('month'))
          }
          picker="date"
        />
      </Modal>
    </div>
  )
}
