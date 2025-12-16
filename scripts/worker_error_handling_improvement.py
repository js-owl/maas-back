"""
Proposed improvements for worker error handling

This shows what SHOULD happen when worker encounters different error types
"""

# Current behavior:
# - All errors treated the same
# - Retry up to 5 times, then acknowledge
# - No distinction between permanent and transient errors

# What SHOULD happen:

class ErrorCategory:
    """Categorize errors for smart retry logic"""
    PERMANENT = "permanent"  # Won't fix itself - acknowledge quickly
    TRANSIENT = "transient"  # Might fix itself - retry with backoff
    BUSINESS_LOGIC = "business_logic"  # Needs case-by-case handling

def categorize_bitrix_error(status_code: int, error_body: str, method: str, operation: str) -> str:
    """
    Categorize Bitrix API error for smart retry decisions
    
    Returns: ErrorCategory constant
    """
    error_lower = error_body.lower()
    
    # Permanent errors - won't fix by retrying
    if status_code == 400:
        if "not found" in error_lower:
            # For update operations: deal/contact doesn't exist - permanent
            if operation == "update":
                return ErrorCategory.PERMANENT
            # For create: shouldn't happen, but if it does, it's permanent
            return ErrorCategory.PERMANENT
        
        if "invalid" in error_lower or "validation" in error_lower:
            # Invalid data format - won't fix itself
            return ErrorCategory.PERMANENT
        
        if "already exists" in error_lower or "duplicate" in error_lower:
            # Business logic - handle case-by-case
            return ErrorCategory.BUSINESS_LOGIC
    
    # Authentication errors - permanent (need to fix config)
    if status_code == 401:
        return ErrorCategory.PERMANENT
    
    # Permission errors - permanent
    if status_code == 403:
        return ErrorCategory.PERMANENT
    
    # Transient errors - might fix by retrying
    if status_code == 429:  # Rate limiting
        return ErrorCategory.TRANSIENT
    
    if status_code >= 500:  # Server errors
        return ErrorCategory.TRANSIENT
    
    # Network/timeout errors (caught as exceptions)
    # These are transient
    
    # Default: treat as transient (safer to retry)
    return ErrorCategory.TRANSIENT


def should_retry(error_category: str, retry_count: int, max_retries: int) -> tuple[bool, int]:
    """
    Determine if message should be retried based on error category
    
    Returns: (should_retry, new_max_retries)
    """
    if error_category == ErrorCategory.PERMANENT:
        # Permanent errors: retry only 1-2 times, then give up
        max_retries_for_permanent = 2
        return (retry_count < max_retries_for_permanent, max_retries_for_permanent)
    
    elif error_category == ErrorCategory.BUSINESS_LOGIC:
        # Business logic: retry a few times, then handle specially
        max_retries_for_business = 3
        return (retry_count < max_retries_for_business, max_retries_for_business)
    
    else:  # TRANSIENT
        # Transient errors: use full retry count with exponential backoff
        return (retry_count < max_retries, max_retries)


# Example usage in worker:

async def process_with_smart_retry(message, db):
    """
    Process message with smart retry logic based on error type
    """
    retry_count = int(message.get("retry_count", "0"))
    operation = message.get("operation")
    entity_type = message.get("entity_type")
    
    # Process the operation
    try:
        success = await process_operation(message, db)
        if success:
            return True, None  # Success, no error
    except BitrixAPIError as e:
        # Categorize the error
        error_category = categorize_bitrix_error(
            e.status_code,
            e.error_body,
            e.method,
            operation
        )
        
        # Determine if should retry
        should_retry_flag, effective_max_retries = should_retry(
            error_category,
            retry_count,
            max_retries=5
        )
        
        if not should_retry_flag:
            # Max retries reached for this error type
            if error_category == ErrorCategory.PERMANENT:
                logger.warning(
                    f"Permanent error for {entity_type} {message.get('entity_id')}: "
                    f"{e.error_body}. Acknowledging after {retry_count} retries."
                )
            elif error_category == ErrorCategory.BUSINESS_LOGIC:
                logger.warning(
                    f"Business logic error for {entity_type} {message.get('entity_id')}: "
                    f"{e.error_body}. May need manual intervention."
                )
            return False, "max_retries_reached"
        
        # Should retry - increment retry count
        return False, error_category  # Return error category for logging
    
    return False, "unknown_error"









