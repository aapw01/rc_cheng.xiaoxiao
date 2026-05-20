import { RefreshCw } from "lucide-react";
import { Button, Card, Select, Space, Table, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { getNotifications, getProviders, NotificationItem, Provider } from "../api";

const STATUS_OPTIONS = [
  { label: "待投递", value: "pending" },
  { label: "投递中", value: "delivering" },
  { label: "重试中", value: "retrying" },
  { label: "已送达", value: "delivered" },
  { label: "失败", value: "failed" }
];

const STATUS_LABELS = Object.fromEntries(STATUS_OPTIONS.map((item) => [item.value, item.label]));

export default function Notifications({ onOpen }: { onOpen: (id: string) => void }) {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [provider, setProvider] = useState<string | undefined>();
  const [status, setStatus] = useState<string | undefined>();
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await getNotifications({
        provider_code: provider,
        status,
        limit: pageSize,
        offset: (page - 1) * pageSize
      });
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getProviders().then(setProviders);
  }, []);

  useEffect(() => {
    load();
  }, [provider, status, page, pageSize]);

  return (
    <Card>
      <Space className="page-title-row">
        <Typography.Title level={3}>通知任务</Typography.Title>
        <Button icon={<RefreshCw size={16} />} loading={loading} onClick={load}>
          刷新
        </Button>
      </Space>
      <Space className="toolbar">
        <Select
          allowClear
          placeholder="供应商"
          style={{ width: 180 }}
          value={provider}
          onChange={(value) => {
            setProvider(value);
            setPage(1);
          }}
          options={providers.map((item) => ({ label: item.display_name, value: item.provider_code }))}
        />
        <Select
          allowClear
          placeholder="状态"
          style={{ width: 180 }}
          value={status}
          onChange={(value) => {
            setStatus(value);
            setPage(1);
          }}
          options={STATUS_OPTIONS}
        />
      </Space>
      <Table
        rowKey="id"
        dataSource={items}
        loading={loading}
        columns={[
          { title: "供应商", dataIndex: "provider_code" },
          { title: "事件类型", dataIndex: "event_type" },
          { title: "事件 ID", dataIndex: "event_id" },
          {
            title: "状态",
            dataIndex: "status",
            render: (value) => <Tag>{STATUS_LABELS[value] ?? value}</Tag>
          },
          { title: "尝试次数", dataIndex: "attempt_count" },
          {
            title: "操作",
            render: (_, row) => <Button onClick={() => onOpen(row.id)}>查看</Button>
          }
        ]}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          onChange: (nextPage, nextPageSize) => {
            setPage(nextPage);
            setPageSize(nextPageSize);
          }
        }}
      />
    </Card>
  );
}
