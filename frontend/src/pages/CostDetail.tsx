import { useState, useEffect } from 'react'
import { Table, Card, Select, Space, Button, Tag, Spin, Alert, Statistic, Row, Col, Tooltip } from 'antd'
import { SyncOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import client from '../api/client'

const ACCOUNTS = ['主业务', 'PLM', '国内']

const GROUP_ORDER = ['共用', 'SmartProduct', 'Community', 'AI', 'Phone', 'Public', '其他']
const GROUP_COLORS: Record<string, string> = {
  '共用': 'green', 'SmartProduct': 'orange', 'Community': 'blue',
  'AI': 'purple', 'Phone': 'gold', 'Public': 'cyan', '其他': 'default',
}
const GROUP_BG: Record<string, string> = {
  '共用': '#f6ffed', 'SmartProduct': '#fff7e6', 'Community': '#e6f7ff',
  'AI': '#f9f0ff', 'Phone': '#fffbe6', 'Public': '#e6fffb', '其他': '#fafafa',
}
const DEPT_COLORS: Record<string, string> = {
  'Smart': 'orange', 'Phone': 'gold', 'AI': 'purple',
  'Community': 'blue', 'IT': 'cyan', '销售': 'red', '其他': 'default',
}

interface RowData {
  key: string
  account_name: string
  biz_group: string
  biz_name: string
  tag_value: string | null
  department: string
  month_costs: Record<string, number>
  dept_breakdown: Record<string, Record<string, number>>
  mom_change: number
}

export default function CostDetail() {
  const [accountName, setAccountName] = useState('主业务')
  const [months, setMonths] = useState(4)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [monthKeys, setMonthKeys] = useState<string[]>([])
  const [rows, setRows] = useState<RowData[]>([])

  useEffect(() => { fetchData() }, [accountName, months])  // eslint-disable-line react-hooks/exhaustive-deps

  async function fetchData() {
    setLoading(true)
    setError(null)
    try {
      const res = await client.get('/costs/business-summary', {
        params: { account_name: accountName, months },
      })
      const { months: mks, data } = res.data
      setMonthKeys(mks)
      setRows(data.map((r: RowData, i: number) => ({ ...r, key: String(i) })))
    } catch (e) {
      setError(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }

  const lastMonth = monthKeys[monthKeys.length - 1]
  const prevMonth = monthKeys[monthKeys.length - 2]
  const totalLast = rows.reduce((s, r) => s + (r.month_costs[lastMonth] ?? 0), 0)
  const totalPrev = rows.reduce((s, r) => s + (r.month_costs[prevMonth] ?? 0), 0)

  // 计算每个 biz_group 的行数，用于合并单元格
  const groupSpanMap: Record<string, { start: number; count: number }> = {}
  rows.forEach((r, i) => {
    if (!groupSpanMap[r.biz_group]) groupSpanMap[r.biz_group] = { start: i, count: 0 }
    groupSpanMap[r.biz_group].count++
  })

  const columns: ColumnsType<RowData> = [
    {
      title: '业务归属',
      dataIndex: 'biz_group',
      key: 'biz_group',
      width: 100,
      onCell: (record, index) => {
        const info = groupSpanMap[record.biz_group]
        if (index === info?.start) return { rowSpan: info.count, style: { background: GROUP_BG[record.biz_group], verticalAlign: 'middle' } }
        return { rowSpan: 0 }
      },
      render: (g: string) => <Tag color={GROUP_COLORS[g]} style={{ fontWeight: 600 }}>{g}</Tag>,
    },
    {
      title: '业务模块',
      dataIndex: 'biz_name',
      key: 'biz_name',
      width: 130,
    },
    {
      title: '标签信息 / 分摊部门',
      key: 'tag_dept',
      width: 200,
      render: (_: unknown, r: RowData) => {
        const depts = Object.keys(r.dept_breakdown ?? {})
        const tagLabel = r.tag_value
          ? <span style={{ color: '#666', fontSize: 12 }}>{r.tag_value}</span>
          : null

        if (depts.length <= 1) {
          return (
            <span>
              {tagLabel}
              {depts[0] && <Tag color={DEPT_COLORS[depts[0]] ?? 'default'} style={{ marginLeft: 4, fontSize: 11 }}>{depts[0]}</Tag>}
            </span>
          )
        }

        // 多部门分摊：显示 tag + 各部门占比
        const lastMo = monthKeys[monthKeys.length - 1]
        const total = r.month_costs[lastMo] ?? 0
        const breakdown = depts.map(d => {
          const amt = r.dept_breakdown[d]?.[lastMo] ?? 0
          const pct = total > 0 ? ((amt / total) * 100).toFixed(0) : '0'
          return `${d}: ${pct}%`
        }).join(' / ')

        return (
          <Tooltip title={breakdown}>
            <span>
              {tagLabel}
              <span style={{ marginLeft: 4 }}>
                {depts.map(d => (
                  <Tag key={d} color={DEPT_COLORS[d] ?? 'default'} style={{ fontSize: 11, marginRight: 2 }}>{d}</Tag>
                ))}
              </span>
            </span>
          </Tooltip>
        )
      },
    },
    ...monthKeys.map(ym => ({
      title: ym,
      key: ym,
      width: 110,
      align: 'right' as const,
      render: (_: unknown, record: RowData) => {
        const v = record.month_costs[ym] ?? 0
        if (v < 0.005) return <span style={{ color: '#ccc' }}>-</span>
        return <span style={{ fontVariantNumeric: 'tabular-nums' }}>${v.toFixed(2)}</span>
      },
    })),
    {
      title: '较上月增加',
      dataIndex: 'mom_change',
      key: 'mom_change',
      width: 110,
      align: 'right' as const,
      render: (v: number) => {
        if (Math.abs(v) < 0.01) return <span style={{ color: '#ccc' }}>-</span>
        const color = v > 0 ? '#f5222d' : '#52c41a'
        const bg = v > 0 ? '#fff1f0' : '#f6ffed'
        return (
          <span style={{ color, background: bg, padding: '2px 6px', borderRadius: 4, fontSize: 12 }}>
            {v > 0 ? '+' : ''}${v.toFixed(2)}
          </span>
        )
      },
      sorter: (a: RowData, b: RowData) => a.mom_change - b.mom_change,
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select value={accountName} onChange={setAccountName} style={{ width: 120 }}
            options={ACCOUNTS.map(a => ({ label: a, value: a }))} />
          <Select value={months} onChange={setMonths} style={{ width: 120 }}
            options={[
              { label: '近3个月', value: 3 }, { label: '近4个月', value: 4 },
              { label: '近6个月', value: 6 }, { label: '近12个月', value: 12 },
            ]} />
          <Button icon={<SyncOutlined />} onClick={fetchData}>刷新</Button>
        </Space>
      </Card>

      {lastMonth && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card><Statistic title={`${lastMonth} 总费用`} value={totalLast} precision={2} prefix="$" /></Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title={`较 ${prevMonth} 环比`}
                value={Math.abs(totalLast - totalPrev)}
                precision={2}
                prefix={totalLast >= totalPrev ? '+$' : '-$'}
                valueStyle={{ color: totalLast >= totalPrev ? '#f5222d' : '#52c41a' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} showIcon closable onClose={() => setError(null)} />}

      <Card title={`费用明细 — ${accountName}账号`}>
        <Spin spinning={loading}>
          <Table<RowData>
            columns={columns}
            dataSource={rows}
            pagination={false}
            size="small"
            scroll={{ x: 900 }}
            bordered
          />
        </Spin>
      </Card>
    </div>
  )
}
