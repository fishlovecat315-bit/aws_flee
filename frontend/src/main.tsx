import React from 'react'
import ReactDOM from 'react-dom/client'
import { ConfigProvider, theme } from 'antd'
import './index.css'
import App from './App'
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider theme={{ algorithm: theme.darkAlgorithm, token: { colorBgBase: '#0b0f19', fontFamily: 'Inter, sans-serif' } }}>
      <App />
    </ConfigProvider>
  </React.StrictMode>
)
