import { useState, useEffect } from 'react'
import { Table, Card, Select, Space, Button, Tag, Spin, Alert, Statistic, Row, Col, Tooltip, Modal } from 'antd'
import { SyncOutlined, QuestionCircleOutlined, TagsOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import client from '../api/client'

const ACCOUNTS = ['主业务', 'PLM', '国内']

const GROUP_ORDER = ['共用', 'SmartProduct', 'Community', 'AI', 'Phone', 'Public', '其他']
const GROUP_COLORS: Record<string, string> = {
  '共用': 'green', 'SmartProduct': 'orange', 'Community': 'blue',
  'AI': 'purple', 'Phone': 'gold', 'Public': 'cyan', '其他': 'default',
}
const GROUP_BG: Record<string, string> = {
  '共用': 'rgba(82, 196, 26, 0.1)', 'SmartProduct': 'rgba(250, 140, 22, 0.1)', 'Community': 'rgba(24, 144, 255, 0.1)',
  'AI': 'rgba(114, 46, 209, 0.1)', 'Phone': 'rgba(250, 173, 20, 0.1)', 'Public': 'rgba(19, 194, 194, 0.1)', '其他': 'rgba(255, 255, 255, 0.05)',
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
  const [publicData, setPublicData] = useState<RowData[]>([])
  const [unclassifiedData, setUnclassifiedData] = useState<RowData[]>([])
  const [publicVisible, setPublicVisible] = useState(false)
  const [unclassifiedVisible, setUnclassifiedVisible] = useState(false)

  useEffect(() => { fetchData() }, [accountName, months])  // eslint-disable-line react-hooks/exhaustive-deps

  async function fetchData() {
    setLoading(true)
    setError(null)
    try {
      const res = await client.get('/costs/business-summary', {
        params: { account_name: accountName, months },
      })
      const { months: mks, data, public_data, unclassified_data } = res.data
      setMonthKeys(mks)
      setRows(data.map((r: RowData, i: number) => ({ ...r, key: String(i) })))
      setPublicData((public_data || []).map((r: RowData, i: number) => ({ ...r, key: `pub-${i}` })))
      setUnclassifiedData((unclassified_data || []).map((r: RowData, i: number) => ({ ...r, key: `unc-${i}` })))
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
        if (Math.abs(v) < 0.01) return <span style={{ color: 'var(--text-secondary)' }}>-</span>
        const color = v > 0 ? 'var(--danger-color)' : 'var(--success-color)'
        const bg = v > 0 ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)'
        return (
          <span style={{ color, background: bg, padding: '4px 8px', borderRadius: 6, fontSize: 12, fontWeight: 500 }}>
            {v > 0 ? '+' : ''}${v.toFixed(2)}
          </span>
        )
      },
      sorter: (a: RowData, b: RowData) => a.mom_change - b.mom_change,
    },
  ]

  return (
    <div style={{ padding: 24, paddingBottom: 48 }}>
      <Card className="glass-panel" style={{ marginBottom: 24, border: 'none' }} bodyStyle={{ padding: '16px 24px' }}>
        <Space wrap size="large">
          <Select value={accountName} onChange={setAccountName} style={{ width: 140 }}
            options={ACCOUNTS.map(a => ({ label: a, value: a }))} size="large" bordered={false} className="glass-select" />
          <Select value={months} onChange={setMonths} style={{ width: 140 }}
            options={[
              { label: '近3个月', value: 3 }, { label: '近4个月', value: 4 },
              { label: '近6个月', value: 6 }, { label: '近12个月', value: 12 },
            ]} size="large" bordered={false} className="glass-select" />
          <Button type="primary" icon={<SyncOutlined />} onClick={fetchData} className="btn-gradient" size="large">刷新数据</Button>
        </Space>
      </Card>

      {lastMonth && (
        <Row gutter={24} style={{ marginBottom: 24 }}>
          <Col span={8}>
            <Card className="glass-panel" style={{ border: 'none' }} bodyStyle={{ padding: '24px' }}>
              <Statistic title={`${lastMonth} 总费用`} value={totalLast} precision={2} prefix="$" valueStyle={{ color: 'var(--text-primary)', fontWeight: 600 }} />
            </Card>
          </Col>
          <Col span={8}>
            <Card className="glass-panel" style={{ border: 'none' }} bodyStyle={{ padding: '24px' }}>
              <Statistic
                title={`较 ${prevMonth} 环比`}
                value={Math.abs(totalLast - totalPrev)}
                precision={2}
                prefix={totalLast >= totalPrev ? '+$' : '-$'}
                valueStyle={{ color: totalLast >= totalPrev ? 'var(--danger-color)' : 'var(--success-color)', fontWeight: 600 }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {error && <Alert type="error" message={error} style={{ marginBottom: 16 }} showIcon closable onClose={() => setError(null)} />}

      <Card className="glass-panel" title={<span style={{ fontSize: '18px', fontWeight: 600 }}>费用明细 — {accountName}账号</span>} style={{ border: 'none' }}>
        <Spin spinning={loading}>
          {/* 两个入口按钮，位于表格上方 */}
          <div style={{ display: 'flex', gap: 24, marginBottom: 24 }}>
            <Button
              icon={<QuestionCircleOutlined />}
              onClick={() => setPublicVisible(true)}
              className="btn-gradient"
              style={{ flex: 1, height: 56, fontSize: '16px' }}
            >
              Public 分摊 (未分类) — 无 Product Tag 资源
              {publicData.length > 0 && monthKeys.length > 0 && (
                <Tag color="rgba(255,255,255,0.2)" style={{ marginLeft: 12, border: 'none', color: 'white', fontSize: '14px', padding: '4px 8px' }}>
                  ${publicData.reduce((s, r) => s + (r.month_costs[monthKeys[monthKeys.length - 1]] ?? 0), 0).toFixed(0)}
                </Tag>
              )}
            </Button>
            <Button
              icon={<TagsOutlined />}
              onClick={() => setUnclassifiedVisible(true)}
              className="btn-glass"
              style={{ flex: 1, height: 56, fontSize: '16px' }}
            >
              已打 Tag 未确定归属
              {unclassifiedData.length > 0 && monthKeys.length > 0 && (
                <Tag color="var(--accent-color)" style={{ marginLeft: 12, border: 'none', fontSize: '14px', padding: '4px 8px' }}>
                  {unclassifiedData.length} 项 / ${unclassifiedData.reduce((s, r) => s + (r.month_costs[monthKeys[monthKeys.length - 1]] ?? 0), 0).toFixed(0)}
                </Tag>
              )}
            </Button>
          </div>
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

      <Modal
        title="Public分摊(未分类) — 无 Product Tag 资源"
        open={publicVisible}
        onCancel={() => setPublicVisible(false)}
        footer={null}
        width={1000}
      >
        <Table<RowData & { allocation_desc?: string }>
          columns={[
            { title: '服务类型', dataIndex: 'biz_name', key: 'biz_name', width: 250 },
            ...monthKeys.map(ym => ({
              title: ym, key: ym, width: 110, align: 'right' as const,
              render: (_: unknown, record: RowData) => {
                const v = record.month_costs[ym] ?? 0
                return v > 0.005 ? `$${v.toFixed(2)}` : '-'
              },
            })),
            {
              title: '较上月', dataIndex: 'mom_change', key: 'mom_change', width: 100, align: 'right' as const,
              render: (v: number) => {
                if (Math.abs(v) < 0.01) return '-'
                const color = v > 0 ? '#f5222d' : '#52c41a'
                return <span style={{ color }}>{v > 0 ? '+' : ''}${v.toFixed(2)}</span>
              },
            },
            {
              title: '费用分摊说明', dataIndex: 'allocation_desc', key: 'allocation_desc', width: 280,
              render: (v: string | undefined) => <span style={{ fontSize: 12 }}>{v ?? '-'}</span>
            },
          ]}
          dataSource={publicData}
          pagination={false}
          size="small"
          bordered
          summary={() => {
            const totals: Record<string, number> = {}
            monthKeys.forEach(ym => { totals[ym] = publicData.reduce((s, r) => s + (r.month_costs[ym] ?? 0), 0) })
            return (
              <Table.Summary.Row>
                <Table.Summary.Cell index={0}><strong>总计</strong></Table.Summary.Cell>
                {monthKeys.map((ym, i) => (
                  <Table.Summary.Cell key={ym} index={i + 1} align="right">
                    <strong>${totals[ym].toFixed(2)}</strong>
                  </Table.Summary.Cell>
                ))}
                <Table.Summary.Cell index={monthKeys.length + 1} />
              </Table.Summary.Row>
            )
          }}
        />
      </Modal>

      {/* 已打Tag未确定归属 弹窗 */}
      <Modal
        title="已打Tag未确定归属 — 有 Product Tag 但未匹配已知业务"
        open={unclassifiedVisible}
        onCancel={() => setUnclassifiedVisible(false)}
        footer={null}
        width={1000}
      >
        <Table<RowData>
          columns={[
            { title: '原始 Tag', dataIndex: 'tag_value', key: 'tag_value', width: 200,
              render: (v: string | null) => <span style={{ fontSize: 12 }}>{v ?? '-'}</span> },
            { title: '部门', dataIndex: 'department', key: 'department', width: 80 },
            ...monthKeys.map(ym => ({
              title: ym, key: ym, width: 110, align: 'right' as const,
              render: (_: unknown, record: RowData) => {
                const v = record.month_costs[ym] ?? 0
                return v > 0.005 ? `$${v.toFixed(2)}` : '-'
              },
            })),
            {
              title: '较上月', dataIndex: 'mom_change', key: 'mom_change', width: 100, align: 'right' as const,
              render: (v: number) => {
                if (Math.abs(v) < 0.01) return '-'
                const color = v > 0 ? '#f5222d' : '#52c41a'
                return <span style={{ color }}>{v > 0 ? '+' : ''}${v.toFixed(2)}</span>
              },
            },
          ]}
          dataSource={unclassifiedData}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          size="small"
          bordered
          summary={() => {
            const totals: Record<string, number> = {}
            monthKeys.forEach(ym => { totals[ym] = unclassifiedData.reduce((s, r) => s + (r.month_costs[ym] ?? 0), 0) })
            return (
              <Table.Summary.Row>
                <Table.Summary.Cell index={0} colSpan={2}><strong>合计</strong></Table.Summary.Cell>
                {monthKeys.map((ym, i) => (
                  <Table.Summary.Cell key={ym} index={i + 2} align="right">
                    <strong>${totals[ym].toFixed(2)}</strong>
                  </Table.Summary.Cell>
                ))}
                <Table.Summary.Cell index={monthKeys.length + 2} />
              </Table.Summary.Row>
            )
          }}
        />
      </Modal>
    </div>
  )
}
