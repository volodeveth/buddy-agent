# Buddy Agent Memory

This file is always loaded into context. Contains persistent facts about the owner and active context.

## Owner
- Language: Ukrainian
- Timezone: Europe/Kyiv
- Stack: TypeScript, Next.js, Python
- Deploy targets: Vercel, Railway

## Active Projects
-> See memory/projects/

## Contacts — MANDATORY WORKFLOW

All contacts are stored in: `C:/Users/User/.openclaw/workspace/skills/buddy-comms/contacts.json`

When user mentions ANY person (by name, role like "дружина", or nickname):
1. FIRST: call exec tool to search contacts:
   ```
   python C:/Users/User/.openclaw/workspace/skills/buddy-comms/contacts_lookup.py "QUERY"
   ```
   This returns JSON with name, email, telegram ID, phone for matched contacts.

2. To send EMAIL: call exec tool:
   ```
   python C:/Users/User/.openclaw/workspace/skills/buddy-comms/send_email.py "EMAIL" "SUBJECT" "BODY" "Volodymyr"
   ```

3. To send TELEGRAM message: use message tool with the telegram ID from contacts:
   ```
   message send --channel telegram --target "TELEGRAM_ID" --message "TEXT"
   ```

NEVER guess contact info. NEVER say "I don't have this contact". ALWAYS run contacts_lookup.py first.
