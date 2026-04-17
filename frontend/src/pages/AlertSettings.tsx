import { useEffect, useState } from 'react'
import {
  Table, InputNumber, Switch, Button, message, Typography, Space, Tag
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import client from '../api/client'
import type { AlertThreshold } from '../types'

const DEPARTMENTS = ['销售', 'AI', 'Smart', 'Phone', 'IT', 'Community']

interface DeptRow {
  department: string
  monthly_threshold_usd: number
  is_active: boolean
  id?: number
  saving: boolean
  saved: boolean
  error: string
}

function buildRows(thresholds: AlertThreshold[]): DeptRow[] {
  return DEPARTMENTS.map(dept => {
    const found = thresholds.find(t => t.department === dept)
    return {
      department: dept,
      monthly_threshold_usd: found ? found.monthly_threshold_usd : 0,
      is_active: found ? found.is_active : true,
      id: found?.id,
      saving: false,
      saved: false,
      error: '',
    }
  })
}

export default function AlertSettings() {
  const [rows, setRows] = useState<DeptRow[]>(DEPARTMENTS.map(dept => ({
    department: dept,
    monthly_threshold_usd: 0,
    is_active: true,
    saving: false,
    saved: false,
    error: '',
  })))
  const [loading, setLoading] = useState(false)

  const fetchThresholds = async () => {
    setLoading(true)
    try {
      const res = await client.get<AlertThreshold[]>('/alerts/thresholds')
      setRows(buildRows(res.data))
    } catch {
      message.error('获取预警阈值失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchThresholds() }, [])

  const updateRow = (dept: string, patch: Partial<DeptRow>) => {
    setRows((prev: DeptRow[]) => prev.map((r: DeptRow) => r.department === dept ? { ...r, ...patch } : r))
  }

  const handleSave = async (row: DeptRow) => {
    updateRow(row.department, { saving: true, saved: false, error: '' })
    try {
      await client.put(`/alerts/thresholds/${encodeURIComponent(row.department)}`, {
        monthly_threshold_usd: row.monthly_threshold_usd,
        is_active: row.is_active,
      })
      updateRow(row.department, { saving: false, saved: true })
      message.success(`${row.department} 阈值已保存`)
    } catch {
      updateRow(row.department, { saving: false, error: '保存失败' })
      message.error(`${row.department} 保存失败`)
    }
  }

  const columns: ColumnsType<DeptRow> = [
    {
      title: '业务部门',
      dataIndex: 'department',
      key: 'department',
      width: 120,
      render: (v: string) => <Typography.Text strong>{v}</Typography.Text>,
    },
    {
      title: '月度阈值（USD）',
      dataIndex: 'monthly_threshold_usd',
      key: 'monthly_threshold_usd',
      width: 200,
      render: (_: number, record: DeptRow) => (
        <InputNumber
          min={0}
          precision={2}
          style={{ width: 160 }}
          value={record.monthly_threshold_usd}
          prefix="$"
          onChange={(val: number | null) =>
            updateRow(record.department, { monthly_threshold_usd: val ?? 0, saved: false })
          }
        />
      ),
    },
    {
      title: '启用预警',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (_: boolean, record: DeptRow) => (
        <Switch
          checked={record.is_active}
          onChange={(checked: boolean) =>
            updateRow(record.department, { is_active: checked, saved: false })
          }
        />
      ),
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_: unknown, record: DeptRow) => {
        if (record.error) return <Tag color="error">保存失败</Tag>
        if (record.saved) return <Tag color="success">已保存</Tag>
        return null
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: DeptRow) => (
        <Space>
          <Button
            type="primary"
            size="small"
            loading={record.saving}
            onClick={() => handleSave(record)}
          >
            保存
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>预警设置</Typography.Title>
      <Typography.Paragraph type="secondary">
        为各业务部门设置月度费用预警阈值，超出阈值时将发送钉钉通知。
      </Typography.Paragraph>
      <Table<DeptRow>
        rowKey="department"
        loading={loading}
        dataSource={rows}
        columns={columns}
        pagination={false}
        size="middle"
        bordered
      />
    </div>
  )
}
