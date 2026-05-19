import { Layout, Menu, Typography } from "antd";
import { Activity, Bell, Server } from "lucide-react";
import { useState } from "react";
import Dashboard from "./pages/Dashboard";
import NotificationDetail from "./pages/NotificationDetail";
import Notifications from "./pages/Notifications";
import Providers from "./pages/Providers";

const { Header, Content, Sider } = Layout;

type Page = "dashboard" | "providers" | "notifications";

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [selectedNotificationId, setSelectedNotificationId] = useState<string | null>(null);

  return (
    <Layout className="app-shell">
      <Sider width={232} className="app-sider">
        <Typography.Title level={4} className="brand">
          Notification Ops
        </Typography.Title>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[page]}
          onClick={({ key }) => {
            setPage(key as Page);
            setSelectedNotificationId(null);
          }}
          items={[
            { key: "dashboard", icon: <Activity size={16} />, label: "Dashboard" },
            { key: "providers", icon: <Server size={16} />, label: "Providers" },
            { key: "notifications", icon: <Bell size={16} />, label: "Notifications" }
          ]}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <Typography.Text strong>Internal API notification delivery platform</Typography.Text>
        </Header>
        <Content className="app-content">
          {selectedNotificationId ? (
            <NotificationDetail id={selectedNotificationId} onBack={() => setSelectedNotificationId(null)} />
          ) : page === "dashboard" ? (
            <Dashboard />
          ) : page === "providers" ? (
            <Providers />
          ) : (
            <Notifications onOpen={setSelectedNotificationId} />
          )}
        </Content>
      </Layout>
    </Layout>
  );
}

