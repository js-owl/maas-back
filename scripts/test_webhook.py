"""Test webhook endpoint"""
import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/bitrix/webhook",
            json={
                "event_type": "deal_updated",
                "entity_type": "deal",
                "entity_id": 22,
                "data": {
                    "STAGE_ID": "C1:EXECUTING"
                }
            }
        )
        print(f"Webhook test response: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    asyncio.run(test())

