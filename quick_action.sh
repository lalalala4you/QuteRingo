#!/bin/bash
# Nihongo Sensei Quick Action
# Usage: Select Japanese text → right-click → Services → "Annotate Japanese"
# Or bind to keyboard shortcut in System Preferences → Keyboard → Shortcuts

TOOL="/Users/yilin/.openclaw/workspace/japanese-helper/nihongo_tool.py"
TMPFILE="/tmp/nihongo_output.txt"

# Read selected text from stdin (Automator passes it)
INPUT=$(cat)
if [ -z "$INPUT" ]; then
    osascript -e 'display notification "No text selected" with title "Nihongo Sensei"'
    exit 0
fi

# Run annotator
echo "$INPUT" | python3 "$TOOL" --format simple > "$TMPFILE"

# Show in a quick preview window
osascript << APPLESCRIPT
set theFile to "$TMPFILE"
set theContent to (do shell script "cat " & quoted form of theFile)
display dialog theContent with title "Nihongo Sensei 🔰" buttons {"Copy to Clipboard", "OK"} default button "OK"
if button returned of result is "Copy to Clipboard" then
    do shell script "cat " & quoted form of theFile & " | pbcopy"
    display notification "Copied annotated text to clipboard" with title "Nihongo Sensei"
end if
APPLESCRIPT
