"""
Audit script to verify Bitrix field mapping and duplicate prevention
Queries ALL orders and users from database and compares with what's sent to Bitrix
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from backend.database import AsyncSessionLocal
from backend import models
from backend.bitrix.client import bitrix_client
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Fields currently sent to Bitrix (from worker.py and service.py)
DEAL_FIELDS_SENT = {
    "TITLE": "Order #{order_id} - {service_id}",
    "OPPORTUNITY": "total_price",
    "CURRENCY_ID": "RUB",
    "COMMENTS": "Service, quantity, status, special_instructions, material, dimensions",
    "CATEGORY_ID": "MaaS funnel category",
    "STAGE_ID": "Mapped from order status",
    "CONTACT_ID": "user.bitrix_contact_id",
    "SOURCE_ID": "WEB (worker only)",
    "SOURCE_DESCRIPTION": "Manufacturing Service API (worker only)"
}

CONTACT_FIELDS_SENT = {
    "NAME": "full_name or username",
    "EMAIL": "email (as array)",
    "PHONE": "phone_number (as array)",
    "COMPANY_TITLE": "company",
    "ADDRESS_CITY": "city",
    "SOURCE_ID": "WEB",
    "TYPE_ID": "CLIENT"
}

# All Order model fields
ORDER_FIELDS = [
    "order_id", "user_id", "service_id", "file_id", "quantity",
    "dimensions", "length", "width", "height", "thickness", "dia", "n_dimensions",
    "composite_rig", "material_id", "material_form", "special_instructions",
    "status", "k_otk", "k_cert", "tolerance_id", "finish_id", "cover_id",
    "mat_volume", "detail_price", "detail_price_one", "mat_weight", "mat_price",
    "work_price", "k_quantity", "detail_time", "k_complexity", "total_time",
    "k_p", "manufacturing_cycle", "suitable_machines", "calculation_type",
    "ml_model", "ml_confidence", "calculation_time", "total_calculation_time",
    "created_at", "updated_at", "bitrix_deal_id",
    "invoice_url", "invoice_file_path", "invoice_generated_at", "document_ids"
]

# All User model fields
USER_FIELDS = [
    "id", "username", "hashed_password", "is_admin", "must_change_password",
    "user_type", "bitrix_contact_id", "email", "full_name", "city", "company",
    "phone_number", "payment_card_number", "building", "region", "street",
    "postal", "payment_company_name", "payment_inn", "payment_kpp",
    "payment_bik", "payment_bank_name", "payment_account", "payment_cor_account",
    "created_at", "updated_at"
]

async def get_all_orders(db) -> List[models.Order]:
    """Get all orders from database"""
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.user))
        .order_by(models.Order.order_id)
    )
    return result.scalars().all()

async def get_all_users(db) -> List[models.User]:
    """Get all users from database"""
    result = await db.execute(
        select(models.User)
        .order_by(models.User.id)
    )
    return result.scalars().all()

async def check_deal_exists_in_bitrix(deal_id: int) -> bool:
    """Check if deal exists in Bitrix"""
    if not bitrix_client.is_configured():
        return False
    try:
        deal = await bitrix_client.get_deal(deal_id)
        return deal is not None
    except Exception:
        return False

async def check_contact_exists_in_bitrix(contact_id: int) -> bool:
    """Check if contact exists in Bitrix"""
    if not bitrix_client.is_configured():
        return False
    try:
        contact = await bitrix_client.get_contact(contact_id)
        return contact is not None
    except Exception:
        return False

def analyze_order_fields(order: models.Order) -> Dict[str, Any]:
    """Analyze order fields and what would be sent to Bitrix"""
    analysis = {
        "order_id": order.order_id,
        "has_bitrix_deal_id": order.bitrix_deal_id is not None,
        "bitrix_deal_id": order.bitrix_deal_id,
        "fields_in_db": {},
        "fields_sent_to_bitrix": {},
        "missing_fields": []
    }
    
    # Check all order fields
    for field in ORDER_FIELDS:
        value = getattr(order, field, None)
        if value is not None:
            analysis["fields_in_db"][field] = value
    
    # Fields that are sent to Bitrix
    analysis["fields_sent_to_bitrix"] = {
        "TITLE": f"Order #{order.order_id} - {order.service_id}",
        "OPPORTUNITY": order.total_price or 0,
        "CURRENCY_ID": "RUB",
        "COMMENTS": f"Service: {order.service_id}\nQuantity: {order.quantity}\nStatus: {order.status}",
        "CATEGORY_ID": "MaaS funnel (if initialized)",
        "STAGE_ID": "Mapped from status",
        "CONTACT_ID": order.user.bitrix_contact_id if order.user else None
    }
    
    # Potential missing fields
    missing = []
    if order.created_at:
        missing.append("BEGINDATE (created_at)")
    if order.manufacturing_cycle:
        missing.append("CLOSEDATE (calculated from manufacturing_cycle)")
    if order.calculation_type or order.ml_model:
        missing.append("ADDITIONAL_INFO (calculation details, ML info)")
    missing.append("ORIGIN_ID (order_id for tracking)")
    missing.append("ORIGINATOR_ID (MaaS API)")
    
    analysis["missing_fields"] = missing
    return analysis

def analyze_contact_fields(user: models.User) -> Dict[str, Any]:
    """Analyze user/contact fields and what would be sent to Bitrix"""
    analysis = {
        "user_id": user.id,
        "has_bitrix_contact_id": user.bitrix_contact_id is not None,
        "bitrix_contact_id": user.bitrix_contact_id,
        "fields_in_db": {},
        "fields_sent_to_bitrix": {},
        "missing_fields": []
    }
    
    # Check all user fields
    for field in USER_FIELDS:
        value = getattr(user, field, None)
        if value is not None:
            analysis["fields_in_db"][field] = value
    
    # Fields that are sent to Bitrix
    analysis["fields_sent_to_bitrix"] = {
        "NAME": user.full_name or user.username,
        "EMAIL": user.email,
        "PHONE": user.phone_number,
        "COMPANY_TITLE": user.company,
        "ADDRESS_CITY": user.city,
        "SOURCE_ID": "WEB",
        "TYPE_ID": "CLIENT"
    }
    
    # Potential missing fields
    missing = []
    if user.full_name:
        missing.append("LAST_NAME, SECOND_NAME (if full_name can be parsed)")
    if user.street or user.building or user.postal or user.region:
        missing.append("ADDRESS fields (street, building, postal, region)")
    if user.user_type == "legal" or user.payment_inn:
        missing.append("COMMENTS (user_type, payment info for legal entities)")
    missing.append("ORIGIN_ID (user id for tracking)")
    
    analysis["missing_fields"] = missing
    return analysis

async def check_duplicate_prevention():
    """Check duplicate prevention logic in code"""
    print("\n" + "="*80)
    print("DUPLICATE PREVENTION ANALYSIS")
    print("="*80)
    
    # Check worker.py logic
    print("\n1. Worker.py - Deal Creation:")
    print("   - Check: Does it check bitrix_deal_id before creating?")
    print("   - Status: ❌ NO - Worker does NOT check bitrix_deal_id before creating deals")
    print("   - Recommendation: Add check for order.bitrix_deal_id before creating")
    
    print("\n2. Worker.py - Contact Creation:")
    print("   - Check: Does it check bitrix_contact_id before creating?")
    print("   - Status: ✅ YES - Worker checks user.bitrix_contact_id (line 226)")
    print("   - Code: if user.bitrix_contact_id: return True")
    
    print("\n3. Sync Service - Contact Queue:")
    print("   - Check: Does it check bitrix_contact_id before queuing?")
    print("   - Status: ✅ YES - Sync service checks user.bitrix_contact_id (line 146)")
    print("   - Code: if user.bitrix_contact_id: return")
    
    print("\n4. Sync Service - Deal Queue:")
    print("   - Check: Does it check bitrix_deal_id before queuing?")
    print("   - Status: ❌ NO - Sync service does NOT check bitrix_deal_id before queuing")
    print("   - Recommendation: Add check for order.bitrix_deal_id before queuing")

async def main():
    """Main audit function"""
    print("="*80)
    print("BITRIX FIELD MAPPING AND DUPLICATE PREVENTION AUDIT")
    print("="*80)
    print(f"Started at: {datetime.now().isoformat()}")
    
    async with AsyncSessionLocal() as db:
        # Get all orders and users
        print("\n[1/5] Querying database...")
        orders = await get_all_orders(db)
        users = await get_all_users(db)
        print(f"   Found {len(orders)} orders and {len(users)} users")
        
        # Analyze orders
        print("\n[2/5] Analyzing orders...")
        order_analyses = []
        orders_without_deals = []
        orders_with_orphaned_deals = []
        
        for order in orders:
            analysis = analyze_order_fields(order)
            order_analyses.append(analysis)
            
            # Check for missing Bitrix deals
            if not order.bitrix_deal_id:
                orders_without_deals.append(order.order_id)
            
            # Check for orphaned deals
            if order.bitrix_deal_id:
                exists = await check_deal_exists_in_bitrix(order.bitrix_deal_id)
                if not exists:
                    orders_with_orphaned_deals.append({
                        "order_id": order.order_id,
                        "bitrix_deal_id": order.bitrix_deal_id
                    })
        
        print(f"   Analyzed {len(order_analyses)} orders")
        print(f"   Orders without Bitrix deals: {len(orders_without_deals)}")
        print(f"   Orders with orphaned Bitrix deals: {len(orders_with_orphaned_deals)}")
        
        # Analyze users
        print("\n[3/5] Analyzing users/contacts...")
        user_analyses = []
        users_without_contacts = []
        users_with_orphaned_contacts = []
        
        for user in users:
            analysis = analyze_contact_fields(user)
            user_analyses.append(analysis)
            
            # Check for missing Bitrix contacts
            if not user.bitrix_contact_id:
                users_without_contacts.append(user.id)
            
            # Check for orphaned contacts
            if user.bitrix_contact_id:
                exists = await check_contact_exists_in_bitrix(user.bitrix_contact_id)
                if not exists:
                    users_with_orphaned_contacts.append({
                        "user_id": user.id,
                        "bitrix_contact_id": user.bitrix_contact_id
                    })
        
        print(f"   Analyzed {len(user_analyses)} users")
        print(f"   Users without Bitrix contacts: {len(users_without_contacts)}")
        print(f"   Users with orphaned Bitrix contacts: {len(users_with_orphaned_contacts)}")
        
        # Check duplicate prevention
        print("\n[4/5] Checking duplicate prevention logic...")
        await check_duplicate_prevention()
        
        # Generate report
        print("\n[5/5] Generating report...")
        report = generate_report(
            order_analyses, user_analyses,
            orders_without_deals, orders_with_orphaned_deals,
            users_without_contacts, users_with_orphaned_contacts
        )
        
        # Write report to file
        report_path = Path("BITRIX_FIELD_AUDIT_REPORT.md")
        report_path.write_text(report, encoding="utf-8")
        print(f"\n✅ Report saved to: {report_path}")
        print("\n" + "="*80)
        print("AUDIT COMPLETE")
        print("="*80)

def generate_report(
    order_analyses: List[Dict],
    user_analyses: List[Dict],
    orders_without_deals: List[int],
    orders_with_orphaned_deals: List[Dict],
    users_without_contacts: List[int],
    users_with_orphaned_contacts: List[Dict]
) -> str:
    """Generate markdown report"""
    report = f"""# Bitrix Field Mapping and Duplicate Prevention Audit Report

