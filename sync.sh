#!/bin/bash
# Sync Buddy Agent repo → OpenClaw workspace
# Run after any changes in the repo to update the live bot

REPO="D:/Myapps/buddy agent"
WORKSPACE="C:/Users/User/.openclaw/workspace"

echo "=== Buddy Agent Sync ==="
echo "Repo:      $REPO"
echo "Workspace: $WORKSPACE"
echo ""

# Skills (sync code files, preserve generated/ in buddy-meta)
echo "[1/4] Syncing skills..."
for skill_dir in "$REPO"/skills/buddy-*/; do
    skill_name=$(basename "$skill_dir")
    mkdir -p "$WORKSPACE/skills/$skill_name"

    if [ "$skill_name" = "buddy-meta" ]; then
        # For buddy-meta: sync top-level files + templates/ but NOT generated/
        for f in "$skill_dir"/*.py "$skill_dir"/*.md "$skill_dir"/*.txt "$skill_dir"/*.json; do
            [ -f "$f" ] && cp "$f" "$WORKSPACE/skills/$skill_name/" 2>/dev/null
        done
        # Sync templates/ subdirectory
        if [ -d "$skill_dir/templates" ]; then
            mkdir -p "$WORKSPACE/skills/$skill_name/templates"
            cp -r "$skill_dir/templates/"* "$WORKSPACE/skills/$skill_name/templates/" 2>/dev/null
        fi
        echo "  ✓ $skill_name (preserved generated/)"
    else
        cp -r "$skill_dir"* "$WORKSPACE/skills/$skill_name/" 2>/dev/null
        echo "  ✓ $skill_name"
    fi
done

# Templates → workspace root (OpenClaw reads them from root)
echo "[2/4] Syncing templates..."
for tmpl in "$REPO"/templates/*.md; do
    cp "$tmpl" "$WORKSPACE/" 2>/dev/null
    echo "  ✓ $(basename "$tmpl")"
done

# Policies
echo "[3/4] Syncing policies..."
mkdir -p "$WORKSPACE/policies"
cp "$REPO"/policies/* "$WORKSPACE/policies/" 2>/dev/null
echo "  ✓ policies/"

# .env (only if exists and workspace copy is older or missing)
echo "[4/4] Syncing .env..."
if [ -f "$REPO/.env" ]; then
    cp "$REPO/.env" "$WORKSPACE/.env"
    echo "  ✓ .env"
else
    echo "  ⚠ .env not found in repo"
fi

echo ""
echo "=== Sync complete ==="
echo ""

# Quick health check
echo "--- Health Check ---"
ERRORS=0

# Check critical Python scripts are importable
for script in \
    "skills/buddy-comms/contacts_lookup.py" \
    "skills/buddy-comms/send_email.py" \
    "skills/buddy-security/pin_gate.py" \
    "skills/buddy-security/audit_log.py" \
    "skills/buddy-files/file_validator.py" \
    "skills/buddy-scheduler/scheduler.py" \
    "skills/buddy-voice-ua/stt_whisper.py" \
    "skills/buddy-search/search.py" \
    "skills/buddy-dev/dev.py" \
    "skills/buddy-utils/env_loader.py"; do
    if [ -f "$WORKSPACE/$script" ]; then
        python -c "import py_compile; py_compile.compile('$WORKSPACE/$script', doraise=True)" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "  ✓ $script"
        else
            echo "  ✗ $script (syntax error!)"
            ERRORS=$((ERRORS + 1))
        fi
    else
        echo "  ✗ $script (missing!)"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check .env has required vars
for var in OPENROUTER_API_KEY TELEGRAM_BOT_TOKEN SMTP_USER SMTP_APP_PASSWORD BUDDY_PIN_HASH; do
    if grep -q "^$var=" "$WORKSPACE/.env" 2>/dev/null; then
        echo "  ✓ .env: $var"
    else
        echo "  ✗ .env: $var missing!"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "✓ All checks passed. Buddy is ready."
else
    echo "✗ $ERRORS issue(s) found. Fix before running Buddy."
fi
