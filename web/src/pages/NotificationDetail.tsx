import { RefreshCw } from "lucide-react";
import { Button, Card, Descriptions, Space, Table, Typography, message } from "antd";
import { useEffect, useState } from "react";
import { Attempt, getNotification, NotificationItem, retryNotification } from "../api";

const STATUS_LABELS: Record<string, string> = {
  pending: "待投递",
  delivering: "投递中",
  retrying: "重试中",
  delivered: "已送达",
  failed: "失败"
};

export default function NotificationDetail({ id, onBack }: { id: string; onBack: () => void }) {
  const [item, setItem] = useState<(NotificationItem & { attempts: Attempt[] }) | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setItem(await getNotification(id));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  async function retry() {
    await retryNotification(id);
    message.success("已重新入队");
    await load();
  }

  if (!item) return null;

  return (
    <Card>
      <Space className="detail-header">
        <Button onClick={onBack}>返回</Button>
        <Typography.Title level={3}>通知详情</Typography.Title>
        <Button icon={<RefreshCw size={16} />} loading={loading} onClick={load}>
          刷新
        </Button>
      </Space>
      <Descriptions bordered column={2} size="small">
        <Descriptions.Item label="ID">{item.id}</Descriptions.Item>
        <Descriptions.Item label="状态">{STATUS_LABELS[item.status] ?? item.status}</Descriptions.Item>
        <Descriptions.Item label="供应商">{item.provider_code}</Descriptions.Item>
        <Descriptions.Item label="事件类型">{item.event_type}</Descriptions.Item>
        <Descriptions.Item label="事件 ID">{item.event_id}</Descriptions.Item>
        <Descriptions.Item label="尝试次数">{item.attempt_count}</Descriptions.Item>
        <Descriptions.Item label="最后错误" span={2}>
          {item.last_error || "-"}
        </Descriptions.Item>
      </Descriptions>
      <Space className="toolbar">
        <Button disabled={item.status !== "failed"} onClick={retry}>
          人工重试
        </Button>
      </Space>
      <Card className="section-card" title="请求载荷">
        <pre>{JSON.stringify(item.payload, null, 2)}</pre>
      </Card>
      <Table
        rowKey="id"
        dataSource={item.attempts}
        loading={loading}
        columns={[
          { title: "次数", dataIndex: "attempt_number" },
          { title: "方法", dataIndex: "request_method" },
          { title: "URL", dataIndex: "request_url" },
          { title: "响应状态", dataIndex: "response_status" },
          { title: "错误类型", dataIndex: "error_type" },
          { title: "错误信息", dataIndex: "error_message" }
        ]}
      />
    </Card>
  );
}