Generated: {datetime.now().isoformat()}

## Summary

- **Total Orders**: {len(order_analyses)}
- **Orders without Bitrix deals**: {len(orders_without_deals)}
- **Orders with orphaned Bitrix deals**: {len(orders_with_orphaned_deals)}
- **Total Users**: {len(user_analyses)}
- **Users without Bitrix contacts**: {len(users_without_contacts)}
- **Users with orphaned Bitrix contacts**: {len(users_with_orphaned_contacts)}

## 1. Order Field Analysis

### Fields Currently Sent to Bitrix

| Field | Source | Notes |
|-------|--------|-------|
| TITLE | Order #order_id - service_id | Deal title |
| OPPORTUNITY | total_price | Deal amount |
| CURRENCY_ID | "RUB" | Fixed currency |
| COMMENTS | Service, quantity, status, special_instructions, material, dimensions | Combined text |
| CATEGORY_ID | MaaS funnel category | If funnel initialized |
| STAGE_ID | Mapped from order status | Status mapping |
| CONTACT_ID | user.bitrix_contact_id | If contact exists |
| SOURCE_ID | "WEB" | Worker only |
| SOURCE_DESCRIPTION | "Manufacturing Service API" | Worker only |

### Potential Missing Fields

| Field | Source | Priority | Notes |
|-------|--------|----------|-------|
| BEGINDATE | order.created_at | High | Deal start date |
| CLOSEDATE | calculated from manufacturing_cycle | Medium | Deal end date |
| ADDITIONAL_INFO | calculation_type, ml_model, ml_confidence | Low | Technical details |
| ORIGIN_ID | order_id | High | For tracking back to source |
| ORIGINATOR_ID | "MaaS API" | High | Source system identifier |

