import { useEffect, useState } from 'react'
import { Form, Input, Button, Card, message, Tag, Space, Divider, Badge } from 'antd'
import { CheckCircleOutlined, ExclamationCircleOutlined, SaveOutlined } from '@ant-design/icons'
import type { FormInstance } from 'antd'
import client from '../api/client'

interface AccountCredential {
  access_key_id: string
  secret_access_key: string
  region: string
  account_id: string
  is_configured?: boolean
}

interface AllCredentials {
  plm: AccountCredential
  main: AccountCredential
  cn: AccountCredential
}

type AccountKey = 'plm' | 'main' | 'cn'

interface AccountCardProps {
  accountKey: AccountKey
  label: string
  color: string
  form: FormInstance
  loading: boolean
  saving: boolean
  configured: boolean
  onSave: (accountKey: AccountKey, values: AccountCredential) => Promise<void>
}

function AccountCard({ accountKey, label, color, form, loading, saving, configured, onSave }: AccountCardProps) {
  return (
    <Card
      loading={loading}
      style={{ marginBottom: 24 }}
      title={
        <Space>
          <Tag color={color}>{label}</Tag>
          {configured
            ? <Badge status="success" text={<span style={{ color: '#52c41a', fontSize: 12 }}><CheckCircleOutlined /> 已配置</span>} />
            : <Badge status="warning" text={<span style={{ color: '#faad14', fontSize: 12 }}><ExclamationCircleOutlined /> 未配置</span>} />
          }
        </Space>
      }
      extra={
        <Button
          type="primary"
          size="small"
          icon={<SaveOutlined />}
          loading={saving}
          onClick={() => form.submit()}
        >
          保存
        </Button>
      }
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={(values) => onSave(accountKey, values as AccountCredential)}
      >
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <Form.Item
            label="Access Key ID"
            name="access_key_id"
            rules={[{ required: true, message: '请输入 Access Key ID' }]}
          >
            <Input placeholder="AKIA..." />
          </Form.Item>

          <Form.Item
            label="Secret Access Key"
            name="secret_access_key"
            rules={[{ required: true, message: '请输入 Secret Access Key' }]}
            extra={configured ? '已保存，重新输入将覆盖' : undefined}
          >
            <Input.Password placeholder="Secret Access Key" />
          </Form.Item>

          <Form.Item
            label="Region"
            name="region"
            rules={[{ required: true }]}
          >
            <Input placeholder="us-east-1" />
          </Form.Item>

          <Form.Item
            label="Account ID"
            name="account_id"
            rules={[{ required: true, message: '请输入 Account ID' }]}
          >
            <Input placeholder="12位数字账号 ID" maxLength={12} />
          </Form.Item>
        </div>
      </Form>
    </Card>
  )
}

export default function AwsSettings() {
  const [plmForm] = Form.useForm()
  const [mainForm] = Form.useForm()
  const [cnForm] = Form.useForm()

  const formMap: Record<AccountKey, FormInstance> = { plm: plmForm, main: mainForm, cn: cnForm }

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState<AccountKey | null>(null)
  const [configured, setConfigured] = useState<Record<AccountKey, boolean>>({
    plm: false, main: false, cn: false,
  })

  useEffect(() => {
    client.get<AllCredentials>('/settings/aws')
      .then(({ data }) => {
        const keys: AccountKey[] = ['plm', 'main', 'cn']
        keys.forEach((key) => {
          const cred = data[key]
          formMap[key].setFieldsValue({
            access_key_id: cred.access_key_id,
            secret_access_key: '',
            region: cred.region || 'us-east-1',
            account_id: cred.account_id,
          })
        })
        setConfigured({
          plm: data.plm.is_configured ?? false,
          main: data.main.is_configured ?? false,
          cn: data.cn.is_configured ?? false,
        })
      })
      .catch(() => message.error('加载配置失败'))
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const onSave = async (accountKey: AccountKey, values: AccountCredential) => {
    setSaving(accountKey)
    try {
      await client.put(`/settings/aws/${accountKey}`, values)
      const labels: Record<AccountKey, string> = { plm: 'PLM', main: '主业务', cn: '国内' }
      message.success(`${labels[accountKey]} 账号凭证已保存`)
      setConfigured(prev => ({ ...prev, [accountKey]: true }))
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      message.error(err?.response?.data?.detail || '保存失败')
    } finally {
      setSaving(null)
    }
  }

  const ACCOUNT_CONFIG: { key: AccountKey; label: string; color: string }[] = [
    { key: 'plm', label: 'PLM', color: 'blue' },
    { key: 'main', label: '主业务', color: 'green' },
    { key: 'cn', label: '国内', color: 'orange' },
  ]

  return (
    <div style={{ padding: 24, maxWidth: 800 }}>
      <h2 style={{ marginBottom: 8 }}>AWS 账号凭证配置</h2>
      <p style={{ color: '#888', marginBottom: 24 }}>
        三个子账号各自独立，分别配置 Access Key、Secret Key、Region 和 Account ID。
      </p>
      <Divider />
      {ACCOUNT_CONFIG.map(({ key, label, color }) => (
        <AccountCard
          key={key}
          accountKey={key}
          label={label}
          color={color}
          form={formMap[key]}
          loading={loading}
          saving={saving === key}
          configured={configured[key]}
          onSave={onSave}
        />
      ))}
    </div>
  )
}
