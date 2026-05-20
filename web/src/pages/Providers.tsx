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
      message.success("供应商已恢复");
    } else {
      await pauseProvider(provider.provider_code);
      message.success("供应商已暂停");
    }
    await load();
  }

  return (
    <Card>
      <Typography.Title level={3}>供应商管理</Typography.Title>
      <Table
        rowKey="provider_code"
        dataSource={providers}
        columns={[
          { title: "供应商", dataIndex: "display_name" },
          { title: "编码", dataIndex: "provider_code" },
          { title: "队列", dataIndex: "queue_name" },
          {
            title: "状态",
            render: (_, row) => (
              <Space>
                <Tag color={row.enabled ? "green" : "red"}>{row.enabled ? "已启用" : "已禁用"}</Tag>
                <Tag color={row.paused ? "orange" : "blue"}>{row.paused ? "已暂停" : "运行中"}</Tag>
              </Space>
            )
          },
          {
            title: "操作",
            render: (_, row) => (
              <Button onClick={() => toggle(row)}>{row.paused ? "恢复" : "暂停"}</Button>
            )
          }
        ]}
      />
    </Card>
  );
}
