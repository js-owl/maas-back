# Bitrix Field Mapping and Duplicate Prevention Audit Report

Generated: 2025-11-20T13:08:51.217586

## Summary

- **Total Orders**: 37
- **Orders without Bitrix deals**: 27
- **Orders with orphaned Bitrix deals**: 10
- **Total Users**: 8
- **Users without Bitrix contacts**: 6
- **Users with orphaned Bitrix contacts**: 2

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

Found 27 orders without Bitrix deals:

| Order ID | Status | Created At |
|----------|--------|-----------|
| 1 | - | - |
| 2 | - | - |
| 3 | - | - |
| 4 | - | - |
| 5 | - | - |
| 6 | - | - |
| 7 | - | - |
| 8 | - | - |
| 9 | - | - |
| 10 | - | - |
| 11 | - | - |
| 12 | - | - |
| 13 | - | - |
| 14 | - | - |
| 15 | - | - |
| 16 | - | - |
| 17 | - | - |
| 18 | - | - |
| 19 | - | - |
| 20 | - | - |

... and 7 more

### Orders with Orphaned Bitrix Deals

Found 10 orders with Bitrix deal IDs that don't exist in Bitrix:

| Order ID | Bitrix Deal ID |
|----------|----------------|
| 28 | 13 |
| 29 | 14 |
| 30 | 15 |
| 31 | 16 |
| 32 | 17 |
| 33 | 18 |
| 34 | 19 |
| 35 | 20 |
| 36 | 21 |
| 37 | 22 |

### Users Without Bitrix Contacts

Found 6 users without Bitrix contacts:

User IDs: 3, 4, 5, 6, 7, 8
### Users with Orphaned Bitrix Contacts

Found 2 users with Bitrix contact IDs that don't exist in Bitrix:

| User ID | Bitrix Contact ID |
|---------|------------------|
| 1 | 8 |
| 2 | 17 |

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
