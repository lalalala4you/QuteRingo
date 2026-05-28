#!/usr/bin/env python3
"""
Nihongo Sensei 🔰 — Japanese Text Annotator
Annotates Japanese text with: hiragana, katakana, romaji
Usage:
  echo "日本語" | python3 nihongo_tool.py
  python3 nihongo_tool.py "日本語のテキスト"
  python3 nihongo_tool.py --file input.txt
  python3 nihongo_tool.py --clipboard           # reads from clipboard
  python3 nihongo_tool.py --format table        # table output
  python3 nihongo_tool.py --format inline       # inline annotations
  python3 nihongo_tool.py --format ruby         # ruby markdown format
"""
import sys
import os
import re
import json
import pykakasi
import jaconv
import argparse
import subprocess

kks = pykakasi.kakasi()


def get_clipboard() -> str:
    """Get text from macOS clipboard."""
    result = subprocess.run(['pbpaste'], capture_output=True, text=True)
    return result.stdout.strip()


def set_clipboard(text: str):
    """Set text to macOS clipboard."""
    subprocess.run(['pbcopy'], input=text, text=True)


def strip_html(text: str) -> str:
    """Strip HTML tags and decode common entities from copied web text."""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    text = text.replace('&nbsp;', ' ').replace('　', '')
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_html(text: str) -> bool:
    """Heuristic check if text contains HTML."""
    return bool(re.search(r'<[a-zA-Z/][^>]*>', text))


def annotate(text: str) -> list[dict]:
    """Annotate Japanese text with readings. Returns list of word dicts."""
    return kks.convert(text)


def build_reading_with_romaji(annotations: list[dict]) -> str:
    """Build a single line with readings + romaji combined: 漢字(かな/romaji)"""
    parts = []
    for item in annotations:
        orig = item['orig']
        if orig.strip() == '':
            continue
        hira = item['hira']
        has_kanji = any('\u4e00' <= c <= '\u9fff' for c in orig)
        result = kks.convert(orig)
        roma = ' '.join(r.get('hepburn', r.get('hira', '')) for r in result)
        if has_kanji:
            parts.append(f"{orig}({hira}/{roma})")
        else:
            parts.append(f"{orig}({roma})")
    return ' '.join(parts)


def translate_vocabulary(words: list[str], api_key: str = None) -> dict[str, str]:
    """Get English meanings for individual Japanese words."""
    if not api_key:
        return {}
    import urllib.request, urllib.error, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    # Deduplicate and filter meaningful tokens
    unique = list(dict.fromkeys([w for w in words if len(w) > 1 and w.strip() not in ('。', '、', '「', '」', '（', '）', ',', '.')]))[:20]
    if not unique:
        return {}
    
    word_list = '\n'.join(unique)
    data = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a Japanese-English dictionary. For each Japanese word below, output ONLY: word = English meaning. No explanations, no extra text. Be concise."},
            {"role": "user", "content": word_list}
        ],
        "max_tokens": 300,
        "temperature": 0.1
    }).encode('utf-8')
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
            result = json.loads(resp.read())
            raw = result['choices'][0]['message']['content'].strip()
            meanings = {}
            for line in raw.split('\n'):
                if '=' in line:
                    w, m = line.split('=', 1)
                    meanings[w.strip()] = m.strip().capitalize()
            return meanings
    except Exception:
        return {}
    """Translate Japanese text to English using DeepSeek API."""
    if not api_key:
        return "(set DEEPSEEK_API_KEY for translation)"
    import urllib.request, urllib.error, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    data = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Translate the following Japanese text to natural English. Output ONLY the translation, no explanations."},
            {"role": "user", "content": text}
        ],
        "max_tokens": 500,
        "temperature": 0.3
    }).encode('utf-8')
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            result = json.loads(resp.read())
            return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"(translation failed: {e})"


def load_api_key() -> str | None:
    """Load DeepSeek API key from OpenClaw auth config."""
    # Try env var first
    key = os.environ.get('DEEPSEEK_API_KEY')
    if key:
        return key
    # Try OpenClaw auth profiles
    auth_path = os.path.expanduser('~/.openclaw/agents/main/agent/auth-profiles.json')
    try:
        with open(auth_path) as f:
            data = json.load(f)
            profile = data.get('profiles', {}).get('deepseek:default', {})
            return profile.get('key')
    except Exception:
        return None


