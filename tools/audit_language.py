#!/usr/bin/env python3
"""Conservative German-language audit for the Herold-TTS source tree.

This is a lexical safety net, not a substitute for human translation review.
The application intentionally generates German speech: examples assigned to
text_de and sample speech data must not be translated.
"""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

EXTENSIONS = {'.md','.markdown','.rst','.txt','.csv','.py','.js','.ts','.tsx','.jsx','.html','.htm','.css','.scss','.yml','.yaml','.json','.toml','.ini','.cfg','.sh','.bash','.zsh','.dockerfile','.env','.xml'}
SPECIAL_NAMES = {'Dockerfile','Makefile','Containerfile','.gitlab-ci.yml','.dockerignore','.gitignore'}
# High-confidence cues; never use generic 'die', 'war', 'bin', 'so', 'in', etc.
PHRASES = re.compile(r'(?i)\b(?:schnellstart|überblick|einführung|voraussetzungen|installation|anleitung|bereitstellung|bereitstellen|fehlermeldung|fehlermeldungen|fehlgeschlagen|abgeschlossen|erfolgreich|wird\s+erstellt|wird\s+verwendet|hier\s+klicken|datei\s+(?:herunterladen|auswählen)|verzeichnis\s+erstellen|dienst\s+starten|nicht\s+gefunden|wird\s+geladen|ladevorgang|beschreibung|hinweise|achtung|beispielansage|sprachsynthese|stimmenauswahl|stimme\s+auswählen|ergebnis\s+(?:anzeigen|speichern)|inhaltsverzeichnis|erzeugt\s+(?:samples|dateien)|keine\s+dateien|bitte\s+(?:warten|prüfen|auswählen))\b')
UMLAUTS = re.compile(r'[äöüÄÖÜß]')
STRONG = re.compile(r'(?i)\b(?:deutsch(?:e|en|er|es)?|englisch(?:e|en|er|es)?|benutzeroberfläche|schaltfläche|geschwindigkeit|verarbeitung|fehlerbehandlung|gespeichert|erzeugung|konvertierung|benötigt|beachten|geprüft|erfolgt|ausgabeordner|einstellungen|verfügbar|ausgewählt|wiederholen)\b')
GERMAN_WORDS = re.compile(r'(?i)\b(?:und|oder|aber|jedoch|wenn|dann|weil|damit|dieser|diese|dieses|einem|einen|einer|eigenen|werden|wurde|wird|sind|kann|können|sollte|muss|müssen|haben|hat|wird|für|auf|mit|zum|zur|von|ohne|nicht|auch|noch|bereits|beim|nach|durch|vor|über|unter|alle|allem|immer|jetzt|hier|dort|erst|sofort|bitte|folge|folgende|siehe|zeigen|öffnen|nutzen|verwenden|starten|prüfen|erstellen|ausführen|ausgegeben|angezeigt|gelöscht|falls|sonst)\b')
# These are actual source-data keys, not prose to be translated.
SPEECH_FIELD = re.compile(r'(?i)(?:\btext_de\s*[:=]|["\']text_de["\']\s*:)')
TO_IGNORE = {'.git','.venv','venv','node_modules','dist','build','__pycache__','.mypy_cache','.pytest_cache'}
MAX_LENGTH = 500_000

def files_tracked(root: Path):
    proc=subprocess.run(['git','-C',str(root),'ls-files','-z'],capture_output=True)
    if proc.returncode: raise SystemExit('ERROR: run in a checked-out Git repository, not a bare clone')
    for raw in proc.stdout.split(b'\x00'):
        if not raw: continue
        rel=raw.decode('utf-8','surrogateescape')
        p=Path(rel)
        if any(part in TO_IGNORE for part in p.parts): continue
        if not(p.suffix.lower() in EXTENSIONS or p.name in SPECIAL_NAMES): continue
        yield rel

def classify(line: str):
    # Speech examples remain German by design. Check this line only, not adjacent documentation.
    if SPEECH_FIELD.search(line):
        return None
    # German quotation marks and punctuation alone are not necessarily German.
    high = bool(PHRASES.search(line))
    umlaut = bool(UMLAUTS.search(line))
    strong = bool(STRONG.search(line))
    words = len(GERMAN_WORDS.findall(line))
    if high: return 'high'
    if umlaut and (words or strong): return 'high'
    if strong and words >= 2: return 'high'
    if umlaut or strong or words >= 3: return 'review'
    return None

def is_intentional_speech(rel: str, line: str, in_speech: bool):
    """Allow explicit bilingual data while auditing all surrounding prose.

    Return (skip_this_line, speech_block_continues).
    The only special cases are the existing fixed speech reference and example fields.
    """
    stripped = line.strip()
    if rel == 'herold/config.py':
        if stripped.startswith('ref_text_de: str = ('):
            return True, True
        if in_speech:
            return True, not stripped.endswith(')')
    if rel == 'herold/audition.py':
        if stripped.startswith('TEXT_DE = ('):
            return True, True
        if in_speech:
            return True, not stripped.endswith(')')
    if rel == 'herold/static/index.html' and '<textarea id="text-de"' in stripped:
        return True, False
    if rel == 'resources/ansagen.yaml' and stripped.startswith('text_de:'):
        return True, False
    return False, False


def main():
    ap=argparse.ArgumentParser(description='Audit tracked files for likely German prose')
    ap.add_argument('repo',nargs='?',default='.')
    ap.add_argument('--json',action='store_true',help='machine-readable report')
    ap.add_argument('--strict',action='store_true',help='also fail on review-level matches')
    args=ap.parse_args()
    root=Path(args.repo).resolve()
    result=[]; inspected=0; skipped=0
    for rel in files_tracked(root):
        # This file contains German lexical patterns as audit data, not prose.
        if rel == 'tools/audit_language.py':
            continue
        path=root/rel
        if not path.is_file(): continue
        if path.stat().st_size>MAX_LENGTH: skipped+=1; continue
        try: data=path.read_text(encoding='utf-8')
        except (UnicodeError,OSError): skipped+=1; continue
        inspected+=1
        in_speech=False
        for number,line in enumerate(data.splitlines(),1):
            exempt,in_speech = is_intentional_speech(rel,line,in_speech)
            if exempt:
                continue
            verdict=classify(line)
            if verdict:
                result.append({'path':rel,'line':number,'severity':verdict,'text':line.strip()[:180]})
    high=sum(x['severity']=='high' for x in result)
    review=len(result)-high
    if args.json:
        print(json.dumps({'inspected':inspected,'skipped':skipped,'high':high,'review':review,'matches':result},ensure_ascii=False,indent=2))
    else:
        print(f'Language audit: {inspected} tracked text files inspected, {skipped} skipped')
        for match in result:
            print(f"{match['severity'].upper():6} {match['path']}:{match['line']}: {match['text']}")
        print(f'Findings: {high} high-confidence German indications, {review} manual-review indications')
        print('English prose must also be reviewed by a human. Explicit text_de and voice-reference speech remain German.')
    return 1 if (high or (args.strict and review)) else 0

if __name__=='__main__': sys.exit(main())
