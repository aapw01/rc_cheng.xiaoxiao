import { RefreshCw } from "lucide-react";
import { Button, Card, Space, Table, Tag, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { getProviders, pauseProvider, Provider, resumeProvider } from "../api";

export default function Providers() {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setProviders(await getProviders());
    } finally {
      setLoading(false);
    }
  };

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
      <Space className="page-title-row">
        <Typography.Title level={3}>供应商管理</Typography.Title>
        <Button icon={<RefreshCw size={16} />} loading={loading} onClick={load}>
          刷新
        </Button>
      </Space>
      <Table
        rowKey="provider_code"
        dataSource={providers}
        loading={loading}
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