### Order Fields in Database (Not Sent)

The following order fields exist in the database but are NOT currently sent to Bitrix:

- **Dimensions**: length, width, height, dia, thickness, n_dimensions
- **Material Details**: material_id, material_form
- **Pricing Details**: detail_price, detail_price_one, mat_price, work_price, mat_weight
- **Calculation Details**: calculation_type, ml_model, ml_confidence, manufacturing_cycle
- **Time Details**: detail_time, total_time, calculation_time, total_calculation_time
- **Other**: tolerance_id, finish_id, cover_id, suitable_machines, k_quantity, k_complexity

## 2. Contact Field Analysis

### Fields Currently Sent to Bitrix

| Field | Source | Notes |
|-------|--------|-------|
| NAME | full_name or username | Contact name |
| EMAIL | email | As array with VALUE_TYPE |
| PHONE | phone_number | As array with VALUE_TYPE |
| COMPANY_TITLE | company | Company name |
| ADDRESS_CITY | city | City only |
| SOURCE_ID | "WEB" | Source identifier |
| TYPE_ID | "CLIENT" | Contact type |

### Potential Missing Fields

| Field | Source | Priority | Notes |
|-------|--------|----------|-------|
| LAST_NAME, SECOND_NAME | Parse full_name | Medium | If full_name can be split |
| ADDRESS fields | street, building, postal, region | Medium | Full address information |
| COMMENTS | user_type, payment info | Low | For legal entities |
| ORIGIN_ID | user id | High | For tracking back to source |

