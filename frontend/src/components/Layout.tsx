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
    <AntLayout style={{ minHeight: '100vh' }}>
      <Header style={{ color: 'white', fontSize: 18, fontWeight: 'bold' }}>
        Nothing AWS 费用统计平台
      </Header>
      <AntLayout>
        <Sider width={200}>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ height: '100%' }}
          />
        </Sider>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
