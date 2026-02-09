# Feature: Administrators can view all emails

## Summary
Administrators with role 'admin' can now view all emails in the system when accessing "Todos los correos" (All Emails) instead of only their own emails.

## Changes Made

### 1. Modified `index()` route in `webmail/app.py`
**Location:** Lines 103-110

**Change:**
```python
# Build base query
# Admin users see all emails when folder is 'all'
if is_admin() and folder == 'all':
    query = {}
else:
    query = build_email_query(email_address)
```

**Explanation:** When an authenticated user accesses the main page with `folder='all'` and has admin role, the query is set to empty `{}`, which retrieves ALL emails from the database instead of filtering by the user's email address.

### 2. Modified `view_email()` route in `webmail/app.py`
**Location:** Lines 143-156

**Change:**
```python
# Verify access: admins can view any email, users can only view their own
if not is_admin():
    query = build_email_query(email_address)
    is_recipient = emails_collection.count_documents({
        '_id': ObjectId(email_id),
        "$or": query["$or"]
    }) > 0
    
    if not is_recipient:
        return render_template('error.html',
                              message='Access denied'), 403
```

**Explanation:** Administrators can now view any email without access restrictions. Regular users still can only view emails addressed to them.

## How to Use

1. Log in as an administrator (user with `role='admin'`)
2. Click on "Todos los correos" in the sidebar navigation
3. All emails in the system will be displayed, regardless of the recipient
4. Administrators can click on any email to view its full content

## User Roles

- **Regular Users:** Can only view emails addressed to their email address in all folders
- **Administrators:** 
  - "Bandeja de entrada" - Shows only their own emails
  - "No leídos" - Shows only their unread emails
  - "Todos los correos" - Shows ALL emails in the system

## Security

- The access control is properly enforced:
  - Regular users cannot access other users' emails
  - Administrators can view all emails only when explicitly viewing "Todos los correos"
  - The `view_email()` route checks admin privileges before bypassing recipient verification

## Testing

To test this feature:

1. Create or ensure you have an admin user
2. Send emails to different users in the system
3. Log in as admin
4. Navigate to "Todos los correos"
5. Verify that emails from all recipients are visible
6. Click on various emails to verify you can view them
7. Log in as a regular user and verify they still only see their own emails