import { Card, Table, Tag, Typography } from "antd";
import { useEffect, useMemo, useState } from "react";
import { getMetrics, Metrics, Provider } from "../api";

type QueueRow = Provider & {
  pending: number;
  retrying: number;
  delivered: number;
  failed: number;
  total: number;
};

export default function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    getMetrics().then(setMetrics);
  }, []);

  const rows = useMemo<QueueRow[]>(() => {
    return (metrics?.providers ?? []).map((provider) => {
      const counts = metrics?.by_provider[provider.provider_code] ?? {};
      const statusCounts = {
        pending: counts.pending ?? 0,
        retrying: counts.retrying ?? 0,
        delivered: counts.delivered ?? 0,
        failed: counts.failed ?? 0
      };
      return {
        ...provider,
        ...statusCounts,
        total: Object.values(statusCounts).reduce((sum, value) => sum + value, 0)
      };
    });
  }, [metrics]);

  return (
    <div>
      <Typography.Title level={3}>队列概览</Typography.Title>
      <Card title="各队列任务状态">
        <Table
          rowKey="provider_code"
          dataSource={rows}
          pagination={false}
          columns={[
            { title: "供应商", dataIndex: "display_name" },
            { title: "队列", dataIndex: "queue_name" },
            {
              title: "待投递",
              dataIndex: "pending",
              align: "right" as const
            },
            {
              title: "已送达",
              dataIndex: "delivered",
              align: "right" as const
            },
            {
              title: "重试中",
              dataIndex: "retrying",
              align: "right" as const
            },
            { title: "合计", dataIndex: "total", align: "right" as const },
            {
              title: "失败",
              dataIndex: "failed",
              align: "right" as const
            },
            {
              title: "状态",
              render: (_, row) => (
                <>
                  <Tag color={row.enabled ? "green" : "red"}>{row.enabled ? "已启用" : "已禁用"}</Tag>
                  <Tag color={row.paused ? "orange" : "blue"}>{row.paused ? "已暂停" : "运行中"}</Tag>
                </>
              )
            }
          ]}
        />
      </Card>
    </div>
  );
}
