import { useState, useEffect } from 'react'
import {
  Table, Button, Modal, Form, Input, Select, Tag, Space,
  Typography, message, Tooltip, DatePicker
} from 'antd'
import { EditOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import client from '../api/client'

const { Text } = Typography

// -----------------------------------------------------------------------
// 静态规则数据（来自截图）
// -----------------------------------------------------------------------
interface RuleRow {
  key: string
  account: string
  bizGroup: string
  bizModule: string
  tagInfo: string
  ratio: string
  note: string
  editable?: boolean  // 是否允许编辑分摊比例
}

const RULES: RuleRow[] = [
  // 主业务 - SmartProduct
  { key: 'm-sp-1', account: '主业务', bizGroup: 'SmartProduct', bizModule: 'Nothing-x', tagInfo: 'nothing x', ratio: 'Smart:100%', note: '', editable: false },
  { key: 'm-sp-2', account: '主业务', bizGroup: 'SmartProduct', bizModule: 'xservice', tagInfo: 'xservice', ratio: 'Smart:100%', note: '', editable: false },
  { key: 'm-sp-3', account: '主业务', bizGroup: 'SmartProduct', bizModule: 'NothingOTA', tagInfo: 'NothingOTA', ratio: 'Smart:100%', note: '', editable: false },
  { key: 'm-sp-4', account: '主业务', bizGroup: 'SmartProduct', bizModule: 'TTS', tagInfo: 'TTS', ratio: 'Smart:100%', note: '语音转文字服务，Ear使用', editable: false },
  { key: 'm-sp-5', account: '主业务', bizGroup: 'SmartProduct', bizModule: 'Mimi', tagInfo: 'Mimi', ratio: 'Smart:100%', note: '耳机用户听力补偿算法，用户用APP来测试自己听力是否有损伤，由服务器计算补偿参数下发到耳机', editable: false },
  { key: 'm-sp-6', account: '主业务', bizGroup: 'SmartProduct', bizModule: '二维码服务', tagInfo: 'LinkJumping', ratio: 'Smart:100%', note: '耳机包装盒二维码，用于扫描下载Nothing-X', editable: false },
  // 主业务 - Common
  { key: 'm-c-1', account: '主业务', bizGroup: 'Common', bizModule: '埋点服务', tagInfo: 'DataCollection', ratio: 'Phone:Smart:销售=70%:20%:10%', note: '按使用方和使用频次分摊，Phone占大头，激活数销售集会使用，行为和品质数据Phone&Smart均使用', editable: true },
  { key: 'm-c-2', account: '主业务', bizGroup: 'Common', bizModule: '看板', tagInfo: 'BI', ratio: 'Phone:Smart:销售=40%:30%:30%', note: '按使用频次分摊', editable: true },
  { key: 'm-c-3', account: '主业务', bizGroup: 'Common', bizModule: '账号中心', tagInfo: 'NAC', ratio: 'Smart:Community:销售=33%:33%:33%', note: '账号来源：Nothing-X、社区、官网，三者均摊，各占1/3，其中官网归属到销售', editable: true },
  { key: 'm-c-4', account: '主业务', bizGroup: 'Common', bizModule: 'NewsReporter', tagInfo: 'NewsReporter', ratio: 'Phone:Smart=50%:50%', note: '近三个月费用连续翻倍，费用增加原因8月已有定论：Smart耳机和手表均支持服务，CDN流量翻倍', editable: true },
  { key: 'm-c-5', account: '主业务', bizGroup: 'Common', bizModule: 'Nacos', tagInfo: 'Nacos', ratio: 'AI:Smart:Phone=33.3%:50%:16.6%', note: '配置管理中心，用于服务配置下发。essential-space、nothing-x、feedback三者使用，建议各占1/3', editable: true },
  { key: 'm-c-6', account: '主业务', bizGroup: 'Common', bizModule: 'Feedback', tagInfo: 'Feedback', ratio: 'Phone:Smart=50%:50%', note: '用户反馈服务，Smart和Phone均使用，服务端难以统计，费用较小，按照各自占50%', editable: true },
  // 主业务 - Community
  { key: 'm-co-1', account: '主业务', bizGroup: 'Community', bizModule: '社区', tagInfo: 'Nothing Community', ratio: 'Community:100%', note: '', editable: false },
  // 主业务 - AI
  { key: 'm-ai-1', account: '主业务', bizGroup: 'AI', bizModule: 'essential-space', tagInfo: 'essential-space', ratio: 'AI:100%', note: '', editable: false },
  // 主业务 - Phone
  { key: 'm-p-1', account: '主业务', bizGroup: 'Phone', bizModule: 'cmf watch', tagInfo: 'Watch1', ratio: 'Phone:100%', note: '', editable: false },
  { key: 'm-p-2', account: '主业务', bizGroup: 'Phone', bizModule: '天气服务', tagInfo: 'NothingWeatherServer', ratio: 'Phone:Smart=9:1', note: '接口调用次数，手表有使用，追踪连续6天调用数据，Phone占比在87%负动，按9:1分摊，归于Phone', editable: true },
  { key: 'm-p-3', account: '主业务', bizGroup: 'Phone', bizModule: 'AI Wallpaper', tagInfo: 'Wallpaper', ratio: 'Phone:100%', note: '', editable: false },
  { key: 'm-p-4', account: '主业务', bizGroup: 'Phone', bizModule: 'BetaOTA', tagInfo: 'BetaOTA', ratio: 'Phone:100%', note: '', editable: false },
  { key: 'm-p-5', account: '主业务', bizGroup: 'Phone', bizModule: 'SharedWidget', tagInfo: 'SharedWidget', ratio: 'Phone:100%', note: '', editable: false },
  { key: 'm-p-6', account: '主业务', bizGroup: 'Phone', bizModule: '社区微件', tagInfo: 'CommunityWidget', ratio: 'Phone:100%', note: '', editable: false },
  { key: 'm-p-7', account: '主业务', bizGroup: 'Phone', bizModule: 'PushService', tagInfo: 'PushService', ratio: 'Phone:100%', note: '', editable: false },
  { key: 'm-p-8', account: '主业务', bizGroup: 'Phone', bizModule: '应用分类', tagInfo: 'APPClassification', ratio: 'Phone:100%', note: '', editable: false },
  { key: 'm-p-9', account: '主业务', bizGroup: 'Phone', bizModule: 'ShortLink', tagInfo: 'ShortLink', ratio: 'Phone:100%', note: '', editable: false },
  { key: 'm-p-10', account: '主业务', bizGroup: 'Phone', bizModule: 'Nothing-Preorder', tagInfo: 'Nothing-Preorder', ratio: 'Phone:100%', note: '', editable: false },
  { key: 'm-p-11', account: '主业务', bizGroup: 'Phone', bizModule: '问卷', tagInfo: 'Questionnaire', ratio: 'Phone:100%', note: '', editable: false },
  { key: 'm-p-12', account: '主业务', bizGroup: 'Phone', bizModule: 'Camera盲测', tagInfo: 'BlindTest', ratio: 'Phone:100%', note: '', editable: false },
  { key: 'm-p-13', account: '主业务', bizGroup: 'Phone', bizModule: 'IMEIServer', tagInfo: 'IMEI', ratio: 'Phone:100%', note: '', editable: false },
  { key: 'm-p-14', account: '主业务', bizGroup: 'Phone', bizModule: '生成式widgets', tagInfo: 'GenWidgets', ratio: 'Phone:100%', note: '', editable: false },
  // 主业务 - Public
  { key: 'm-pub-1', account: '主业务', bizGroup: 'Public', bizModule: 'Phone', tagInfo: 'Public分摊', ratio: 'Phone:100%', note: '3. EFS归属Nacos业务\n4. ECS/EKS: nothing-x、share-wiget、生成式wiget、essential-space四者均摊\n5. TTS实例：语音转文字服务，单独列出，计入Smart\n6. Athena&&Glue实例："看板"业务使用，计入BI看板\n7. ELB实例：Nothing-X使用的负载均衡服务，计入Nothing-X\n8. Mongodb实例：基础费用$2500由essential-space、Nothing-x、sharedwiget三项业务均摊，超出部分计入Nothing-X', editable: true },
  { key: 'm-pub-2', account: '主业务', bizGroup: 'Public', bizModule: 'SmartProduct', tagInfo: 'Public分摊', ratio: 'Smart:100%', note: '', editable: true },
  { key: 'm-pub-3', account: '主业务', bizGroup: 'Public', bizModule: 'IT', tagInfo: 'Public分摊', ratio: 'IT:100%', note: 'Software每月会部件知会各方实际使用金额', editable: true },
  { key: 'm-pub-4', account: '主业务', bizGroup: 'Public', bizModule: 'Community', tagInfo: 'Public分摊', ratio: 'Community:100%', note: '', editable: true },
  // 国内账号 - SmartProduct
  { key: 'cn-sp-1', account: '国内', bizGroup: 'SmartProduct', bizModule: 'Nothing-x中国区', tagInfo: 'NothingX', ratio: 'Smart:100%', note: '', editable: false },
  { key: 'cn-sp-2', account: '国内', bizGroup: 'SmartProduct', bizModule: 'Mimi', tagInfo: 'Mini', ratio: 'Smart:100%', note: '', editable: false },
  { key: 'cn-sp-3', account: '国内', bizGroup: 'SmartProduct', bizModule: '埋点服务', tagInfo: 'DataCollection', ratio: 'Smart:100%', note: '', editable: false },
  { key: 'cn-sp-4', account: '国内', bizGroup: 'SmartProduct', bizModule: 'Nothing-ota', tagInfo: 'OTA', ratio: 'Smart:100%', note: '', editable: false },
  { key: 'cn-sp-5', account: '国内', bizGroup: 'SmartProduct', bizModule: 'feedback', tagInfo: 'feedback', ratio: 'Smart:100%', note: '', editable: false },
  { key: 'cn-sp-6', account: '国内', bizGroup: 'SmartProduct', bizModule: '账号中心-中国区', tagInfo: 'NAC', ratio: 'Smart:100%', note: '', editable: false },
  { key: 'cn-sp-7', account: '国内', bizGroup: 'SmartProduct', bizModule: 'Common Cache', tagInfo: 'Common Cache', ratio: 'Smart:100%', note: '', editable: false },
  { key: 'cn-sp-8', account: '国内', bizGroup: 'SmartProduct', bizModule: '日志服务', tagInfo: 'LogCollect', ratio: 'Smart:100%', note: '', editable: false },
  { key: 'cn-sp-9', account: '国内', bizGroup: 'SmartProduct', bizModule: 'Nacos', tagInfo: 'Nacos', ratio: 'Smart:100%', note: '', editable: false },
  { key: 'cn-sp-10', account: '国内', bizGroup: 'SmartProduct', bizModule: '其他', tagInfo: '-', ratio: 'Smart:100%', note: '', editable: false },
]

const GROUP_COLORS: Record<string, string> = {
  SmartProduct: 'orange', Common: 'green', Community: 'blue',
  AI: 'purple', Phone: 'gold', Public: 'cyan',
}
const GROUP_BG: Record<string, string> = {
  SmartProduct: '#fff7e6', Common: '#f6ffed', Community: '#e6f7ff',
  AI: '#f9f0ff', Phone: '#fffbe6', Public: '#e6fffb',
}

// -----------------------------------------------------------------------
// 编辑弹窗
// -----------------------------------------------------------------------
interface EditState {
  row: RuleRow
  ratio: string
  note: string
}

export default function RulesManagement() {
  const [editState, setEditState] = useState<EditState | null>(null)
  const [saving, setSaving] = useState(false)
  const [recalcVisible, setRecalcVisible] = useState(false)
  const [recalcRow, setRecalcRow] = useState<RuleRow | null>(null)
  const [recalcDates, setRecalcDates] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
  const [recalcLoading, setRecalcLoading] = useState(false)
  const [rules, setRules] = useState<RuleRow[]>(RULES)

  // 页面加载时从后端读取 DB 规则，覆盖硬编码默认值
  useEffect(() => {
    client.get('/rules').then(({ data }) => {
      if (!data || data.length === 0) return
      setRules(prev => prev.map(row => {
        const tagForMatch = row.tagInfo === 'Public分摊' ? null : row.tagInfo
        const dbRule = data.find((r: { account_name: string; tag_value: string | null; business_module: string | null }) =>
          r.account_name === row.account && r.tag_value === tagForMatch && r.business_module === row.bizModule
        )
        if (!dbRule) return row
        const updated = { ...row }
        // 从 special_config 读取 note 和 ratio 显示文本
        if (dbRule.special_config?.note) updated.note = dbRule.special_config.note
        if (dbRule.special_config?.ratio_display) {
          updated.ratio = dbRule.special_config.ratio_display
        } else if (dbRule.ratios) {
          const entries = Object.entries(dbRule.ratios as Record<string, number>)
          updated.ratio = entries.length === 1
            ? `${entries[0][0]}:${Math.round(entries[0][1] * 100)}%`
            : entries.map(([k]) => k).join(':') + '=' + entries.map(([, v]) => `${Math.round(v * 100)}%`).join(':')
        }
        return updated
      }))
    }).catch(() => { /* 静默失败 */ })
  }, [])

  // 按账号分组
  const accounts = ['主业务', '国内']

  const handleSave = async () => {
    if (!editState) return
    const ratios = parseRatioString(editState.ratio)
    if (!ratios) {
      message.error('分摊比例格式错误，请使用格式如：Phone:Smart:销售=70%:20%:10%')
      return
    }
    setSaving(true)
    try {
      await client.post('/rules', {
        account_name: editState.row.account,
        tag_value: editState.row.tagInfo === 'Public分摊' ? null : editState.row.tagInfo,
        rule_type: 'shared',
        ratios,
        business_module: editState.row.bizModule,
        department: null,
        is_active: true,
        special_config: {
          ratio_display: editState.ratio,
          note: editState.note,
        },
      })
      // 更新本地数据
      setRules(prev => prev.map(r =>
        r.key === editState.row.key
          ? { ...r, ratio: editState.ratio, note: editState.note }
          : r
      ))
      message.success('规则已保存')
      setEditState(null)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err?.response?.data?.detail || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleRecalc = async () => {
    if (!recalcRow || !recalcDates) return
    setRecalcLoading(true)
    try {
      await client.post('/sync/trigger', null, {
        params: {
          start_date: recalcDates[0].format('YYYY-MM-DD'),
          end_date: recalcDates[1].format('YYYY-MM-DD'),
        }
      })
      message.success('重算任务已触发')
      setRecalcVisible(false)
    } catch {
      message.error('触发失败')
    } finally {
      setRecalcLoading(false)
    }
  }

  // 计算每个 bizGroup 的行数（用于合并单元格）
  const buildSpanMap = (rows: RuleRow[]) => {
    const map: Record<string, { start: number; count: number }> = {}
    rows.forEach((r, i) => {
      if (!map[r.bizGroup]) map[r.bizGroup] = { start: i, count: 0 }
      map[r.bizGroup].count++
    })
    return map
  }

  const columns = (rows: RuleRow[]): ColumnsType<RuleRow> => {
    const spanMap = buildSpanMap(rows)
    return [
      {
        title: '业务归属',
        dataIndex: 'bizGroup',
        key: 'bizGroup',
        width: 100,
        onCell: (record, index) => {
          const info = spanMap[record.bizGroup]
          if (index === info?.start) return { rowSpan: info.count, style: { background: GROUP_BG[record.bizGroup], verticalAlign: 'middle', textAlign: 'center' } }
          return { rowSpan: 0 }
        },
        render: (g: string) => <Tag color={GROUP_COLORS[g]} style={{ fontWeight: 600 }}>{g}</Tag>,
      },
      {
        title: '业务模块',
        dataIndex: 'bizModule',
        key: 'bizModule',
        width: 120,
      },
      {
        title: '标签信息',
        dataIndex: 'tagInfo',
        key: 'tagInfo',
        width: 160,
        render: (v: string) => <Text style={{ fontSize: 12, color: '#555' }}>{v}</Text>,
      },
      {
        title: '分摊比例',
        dataIndex: 'ratio',
        key: 'ratio',
        width: 220,
        render: (v: string) => <Text style={{ fontSize: 12 }}>{v}</Text>,
      },
      {
        title: '费用分摊说明',
        dataIndex: 'note',
        key: 'note',
        render: (v: string) => v ? (
          <Text style={{ fontSize: 12, color: '#666', whiteSpace: 'pre-line' }}>{v}</Text>
        ) : null,
      },
      {
        title: '操作',
        key: 'actions',
        width: 100,
        render: (_: unknown, record: RuleRow) => (
          <Space size={4}>
            {record.editable && (
              <Tooltip title="编辑分摊比例">
                <Button
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => setEditState({ row: record, ratio: record.ratio, note: record.note })}
                />
              </Tooltip>
            )}
            <Tooltip title="触发重算">
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => { setRecalcRow(record); setRecalcDates(null); setRecalcVisible(true) }}
              />
            </Tooltip>
          </Space>
        ),
      },
    ]
  }

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>分摊规则</Typography.Title>

      {accounts.map(account => {
        const accountRows = rules.filter(r => r.account === account)
        return (
          <div key={account} style={{ marginBottom: 32 }}>
            <Typography.Title level={5} style={{ marginBottom: 8 }}>
              <Tag color="blue">{account}账号</Tag>
            </Typography.Title>
            <Table<RuleRow>
              rowKey="key"
              dataSource={accountRows}
              columns={columns(accountRows)}
              pagination={false}
              size="small"
              bordered
              scroll={{ x: 900 }}
            />
          </div>
        )
      })}

      {/* 编辑弹窗 */}
      <Modal
        title={`编辑分摊规则 — ${editState?.row.bizModule}`}
        open={!!editState}
        onCancel={() => setEditState(null)}
        onOk={handleSave}
        okText="保存"
        cancelText="取消"
        confirmLoading={saving}
      >
        {editState && (
          <Form layout="vertical">
            <Form.Item label="业务模块">
              <Input value={editState.row.bizModule} disabled />
            </Form.Item>
            <Form.Item label="标签信息">
              <Input value={editState.row.tagInfo} disabled />
            </Form.Item>
            <Form.Item label="分摊比例" extra="格式示例：Phone:Smart:销售=70%:20%:10%">
              <Input
                value={editState.ratio}
                onChange={e => setEditState({ ...editState, ratio: e.target.value })}
              />
            </Form.Item>
            <Form.Item label="费用分摊说明">
              <Input.TextArea
                rows={3}
                value={editState.note}
                onChange={e => setEditState({ ...editState, note: e.target.value })}
              />
            </Form.Item>
          </Form>
        )}
      </Modal>

      {/* 重算弹窗 */}
      <Modal
        title={`触发历史重算 — ${recalcRow?.bizModule}`}
        open={recalcVisible}
        onCancel={() => setRecalcVisible(false)}
        onOk={handleRecalc}
        okText="确认重算"
        cancelText="取消"
        okButtonProps={{ disabled: !recalcDates }}
        confirmLoading={recalcLoading}
      >
        <Form layout="vertical">
          <Form.Item label="选择日期范围" required>
            <DatePicker.RangePicker
              style={{ width: '100%' }}
              onChange={(dates) => setRecalcDates(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

// 解析比例字符串并归一化到总和 1.0
function parseRatioString(ratio: string): Record<string, number> | null {
  try {
    const eqIdx = ratio.indexOf('=')
    let depts: string[], pcts: number[]
    if (eqIdx === -1) {
      // "Smart:100%" 格式
      const parts = ratio.split(':')
      if (parts.length === 2) {
        depts = [parts[0].trim()]
        pcts = [parseFloat(parts[1]) / 100]
      } else return null
    } else {
      depts = ratio.slice(0, eqIdx).split(':').map(s => s.trim())
      pcts = ratio.slice(eqIdx + 1).split(':').map(s => parseFloat(s) / 100)
    }
    if (depts.length !== pcts.length) return null
    const total = pcts.reduce((a, b) => a + b, 0)
    if (total <= 0) return null
    const result: Record<string, number> = {}
    depts.forEach((d, i) => { result[d] = Math.round(pcts[i] / total * 10000) / 10000 })
    // 修正舍入误差
    const keys = Object.keys(result)
    const sum = Object.values(result).reduce((a, b) => a + b, 0)
    result[keys[0]] = Math.round((result[keys[0]] + (1 - sum)) * 10000) / 10000
    return result
  } catch {
    return null
  }
}
