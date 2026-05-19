import { Button, Card, Select, Space, Table, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { getNotifications, getProviders, NotificationItem, Provider } from "../api";

export default function Notifications({ onOpen }: { onOpen: (id: string) => void }) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [provider, setProvider] = useState<string | undefined>();
  const [status, setStatus] = useState<string | undefined>();

  const load = () => getNotifications({ provider_code: provider, status }).then((data) => setItems(data.items));

  useEffect(() => {
    getProviders().then(setProviders);
  }, []);

  useEffect(() => {
    load();
  }, [provider, status]);

  return (
    <Card>
      <Typography.Title level={3}>Notifications</Typography.Title>
      <Space className="toolbar">
        <Select
          allowClear
          placeholder="Provider"
          style={{ width: 180 }}
          value={provider}
          onChange={setProvider}
          options={providers.map((item) => ({ label: item.display_name, value: item.provider_code }))}
        />
        <Select
          allowClear
          placeholder="Status"
          style={{ width: 180 }}
          value={status}
          onChange={setStatus}
          options={["pending", "delivering", "retrying", "delivered", "failed"].map((item) => ({
            label: item,
            value: item
          }))}
        />
      </Space>
      <Table
        rowKey="id"
        dataSource={items}
        columns={[
          { title: "Provider", dataIndex: "provider_code" },
          { title: "Event", dataIndex: "event_type" },
          { title: "Event ID", dataIndex: "event_id" },
          {
            title: "Status",
            dataIndex: "status",
            render: (value) => <Tag>{value}</Tag>
          },
          { title: "Attempts", dataIndex: "attempt_count" },
          {
            title: "Action",
            render: (_, row) => <Button onClick={() => onOpen(row.id)}>Open</Button>
          }
        ]}
      />
    </Card>
  );
}

