import { Card, Tabs, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { SummaryItem, SummaryResponse } from '../types'

interface CostSummaryTableProps {
  summary: SummaryResponse
}

function makeColumns(nameKey: keyof SummaryItem, nameLabel: string): ColumnsType<SummaryItem> {
  return [
    {
      title: nameLabel,
      dataIndex: nameKey as string,
      key: 'name',
      render: (v: string | null) => v ?? '(未标记)',
    },
    {
      title: '总费用 (USD)',
      dataIndex: 'total_amount',
      key: 'total_amount',
      render: (v: number) => `$${Number(v).toFixed(2)}`,
      sorter: (a: SummaryItem, b: SummaryItem) => a.total_amount - b.total_amount,
      defaultSortOrder: 'descend',
    },
  ]
}

export default function CostSummaryTable({ summary }: CostSummaryTableProps) {
  const deptColumns = makeColumns('department', '部门')
  const accountColumns = makeColumns('account_name', '账号')
  const tagColumns = makeColumns('tag_value', 'Tag 值')

  const tableProps = {
    size: 'small' as const,
    pagination: false as const,
  }

  const items = [
    {
      key: 'department',
      label: '按部门',
      children: (
        <Table<SummaryItem>
          {...tableProps}
          rowKey={(r) => r.department ?? ''}
          columns={deptColumns}
          dataSource={summary.by_department}
        />
      ),
    },
    {
      key: 'account',
      label: '按账号',
      children: (
        <Table<SummaryItem>
          {...tableProps}
          rowKey={(r) => r.account_name ?? ''}
          columns={accountColumns}
          dataSource={summary.by_account}
        />
      ),
    },
    {
      key: 'tag',
      label: '按 Tag',
      children: (
        <Table<SummaryItem>
          {...tableProps}
          rowKey={(r) => r.tag_value ?? '(未标记)'}
          columns={tagColumns}
          dataSource={summary.by_tag}
        />
      ),
    },
  ]

  return (
    <Card title="费用汇总" style={{ marginBottom: 16 }}>
      <Tabs items={items} />
    </Card>
  )
}
