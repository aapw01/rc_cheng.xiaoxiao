import { Button, Card, Descriptions, Space, Table, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { Attempt, getNotification, NotificationItem, retryNotification } from "../api";

export default function NotificationDetail({ id, onBack }: { id: string; onBack: () => void }) {
  const [item, setItem] = useState<(NotificationItem & { attempts: Attempt[] }) | null>(null);

  const load = () => getNotification(id).then(setItem);

  useEffect(() => {
    load();
  }, [id]);

  async function retry() {
    await retryNotification(id);
    message.success("Retry queued");
    await load();
  }

  if (!item) return null;

  return (
    <Card>
      <Space className="detail-header">
        <Button onClick={onBack}>Back</Button>
        <Typography.Title level={3}>Notification Detail</Typography.Title>
      </Space>
      <Descriptions bordered column={2} size="small">
        <Descriptions.Item label="ID">{item.id}</Descriptions.Item>
        <Descriptions.Item label="Status">{item.status}</Descriptions.Item>
        <Descriptions.Item label="Provider">{item.provider_code}</Descriptions.Item>
        <Descriptions.Item label="Event">{item.event_type}</Descriptions.Item>
        <Descriptions.Item label="Event ID">{item.event_id}</Descriptions.Item>
        <Descriptions.Item label="Attempts">{item.attempt_count}</Descriptions.Item>
      </Descriptions>
      <Space className="toolbar">
        <Button disabled={item.status !== "failed"} onClick={retry}>
          Retry
        </Button>
      </Space>
      <Card className="section-card" title="Payload">
        <pre>{JSON.stringify(item.payload, null, 2)}</pre>
      </Card>
      <Table
        rowKey="id"
        dataSource={item.attempts}
        columns={[
          { title: "#", dataIndex: "attempt_number" },
          { title: "Method", dataIndex: "request_method" },
          { title: "URL", dataIndex: "request_url" },
          { title: "Status", dataIndex: "response_status" },
          { title: "Error", dataIndex: "error_type" },
          { title: "Message", dataIndex: "error_message" }
        ]}
      />
    </Card>
  );
}

