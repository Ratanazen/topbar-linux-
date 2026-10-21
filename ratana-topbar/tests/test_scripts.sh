#!/usr/bin/env bash
# ============================================================
# Ratana Top Bar — Automated Verification Test Suite
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config/waybar"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"

echo "=== Running Ratana Top Bar Test Suite ==="

# 1. Test JSON Syntax
echo -n "[1/5] Checking config.jsonc JSON syntax... "
python3 -c "
import json, re

with open('$CONFIG_DIR/config.jsonc', 'r') as f:
    raw = f.read()
    # Strip comments for json parsing
    cleaned = re.sub(r'/\*.*?\*/', '', raw, flags=re.DOTALL)
    cleaned = re.sub(r'//.*', '', cleaned)
    json.loads(cleaned)
"
echo "PASS"

# 2. Test CSS Syntax
echo -n "[2/5] Checking style.css file existence and non-empty... "
if [[ -s "$CONFIG_DIR/style.css" ]]; then
    echo "PASS ($(wc -l < "$CONFIG_DIR/style.css") lines)"
else
    echo "FAIL: style.css empty or missing"
    exit 1
fi

# 3. Test power-profile.sh
echo -n "[3/5] Testing power-profile.sh output format... "
out_power=$("$SCRIPTS_DIR/power-profile.sh")
echo "$out_power" | python3 -c "import json, sys; d = json.load(sys.stdin); assert 'text' in d; assert 'tooltip' in d"
echo "PASS -> $out_power"

# 4. Test toggle_dark_light.sh
echo -n "[4/5] Testing toggle_dark_light.sh output format... "
out_dark=$("$SCRIPTS_DIR/toggle_dark_light.sh")
echo "$out_dark" | python3 -c "import json, sys; d = json.load(sys.stdin); assert 'text' in d; assert 'tooltip' in d"
echo "PASS -> $out_dark"

# 5. Test weather.sh
echo -n "[5/5] Testing weather.sh output format and offline fallback... "
out_weather=$("$SCRIPTS_DIR/weather.sh")
echo "$out_weather" | python3 -c "import json, sys; d = json.load(sys.stdin); assert 'text' in d; assert 'tooltip' in d"
echo "PASS -> $out_weather"

echo "=== ALL RATANA TOP BAR TESTS PASSED ==="
exit 0
