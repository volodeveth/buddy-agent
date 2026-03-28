---
name: buddy-comms
description: Send emails and messages to contacts. Always shows preview before sending.
trigger:
  - on_intent: send_email, send_message, contact_lookup
priority: 70
tools:
  - shell
  - send_message
  - file_read
---

## Rules

1. Before sending ANY message, ALWAYS show the user:
   - Recipient (name + address/handle)
   - Subject/context (for email)
   - Full message text
   - Delivery method (email, Telegram, etc.)
2. Email -> MEDIUM security (confirmation button)
3. Sending ON BEHALF of owner -> CRITICAL (PIN)
4. Contacts ONLY from contacts.json
5. Unknown contact -> ask for clarification, NEVER guess
6. Always sign emails with owner's name
7. CC/BCC -> show explicitly before sending