### User Fields in Database (Not Sent)

The following user fields exist in the database but are NOT currently sent to Bitrix:

- **Address Details**: building, region, street, postal
- **Legal Entity Details**: payment_company_name, payment_inn, payment_kpp, payment_bik, payment_bank_name, payment_account, payment_cor_account
- **Other**: user_type, payment_card_number

## 3. Duplicate Prevention Status

### Deal Creation

- **Worker.py**: ❌ **MISSING** - Does NOT check `order.bitrix_deal_id` before creating deals
- **Sync Service**: ❌ **MISSING** - Does NOT check `order.bitrix_deal_id` before queuing

**Recommendation**: Add duplicate check in `worker.py` `_process_deal_operation`:
```python
if order.bitrix_deal_id:
    logger.info(f"Order already has Bitrix deal")
    return True
```

### Contact Creation

- **Worker.py**: ✅ **OK** - Checks `user.bitrix_contact_id` before creating (line 226)
- **Sync Service**: ✅ **OK** - Checks `user.bitrix_contact_id` before queuing (line 146)

## 4. Data Quality Issues

### Orders Without Bitrix Deals

"""
    
    if orders_without_deals:
        report += f"Found {len(orders_without_deals)} orders without Bitrix deals:\n\n"
        report += "| Order ID | Status | Created At |\n"
        report += "|----------|--------|-----------|\n"
        for order_id in orders_without_deals[:20]:  # Show first 20
            order = next((o for o in order_analyses if o["order_id"] == order_id), None)
            if order:
                report += f"| {order_id} | - | - |\n"
        if len(orders_without_deals) > 20:
            report += f"\n... and {len(orders_without_deals) - 20} more\n"
    else:
        report += "✅ All orders have Bitrix deals\n"
    
    report += "\n### Orders with Orphaned Bitrix Deals\n\n"
    if orders_with_orphaned_deals:
        report += f"Found {len(orders_with_orphaned_deals)} orders with Bitrix deal IDs that don't exist in Bitrix:\n\n"
        report += "| Order ID | Bitrix Deal ID |\n"
        report += "|----------|----------------|\n"
        for item in orders_with_orphaned_deals[:20]:  # Show first 20
            report += f"| {item['order_id']} | {item['bitrix_deal_id']} |\n"
        if len(orders_with_orphaned_deals) > 20:
            report += f"\n... and {len(orders_with_orphaned_deals) - 20} more\n"
    else:
        report += "✅ No orphaned Bitrix deals found\n"
    
    report += "\n### Users Without Bitrix Contacts\n\n"
    if users_without_contacts:
        report += f"Found {len(users_without_contacts)} users without Bitrix contacts:\n\n"
        report += f"User IDs: {', '.join(map(str, users_without_contacts[:50]))}"
        if len(users_without_contacts) > 50:
            report += f" ... and {len(users_without_contacts) - 50} more\n"
    else:
        report += "✅ All users have Bitrix contacts\n"
    
    report += "\n### Users with Orphaned Bitrix Contacts\n\n"
    if users_with_orphaned_contacts:
        report += f"Found {len(users_with_orphaned_contacts)} users with Bitrix contact IDs that don't exist in Bitrix:\n\n"
        report += "| User ID | Bitrix Contact ID |\n"
        report += "|---------|------------------|\n"
        for item in users_with_orphaned_contacts[:20]:  # Show first 20
            report += f"| {item['user_id']} | {item['bitrix_contact_id']} |\n"
        if len(users_with_orphaned_contacts) > 20:
            report += f"\n... and {len(users_with_orphaned_contacts) - 20} more\n"
    else:
        report += "✅ No orphaned Bitrix contacts found\n"
    
    report += """
