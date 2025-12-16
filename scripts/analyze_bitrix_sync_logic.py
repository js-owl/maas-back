"""Analyze Bitrix sync logic for correctness and duplicate prevention"""
import sys
sys.path.insert(0, '/app')

print("=" * 80)
print("Bitrix Sync Logic Analysis")
print("=" * 80)

print("\n1. ORDER CREATION/UPDATE LOGIC:")
print("-" * 80)
print("✅ Order Creation:")
print("   - create_order_with_calculation() → queue_deal_creation()")
print("   - create_order_with_dimensions() → queue_deal_creation()")
print("   - Both check if order.bitrix_deal_id exists before queuing")

print("\n✅ Order Update:")
print("   - update_order() → queue_deal_update() IF bitrix_deal_id exists")
print("   - ⚠️  ISSUE: If order is updated but has no deal_id, no deal is created")
print("   - Should queue_deal_creation() if bitrix_deal_id is None")

print("\n2. USER CREATION/UPDATE LOGIC:")
print("-" * 80)
print("✅ User Creation:")
print("   - register_user() → queue_contact_creation()")
print("   - Checks if user.bitrix_contact_id exists before queuing")

print("\n✅ User Update:")
print("   - update_profile() → queue_contact_update() IF bitrix_contact_id exists")
print("   - update_user_by_id_endpoint() → queue_contact_update() IF bitrix_contact_id exists")
print("   - ⚠️  ISSUE: If user is updated but has no contact_id, no contact is created")
print("   - Should queue_contact_creation() if bitrix_contact_id is None")

print("\n3. DUPLICATE PREVENTION:")
print("-" * 80)
print("✅ Queue Level (sync_service.py):")
print("   - queue_deal_creation(): Checks order.bitrix_deal_id, returns early if exists")
print("   - queue_contact_creation(): Checks user.bitrix_contact_id, returns early if exists")

print("\n✅ Worker Level (worker.py):")
print("   - _process_deal_operation('create'): Checks order.bitrix_deal_id, returns early if exists")
print("   - _process_contact_operation('create'): Checks user.bitrix_contact_id, returns early if exists")
print("   - _process_deal_operation('create'): Also checks for duplicates and cleans them up")

print("\n⚠️  RACE CONDITION:")
print("   - Between checking bitrix_deal_id/bitrix_contact_id and creating, another")
print("     message could be processed, potentially creating duplicates")
print("   - Mitigation: Worker checks again before creating (double-check pattern)")
print("   - Better: Use database transaction with SELECT FOR UPDATE or unique constraint")

print("\n4. POTENTIAL ISSUES:")
print("-" * 80)
print("❌ Issue 1: Order update without deal_id doesn't create deal")
print("   - Fix: In update_order(), if bitrix_deal_id is None, queue_deal_creation()")

print("\n❌ Issue 2: User update without contact_id doesn't create contact")
print("   - Fix: In update_profile() and update_user_by_id_endpoint(),")
print("     if bitrix_contact_id is None, queue_contact_creation()")

print("\n⚠️  Issue 3: Race condition in duplicate prevention")
print("   - Current: Double-check pattern (check in queue, check in worker)")
print("   - Better: Use database-level locking or unique constraints")

print("\n✅ Issue 4: Duplicate cleanup")
print("   - Worker calls cleanup_duplicate_deals_for_order() if deal_id exists")
print("   - This is good, but should be more proactive")

print("\n" + "=" * 80)
print("RECOMMENDATIONS:")
print("=" * 80)
print("1. Fix order update: Create deal if missing")
print("2. Fix user update: Create contact if missing")
print("3. Consider database-level duplicate prevention")
print("4. Add idempotency keys to Redis messages")
print("=" * 80)






