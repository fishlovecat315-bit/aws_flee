import { Layout as AntLayout, Menu } from 'antd'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { DashboardOutlined, DollarOutlined, SettingOutlined, BellOutlined, KeyOutlined } from '@ant-design/icons'

const { Header, Sider, Content } = AntLayout

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    { key: '/dashboard', icon: <DashboardOutlined />, label: '费用总览' },
    { key: '/costs', icon: <DollarOutlined />, label: '费用明细' },
    { key: '/rules', icon: <SettingOutlined />, label: '分摊规则' },
    { key: '/alerts', icon: <BellOutlined />, label: '预警设置' },
    { key: '/aws-settings', icon: <KeyOutlined />, label: 'AWS 凭证' },
  ]

  return (
    <AntLayout style={{ minHeight: '100vh', background: 'transparent' }}>
      <Header className="glass-header" style={{ color: 'white', fontSize: 18, fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>
        <span style={{ background: 'var(--accent-gradient)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', fontSize: '22px' }}>Nothing</span>
        <span style={{ marginLeft: 8, opacity: 0.9 }}>AWS 费用统计</span>
      </Header>
      <AntLayout style={{ background: 'transparent' }}>
        <Sider width={220} className="glass-sider">
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ height: '100%', paddingTop: 16 }}
          />
        </Sider>
        <Content className="main-content">
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
