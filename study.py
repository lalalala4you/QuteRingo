#!/usr/bin/env python3
"""
Nihongo Sensei — Study Mode
Annotates all reading materials and saves annotated copies.
Usage: python3 study.py
       python3 study.py arashi   # just the Arashi material
"""
import sys
import os
from nihongo_tool import annotate, format_simple, format_table

MATERIALS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'materials')

def study_file(filepath):
    name = os.path.basename(filepath).replace('.md', '')
    with open(filepath) as f:
        content = f.read()
    
    # Split into sections: heading lines stay as-is, content gets annotated
    lines = content.split('\n')
    result = []
    in_table = False
    
    for line in lines:
        # Skip empty lines, markdown tables, already-annotated lines
        if not line.strip():
            result.append('')
            continue
        if line.strip().startswith('|'):
            result.append(line)
            continue
        if line.strip().startswith('#'):
            result.append(line)
            continue
        if line.strip().startswith('- '):
            result.append(line)
            continue
        
        # Annotate the line
        if any('\u4e00' <= c <= '\u9fff' or '\u3040' <= c <= '\u309f' 
               or '\u30a0' <= c <= '\u30ff' for c in line):
            annotations = annotate(line)
            annotated = format_simple(annotations)
            result.append(f"**原文:** {line}")
            result.append(f"**読み:** {annotated}")
            result.append('')
        else:
            result.append(line)
    
    output = '\n'.join(result)
    outpath = os.path.join(MATERIALS_DIR, f'{name}_annotated.md')
    with open(outpath, 'w') as f:
        f.write(output)
    print(f'✅ {outpath}')


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else None
    
    if target:
        filepath = os.path.join(MATERIALS_DIR, f'{target}.md')
        if os.path.exists(filepath):
            study_file(filepath)
        else:
            available = [f.replace('.md', '') for f in os.listdir(MATERIALS_DIR) 
                        if f.endswith('.md') and '_annotated' not in f]
            print(f"❌ No material '{target}'. Available: {', '.join(available)}")
    else:
        for f in sorted(os.listdir(MATERIALS_DIR)):
            if f.endswith('.md') and '_annotated' not in f:
                study_file(os.path.join(MATERIALS_DIR, f))


if __name__ == '__main__':
    main()
