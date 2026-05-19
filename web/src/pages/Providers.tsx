import { Button, Card, Space, Table, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { getProviders, pauseProvider, Provider, resumeProvider } from "../api";

export default function Providers() {
  const [providers, setProviders] = useState<Provider[]>([]);

  const load = () => getProviders().then(setProviders);

  useEffect(() => {
    load();
  }, []);

  async function toggle(provider: Provider) {
    if (provider.paused) {
      await resumeProvider(provider.provider_code);
      message.success("Provider resumed");
    } else {
      await pauseProvider(provider.provider_code);
      message.success("Provider paused");
    }
    await load();
  }

  return (
    <Card>
      <Typography.Title level={3}>Providers</Typography.Title>
      <Table
        rowKey="provider_code"
        dataSource={providers}
        columns={[
          { title: "Provider", dataIndex: "display_name" },
          { title: "Code", dataIndex: "provider_code" },
          { title: "Queue", dataIndex: "queue_name" },
          {
            title: "Status",
            render: (_, row) => (
              <Space>
                <Tag color={row.enabled ? "green" : "red"}>{row.enabled ? "enabled" : "disabled"}</Tag>
                <Tag color={row.paused ? "orange" : "blue"}>{row.paused ? "paused" : "active"}</Tag>
              </Space>
            )
          },
          {
            title: "Action",
            render: (_, row) => (
              <Button onClick={() => toggle(row)}>{row.paused ? "Resume" : "Pause"}</Button>
            )
          }
        ]}
      />
    </Card>
  );
}