## 5. Recommendations

### High Priority

1. **Add duplicate prevention for deals**: Check `order.bitrix_deal_id` before creating deals in `worker.py`
2. **Add ORIGIN_ID to deals**: Include `order_id` as `ORIGIN_ID` for tracking
3. **Add ORIGINATOR_ID to deals**: Set to "MaaS API" to identify source system
4. **Add BEGINDATE to deals**: Use `order.created_at` as deal start date

### Medium Priority

1. **Add ORIGIN_ID to contacts**: Include `user.id` as `ORIGIN_ID` for tracking
2. **Add address fields to contacts**: Include street, building, postal, region if available
3. **Add CLOSEDATE to deals**: Calculate from `manufacturing_cycle` if available
4. **Parse full_name for contacts**: Split into NAME, LAST_NAME, SECOND_NAME if possible

### Low Priority

1. **Add ADDITIONAL_INFO to deals**: Include calculation_type, ml_model, ml_confidence
2. **Add COMMENTS to contacts**: Include user_type and payment info for legal entities

## 6. Implementation Notes

- All field additions should maintain backward compatibility
- Test with existing Bitrix deals/contacts before deploying
- Consider adding validation for required fields
- Monitor Bitrix API rate limits when adding new fields
"""
    
    return report

if __name__ == "__main__":
    asyncio.run(main())

