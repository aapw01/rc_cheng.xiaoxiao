import { Card, Col, Row, Statistic, Table, Tag, Typography } from "antd";
import { useEffect, useState } from "react";
import { getMetrics, Metrics } from "../api";

export default function Dashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    getMetrics().then(setMetrics);
  }, []);

  const statuses = metrics?.by_status ?? {};

  return (
    <div>
      <Typography.Title level={3}>Dashboard</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic title="Total" value={metrics?.total ?? 0} />
          </Card>
        </Col>
        {["pending", "retrying", "delivered", "failed"].map((status) => (
          <Col span={6} key={status}>
            <Card>
              <Statistic title={status} value={statuses[status] ?? 0} />
            </Card>
          </Col>
        ))}
      </Row>
      <Card className="section-card" title="Provider Backlog">
        <Table
          rowKey="provider_code"
          dataSource={metrics?.providers ?? []}
          pagination={false}
          columns={[
            { title: "Provider", dataIndex: "display_name" },
            { title: "Queue", dataIndex: "queue_name" },
            {
              title: "State",
              render: (_, row) => (
                <>
                  <Tag color={row.enabled ? "green" : "red"}>{row.enabled ? "enabled" : "disabled"}</Tag>
                  <Tag color={row.paused ? "orange" : "blue"}>{row.paused ? "paused" : "active"}</Tag>
                </>
              )
            },
            {
              title: "Failures",
              render: (_, row) => metrics?.by_provider[row.provider_code]?.failed ?? 0
            }
          ]}
        />
      </Card>
    </div>
  );
}

