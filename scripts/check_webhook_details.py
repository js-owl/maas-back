"""Check webhook message details"""
import asyncio
import sys
import json
sys.path.insert(0, '/app')

from backend.bitrix.queue_service import bitrix_queue_service

async def check():
    print("=" * 80)
    print("Checking Webhook Message Details")
    print("=" * 80)
    
    try:
        redis = await bitrix_queue_service._get_redis()
        
        # Get the webhook message
        messages = await redis.xrange(
            bitrix_queue_service.webhooks_stream,
            min="-",
            max="+",
            count=1
        )
        
        if messages:
            msg_id, fields = messages[0]
            print(f"\nMessage ID: {msg_id}")
            print(f"\nFields:")
            for key, value in fields.items():
                if key == "data":
                    try:
                        data = json.loads(value)
                        print(f"  {key}:")
                        for k, v in data.items():
                            print(f"    {k}: {v}")
                    except:
                        print(f"  {key}: {value}")
                else:
                    print(f"  {key}: {value}")
            
            # Check category ID
            data_str = fields.get("data", "{}")
            try:
                data = json.loads(data_str)
                category_id = data.get("CATEGORY_ID") or data.get("category_id")
                print(f"\nCategory ID in webhook: {category_id}")
                
                # Check MaaS funnel category
                from backend.bitrix.funnel_manager import funnel_manager
                maas_category_id = funnel_manager.get_category_id()
                print(f"MaaS Funnel Category ID: {maas_category_id}")
                
                if category_id and maas_category_id:
                    if str(category_id) == str(maas_category_id):
                        print("✓ Category matches MaaS funnel")
                    else:
                        print(f"✗ Category {category_id} does not match MaaS funnel {maas_category_id}")
            except Exception as e:
                print(f"Error parsing data: {e}")
        else:
            print("\nNo webhook messages found")
        
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check())






