# Sync Issues Analysis and Resolution

## 1. Funnel Manager Initialization

### Status: ✅ FIXED

**Findings:**
- Funnel manager IS initialized on application startup
- Logs confirm: `INFO:backend.main:MaaS funnel initialized with category ID: 1`
- The script showed it as "not initialized" because it runs in a separate process where the global instance is recreated

**Issue:**
- The sync service might run before funnel manager is fully initialized, or the instance might not be accessible in the sync context

**Solution Applied:**
- ✅ Added initialization check in `deal_sync_service.py` before stage mapping
- ✅ Sync service now ensures funnel manager is initialized before use
- ✅ Falls back to name-based mapping if initialization fails

**Funnel Mapping:**
```
Stage mapping: {
  'pending': 'C1:NEW',
  'processing': 'C1:EXECUTING', 
  'completed': 'C1:WON',
  'cancelled': 'C1:LOSE'
}
```

## 2. Problematic Deal IDs

### Status: ⚠️ 7 DEALS RETURNING 400 BAD REQUEST

**Problematic Deal IDs:**
- Deal 32
- Deal 33
- Deal 34
- Deal 35
- Deal 36
- Deal 37
- Deal 38

**Cause:**
- These deals likely don't exist in Bitrix anymore (deleted or invalid)
- Bitrix API returns `400 Bad Request` when trying to access non-existent deals

**Impact:**
- Sync errors for orders associated with these deals
- Stage sync fails for these orders
- Invoice check fails for these orders

**Solution Applied:**
- ✅ Added specific handling for 400 Bad Request errors
- ✅ Sync service now logs warnings instead of errors for invalid deals
- ✅ Invalid deals are skipped gracefully without breaking the sync process
- ✅ Both stage sync and invoice check handle 400 errors properly

## 3. PDF Storage and API Access

### Status: ✅ FULLY WORKING

**Order 41 Invoice:**
- ✅ PDF file exists: `uploads/invoices/invoice_order_41_deal_65.pdf` (30,178 bytes)
- ✅ Document record in database: Document ID 26
- ✅ File path correctly set: `uploads/invoices/invoice_order_41_deal_65.pdf`
- ✅ Original filename: `invoice_order_41.pdf`
- ✅ Category: `invoice`
- ✅ User ID: 1

**API Endpoints Available:**
1. `GET /orders/41/invoices` - Returns list of invoice documents
2. `GET /orders/41/invoice` - Downloads invoice PDF file
3. `GET /documents/26` - Downloads document directly

**Frontend Integration:**
- PDF can be sent to frontend via any of the above endpoints
- File is properly stored and accessible
- Document metadata is correctly stored in database

## Recommendations

1. **Funnel Manager:** Add initialization check in sync service before stage mapping
2. **Invalid Deals:** Handle 400 errors gracefully - skip invalid deals and log them
3. **PDF Storage:** Already working correctly - no changes needed