def translate_ja_en(text: str, api_key: str = None) -> str:
    """Translate Japanese text to English using DeepSeek API."""
    if not api_key:
        return "(set DEEPSEEK_API_KEY for translation)"
    import urllib.request, urllib.error, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    data = json.dumps({
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Translate the following Japanese text to natural English. Output ONLY the translation, no explanations."},
            {"role": "user", "content": text}
        ],
        "max_tokens": 500,
        "temperature": 0.3
    }).encode('utf-8')
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            result = json.loads(resp.read())
            return result['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"(translation failed: {e})"


def format_reading(annotations: list[dict]) -> str:
    """Reading format with combined kana+romaji."""
    orig_parts = []
    
    for item in annotations:
        orig = item['orig']
        if orig.strip() == '':
            continue
        orig_parts.append(orig)
    
    orig_line = ''.join(orig_parts)
    reading_line = build_reading_with_romaji(annotations)
    
    return f"原文: {orig_line}\n━━━━━━━━━━━━\n読み: {reading_line}"


def format_web(annotations: list[dict], audio_b64: str = "", translation: str = None) -> str:
    """Floating popup — 原文 / 読み(furigana-style below kanji) / Romaji / Replay."""
    # Build 原文
    orig_parts = [item['orig'] for item in annotations if item['orig'].strip()]
    orig_line = ''.join(orig_parts)
    
    # Build 読み — furigana style: kanji on top, kana below in small text
    reads_rows = []
    for item in annotations:
        orig = item['orig']
        if not orig.strip():
            continue
        hira = item['hira']
        has_kanji = any('\u4e00' <= c <= '\u9fff' for c in orig)
        if has_kanji:
            reads_rows.append(f"<span class='fg'><span class='fg-top'>{hira}</span><span class='fg-bot'>{orig}</span></span>")
        else:
            reads_rows.append(f"<span class='fg'><span class='fg-top'>&nbsp;</span><span class='fg-bot'>{orig}</span></span>")
    reading_line = ''.join(reads_rows)
    
    # Build Romaji
    roma_parts = []
    for item in annotations:
        orig = item['orig']
        if not orig.strip():
            continue
        result = kks.convert(orig)
        roma = ' '.join(r.get('hepburn', r.get('hira', '')) for r in result)
        roma_parts.append(roma)
    roma_line = ' '.join(roma_parts)
    
    # Audio
    audio_html = ''
    if audio_b64:
        audio_html = f"""
    <audio id="audio" autoplay>
        <source src="data:audio/mp4;base64,{audio_b64}" type="audio/mp4">
    </audio>
"""
    # Translation
    trans_html = ''
    if translation:
        trans_html = f'<hr class="divider"><div class="label">🇬🇧 English</div><div class="roma">{translation}</div>'
    
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: -apple-system, 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', sans-serif;
  background: #1a1a2e; color: #eee; padding: 30px 34px;
}}
.label {{ font-size: 10px; color: #555; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 10px; }}
.orig {{ font-size: 22px; color: #fff; line-height: 1.8; margin-bottom: 22px; }}
.divider {{ border: none; border-top: 1px solid #2a2a4a; margin: 18px 0; }}
.fg-row {{ display: flex; flex-wrap: wrap; gap: 4px 12px; align-items: flex-end; }}
.fg {{ display: inline-flex; flex-direction: column; align-items: center; min-width: 28px; }}
.fg-top {{ font-size: 11px; color: #888; line-height: 1.3; }}
.fg-bot {{ font-size: 20px; color: #ddd; line-height: 1.3; }}
.roma {{ font-size: 15px; color: #555; line-height: 1.8; font-style: italic; }}
.replay {{
  width: 100%; margin-top: 24px; padding: 14px;
  background: #e94560; color: #fff; border: none; border-radius: 12px;
  font-size: 17px; cursor: pointer; transition: background 0.15s;
}}
.replay:hover {{ background: #c23152; }}
</style>
</head>
<body>
  {audio_html}
  <div class="label">原文</div>
  <div class="orig">{orig_line}</div>
  <hr class="divider">
  <div class="label">読み</div>
  <div class="fg-row">{reading_line}</div>
  <hr class="divider">
  <div class="label">🔤 Romaji</div>
  <div class="roma">{roma_line}</div>
  {trans_html}
  <button class="replay" onclick="document.getElementById('audio').play()">🔊 Play Again</button>
</body>
</html>"""


def format_inline(annotations: list[dict]) -> str:
    """Inline format: 日本語(にほんご/Nihongo)"""
    parts = []
    for item in annotations:
        orig = item['orig']
        hira = item['hira']
        # Skip pure kana/punctuation — only annotate kanji-containing words
        has_kanji = any('\u4e00' <= c <= '\u9fff' for c in orig)
        if has_kanji or orig.strip().isascii() == False:
            # Get romaji for this segment
            romaji = jaconv.hira2kata(jaconv.kata2hira(hira))
            # Better romaji via pykakasi
            result = kks.convert(orig)
            roma_parts = []
            for r in result:
                roma_parts.append(r.get('hepburn', r.get('hira', '')))
            roma = ' '.join(roma_parts)
            parts.append(f"{orig}（{hira}／{roma}）")
        else:
            parts.append(orig)
    return ''.join(parts)


def format_table(annotations: list[dict]) -> str:
    """Table format with columns: Original | Hiragana | Katakana | Romaji"""
    lines = []
    lines.append(f"{'Original':<12} {'Hiragana':<16} {'Katakana':<16} {'Romaji':<16}")
    lines.append("-" * 64)

    for item in annotations:
        orig = item['orig']
        if orig.strip() in ('', '\n', ' ', '　'):
            lines.append('')
            continue

        hira = item['hira']
        kata = jaconv.hira2kata(hira) if hira else ''
        
        # Romaji
        result = kks.convert(orig)
        roma_parts = [r.get('hepburn', r.get('hira', '')) for r in result]
        romaji = ' '.join(roma_parts)

        lines.append(f"{orig:<12} {hira:<16} {kata:<16} {romaji:<16}")

    return '\n'.join(lines)


def format_ruby(annotations: list[dict]) -> str:
    """Ruby markdown format for apps that support it."""
    parts = []
    for item in annotations:
        orig = item['orig']
        hira = item['hira']
        has_kanji = any('\u4e00' <= c <= '\u9fff' for c in orig)
        if has_kanji:
            parts.append(f"<ruby>{orig}<rt>{hira}</rt></ruby>")
        else:
            parts.append(orig)
    return ''.join(parts)


def format_simple(annotations: list[dict]) -> str:
    """Simple format: 日本語 = にほんご (Nihongo)"""
    lines = []
    for item in annotations:
        orig = item['orig']
        if orig.strip() in ('', '\n', ' ', '　'):
            continue
        hira = item['hira']
        result = kks.convert(orig)
        roma_parts = [r.get('hepburn', r.get('hira', '')) for r in result]
        romaji = ' '.join(roma_parts)
        
        has_kanji = any('\u4e00' <= c <= '\u9fff' for c in orig)
        if has_kanji:
            lines.append(f"{orig}  =  {hira}  ({romaji})")
        else:
            lines.append(f"{orig}  ({romaji})")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Nihongo Sensei — Japanese Text Annotator')
    parser.add_argument('text', nargs='?', help='Japanese text to annotate')
    parser.add_argument('--file', '-f', help='Read from file')
    parser.add_argument('--clipboard', '-c', action='store_true', help='Read from clipboard')
    parser.add_argument('--format', '-F', choices=['inline', 'table', 'ruby', 'simple', 'reading', 'web'],
                        default='reading', help='Output format (default: reading)')
    parser.add_argument('--copy', action='store_true', help='Copy result to clipboard')
    parser.add_argument('--clean', action='store_true', help='Strip HTML tags from input')
    parser.add_argument('--speak', '-s', action='store_true', help='Speak the original text aloud (macOS voice)')
    parser.add_argument('--audio', '-a', type=str, metavar='FILE', help='Save spoken audio to file (.m4a)')
    parser.add_argument('--voice', '-v', type=str, default='Kyoko', help='macOS voice (default: Kyoko). Try: Otoya, Hattori')
    parser.add_argument('--web', '-w', action='store_true', help='Open interactive web page with annotation + audio player')
    parser.add_argument('--translate', '-t', action='store_true', help='Add English translation')
    args = parser.parse_args()

    # Get input text
    text = None
    if args.clipboard:
        text = get_clipboard()
    elif args.file:
        with open(args.file, 'r') as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        # Read from stdin (pipe)
        if not sys.stdin.isatty():
            text = sys.stdin.read().strip()
        else:
            parser.print_help()
            sys.exit(1)

    # Check if we have any text
    if not text:
        print("🔰 Nihongo Sensei — Select Japanese text and run again!")
        sys.exit(0)

    # Auto-detect and strip HTML from copied web text
    if is_html(text) or args.clean:
        text = strip_html(text)
        if not any('\u3000' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9fff' for c in text):
            print("🔰 No Japanese text found — try copying from a Japanese webpage.")
            sys.exit(0)

    # Annotate
    annotations = annotate(text)

    # If web mode: generate HTML + floating popup
    if args.web or args.format == 'web':
        import tempfile, base64
        tmpdir = tempfile.mkdtemp(prefix='nihongo_')
        audio_path = os.path.join(tmpdir, 'speech.m4a')
        
        # Generate audio
        aiff_path = audio_path.replace('.m4a', '.aiff')
        subprocess.run(['say', '-v', args.voice, '-o', aiff_path, text], capture_output=True)
        subprocess.run(['afconvert', '-f', 'm4af', '-d', 'aac', '-s', '3', aiff_path, audio_path], capture_output=True)
        if os.path.exists(aiff_path):
            os.remove(aiff_path)
        
        # Embed audio as base64
        audio_b64 = ''
        if os.path.exists(audio_path):
            with open(audio_path, 'rb') as f:
                audio_b64 = base64.b64encode(f.read()).decode()
        
        # Translation
        trans = None
        if args.translate:
            key = load_api_key()
            if key:
                print("🌐 Translating...", file=sys.stderr)
                trans = translate_ja_en(text, key)
        
        # Generate HTML
        html = format_web(annotations, audio_b64, trans)
        
        # Get screen size
        result = subprocess.run(
            ['osascript', '-e', 'tell application "Finder" to get bounds of window of desktop'],
            capture_output=True, text=True
        )
        screen_w, screen_h = 1440, 900
        if result.returncode == 0:
            parts = result.stdout.strip().split(', ')
            if len(parts) == 4:
                screen_w = int(parts[2]) - int(parts[0])
                screen_h = int(parts[3]) - int(parts[1])
        
        w = int(screen_w * 0.7)
        h = int(screen_h * 0.5)
        
        import webview
        webview.create_window(
            title='Nihongo Sensei 🔰',
            html=html,
            width=w,
            height=h,
            x=int((screen_w - w) / 2),
            y=int((screen_h - h) / 2),
            resizable=True,
            on_top=True
        )
        webview.start()
        sys.exit(0)

    # Annotate
    annotations = annotate(text)

    # Format
    formatters = {
        'inline': format_inline,
        'table': format_table,
        'ruby': format_ruby,
        'simple': format_simple,
        'reading': format_reading,
        'web': None,  # handled above
    }
    output = formatters[args.format](annotations)

    print(output)
    
    if args.copy:
        set_clipboard(output)
        print("\n📋 Copied to clipboard!")
    
    # Audio: speak or save
    if args.speak or args.audio:
        print()
        # Prepare clean text for TTS (strip HTML if needed)
        tts_text = strip_html(text) if is_html(text) else text
        
        if args.speak:
            print(f"🔊 Speaking with {args.voice}...")
            subprocess.run(['say', '-v', args.voice, tts_text])
        
        if args.audio:
            outfile = args.audio
            if not outfile.endswith('.m4a'):
                outfile += '.m4a'
            print(f"💾 Saving audio to {outfile}...")
            subprocess.run(['say', '-v', args.voice, '-o', outfile.replace('.m4a', '.aiff'), tts_text])
            # Convert aiff → m4a using macOS built-in afconvert
            aiff = outfile.replace('.m4a', '.aiff')
            if os.path.exists(aiff):
                result = subprocess.run(
                    ['afconvert', '-f', 'm4af', '-d', 'aac', '-s', '3', aiff, outfile],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    os.remove(aiff)
                    print(f"✅ Audio saved: {outfile} ({os.path.getsize(outfile)/1024:.0f} KB)")
                else:
                    print(f"⚠️  AAC conversion failed: {result.stderr.strip()}")
                    os.rename(aiff, outfile.replace('.m4a', '.aiff'))
                    print(f"✅ Audio saved as AIFF: {outfile.replace('.m4a', '.aiff')}")


if __name__ == '__main__':
    main()
