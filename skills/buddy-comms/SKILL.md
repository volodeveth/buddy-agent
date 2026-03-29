---
name: buddy-comms
description: "MANDATORY for any contact or email operation. When user mentions a person's name, says 'контакт', 'дружина', 'email', 'імейл', 'напиши', 'надішли', '��найди контакт' — you MUST use this skill's exec scripts, NOT memory search."
trigger:
  - on_intent: send_email, send_message, contact_lookup, find_contact, find_person
  - on_keyword: контакт, імейл, email, напиши, надішли, дружина, дружині
priority: 70
tools:
  - exec
  - read
  - write
---

## CRITICAL: Contact operations require exec tool

When the user asks to find a contact, send an email, or mentions a person by name or role (дружина, колега, etc.):
1. You MUST call exec with contacts_lookup.py — do NOT search memory or guess
2. You MUST call exec with send_email.py to send — do NOT try other methods
3. Contact data lives in contacts.json, NOT in memory files

## Rules

1. Before sending ANY message, ALWAYS show the user:
   - Recipient (name + address/handle)
   - Subject/context (for email)
   - Full message text
   - Delivery method (email, Telegram, etc.)
2. Email -> MEDIUM security (confirmation from user)
3. Sending ON BEHALF of owner (impersonating) -> CRITICAL (PIN)
4. Contacts are ONLY from contacts.json (accessed via contacts_lookup.py)
5. Unknown contact -> ask for clarification, NEVER guess email/phone
6. For emails, use templates from message_templates/ when applicable
7. Always sign emails with owner's name (from USER.md)
8. CC/BCC -> show explicitly before sending
9. Attachments -> show file name and size before sending

## Contact Lookup

When user says "знайди контакт", "send to Oleg", "email Oleg", "напиши дружині", or ANY reference to a person:
1. ALWAYS call exec with contacts_lookup.py first:
```
python C:/Users/User/.openclaw/workspace/skills/buddy-comms/contacts_lookup.py "NAME"
```
2. If exact match -> use that contact
3. If multiple matches -> show list, ask to choose
4. If no match -> ask user for contact details, offer to save

## Email Sending

After user confirms, call exec:
```
python C:/Users/User/.openclaw/workspace/skills/buddy-comms/send_email.py "TO_EMAIL" "SUBJECT" "BODY" "FROM_NAME"
```

Optional additional args: cc, bcc, attachment_path

Result JSON:
- `{"status": "success", "to": "...", "subject": "..."}` -> tell user email sent
- `{"status": "error", "message": "..."}` -> tell user what went wrong

## Sending Telegram Messages

To send a Telegram message to a contact, use the built-in `message` tool (NOT exec):
```
message send --channel telegram --target "PHONE_OR_CHAT_ID" --message "TEXT"
```

Example: send to Ірина Дорош:
```
message send --channel telegram --target "+380937015185" --message "Привіт!"
```

IMPORTANT: Use the phone number from contacts.json as target. The `message` tool is built into OpenClaw — do NOT try to find a Python script for this.

## Adding New Contact

To add a contact, call exec:
```
python C:/Users/User/.openclaw/workspace/skills/buddy-comms/contacts_lookup.py --add "NAME" "EMAIL" "ROLE"
```
