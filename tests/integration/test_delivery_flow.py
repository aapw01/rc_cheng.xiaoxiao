from app.models import NotificationStatus
from app.services.delivery import deliver_notification


async def test_api_to_worker_success_flow(api_client, db_session, httpx_mock):
    created = await api_client.post(
        "/api/notifications",
        json={
            "provider_code": "crm",
            "event_type": "subscription_paid",
            "event_id": "evt_integration_success",
            "payload": {
                "user_id": "u_123",
                "email": "alice@example.com",
                "subscription_id": "sub_1",
                "amount": 19900,
                "currency": "USD",
                "paid_at": "2026-05-19T10:00:00Z",
            },
        },
    )
    notification_id = created.json()["data"]["id"]
    httpx_mock.add_response(status_code=200, json={"ok": True})

    await deliver_notification(db_session, notification_id)

    detail = await api_client.get(f"/api/admin/notifications/{notification_id}")
    assert detail.json()["data"]["status"] == NotificationStatus.delivered.value
    assert detail.json()["data"]["attempts"][0]["response_status"] == 200


async def test_pause_blocks_new_submission_then_resume_allows(api_client):
    await api_client.post("/api/admin/providers/crm/pause")
    blocked = await api_client.post(
        "/api/notifications",
        json={
            "provider_code": "crm",
            "event_type": "subscription_paid",
            "event_id": "evt_pause_flow",
            "payload": {
                "user_id": "u_123",
                "email": "alice@example.com",
                "subscription_id": "sub_1",
                "amount": 19900,
                "currency": "USD",
                "paid_at": "2026-05-19T10:00:00Z",
            },
        },
    )
    await api_client.post("/api/admin/providers/crm/resume")
    accepted = await api_client.post(
        "/api/notifications",
        json={
            "provider_code": "crm",
            "event_type": "subscription_paid",
            "event_id": "evt_pause_flow",
            "payload": {
                "user_id": "u_123",
                "email": "alice@example.com",
                "subscription_id": "sub_1",
                "amount": 19900,
                "currency": "USD",
                "paid_at": "2026-05-19T10:00:00Z",
            },
        },
    )

    assert blocked.status_code == 409
    assert accepted.status_code == 202
