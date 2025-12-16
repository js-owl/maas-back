# Why Public URL Returns 403 Forbidden

## Current Situation

The code is currently using **authenticated AJAX URLs** (`downloadUrl`, `pdfUrl`), not public URLs. These URLs require browser session authentication, which is why they return 403.

## Why Public URLs Might Also Return 403

If you're getting 403 on `publicUrl`, here are the possible reasons:

### 1. Public URL Not Enabled

Public URLs must be **explicitly enabled** for each document. By default, documents don't have public URLs enabled.

**Solution:** Use `crm.documentgenerator.document.enablepublicurl` to enable it:
```python
await bitrix_client.enable_document_public_url(document_id, enable=True)
```

### 2. Public URL Expired or Disabled

Public URLs can be:
- **Time-limited** - May expire after a certain period
- **Manually disabled** - Can be turned off in Bitrix settings
- **Revoked** - May be invalidated if document is updated

**Solution:** Check if public URL is still valid, re-enable if needed.

### 3. Bitrix Security Settings

Bitrix may have security settings that:
- **Block external access** to public URLs
- **Require IP whitelist** for public document access
- **Require authentication** even for "public" URLs

**Solution:** Check Bitrix security settings:
- Settings → Security → Public Document Access
- Settings → CRM → Document Generator → Public URL Settings

### 4. Document Generator Permissions

The webhook user might not have permission to:
- **Enable public URLs** for documents
- **Access public URLs** even if enabled

**Solution:** Check webhook user permissions:
- Settings → CRM → Access Rights
- Ensure "Manage Document Generator" permission

### 5. Public URL Format Issue

The public URL might be:
- **Incomplete** - Missing required parameters
- **Malformed** - Incorrect format
- **Domain-specific** - May require specific domain access

**Solution:** Verify the public URL format and ensure it's complete.

## Updated Code Behavior

The updated code now:

1. **Checks for `publicUrl` first** - Uses public URL if available
2. **Enables public URL if missing** - Automatically enables it using the API
3. **Falls back to authenticated URLs** - Uses `downloadUrl`/`pdfUrl` if public URL unavailable

## Testing Public URL

To test if public URL works:

1. **Enable public URL manually in Bitrix:**
   - Open the document in Bitrix
   - Enable "Public Link" option
   - Copy the public URL

2. **Test the URL directly:**
   ```bash
   curl -I "https://your-bitrix-domain.com/public-url-here"
   ```

3. **Check response:**
   - `200 OK` = Public URL works
   - `403 Forbidden` = Public URL requires authentication or is disabled
   - `404 Not Found` = Public URL is invalid or expired

## Recommended Fix

The code has been updated to:
1. Try `publicUrl` first
2. Enable it automatically if not available
3. Log which URL type is being used

After restarting the container, check logs for:
- `"[INVOICE_SYNC] Using public URL"` - Public URL is working
- `"[INVOICE_SYNC] Enabled and using public URL"` - Public URL was enabled
- `"[INVOICE_SYNC] Using PDF URL (may require authentication)"` - Falling back to authenticated URL

## If Public URL Still Returns 403

If public URLs still return 403 after enabling:

1. **Check Bitrix security settings** - May block external access
2. **Verify webhook permissions** - Need "Manage Document Generator" permission
3. **Check document template settings** - Some templates may not allow public URLs
4. **Contact Bitrix support** - May be a platform limitation

## Alternative Solution

If public URLs don't work, consider:
- Using Bitrix file storage API to access documents
- Requesting documents via email/webhook instead of direct download
- Using a different authentication method for download URLs


