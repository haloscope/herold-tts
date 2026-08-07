# ADR 0004: Commit-Konventionen — Englisch, Zeitstempel-Anonymisierung auf 12:00 UTC

**Status:** Akzeptiert (2026-08-07)

## Kontext

Die Commit-Historie enthielt gemischtsprachige Messages (Deutsch/Englisch) und exakte
Uhrzeiten, aus denen sich persönliche Arbeitszeitmuster der Beteiligten ablesen lassen
(Tagesrhythmen, Wochentage mit Uhrzeit). Für den Fall einer späteren Veröffentlichung des
Repos oder erweiterten Zugriffs sollen solche Muster nicht ableitbar sein. Bewusst
verworfen wurde die Alternative, Zeitstempel auf Zeiten *außerhalb* üblicher Arbeitszeiten
zu verschieben: Das würde ein gezielt falsches Bild der Entstehungszeiten fabrizieren.
Gewählt wurde stattdessen eine erkennbar synthetische, neutrale Normalisierung.

## Entscheidung

1. **Commit-Messages einheitlich Englisch und sachlich** im Conventional-Commit-Stil
   (`feat:`/`fix:`/`docs:`/`chore:`). Per History-Rewrite wurden deutsche Messages
   übersetzt und saloppe Messages (z. B. „late commit :D", „readme", „housekeeping")
   durch präzise Beschreibungen des tatsächlichen Commit-Inhalts ersetzt.
2. **Zeitstempel-Anonymisierung:** Author- und Committer-Date jedes Commits werden auf
   **12:00:00 UTC des jeweiligen (lokalen) Commit-Datums** gesetzt. Das Datum bleibt
   erhalten, die Uhrzeit ist für alle Commits identisch und offensichtlich synthetisch.
3. **Gilt rückwirkend und künftig:** Die gesamte Historie (alle Branches) wurde am
   2026-08-07 per `git filter-repo` umgeschrieben. Neue Commits werden mit
   `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE = <heute>T12:00:00Z` erstellt (siehe CLAUDE.md).

## Konsequenzen

- **Alle Commit-Hashes haben sich geändert.** Hash-Referenzen in älteren AARs/CHANGELOG-
  Einträgen zeigen auf die Vor-Rewrite-Historie und sind nur noch narrativ zu verstehen.
- Jeder Checkout muss einmalig hart nachgezogen werden:
  `git fetch origin && git reset --hard origin/main`.
- Auf dem GitLab-Server können alte Objekte (mit Original-Zeitstempeln) bis zur nächsten
  Housekeeping-/GC-Runde bzw. in Pipeline-Metadaten (keep-around-Refs) erhalten bleiben —
  die Anonymisierung wirkt vollständig erst nach serverseitigem Housekeeping und schützt
  primär gegen künftige Leser der Historie.
- Ein lokales Backup der Vor-Rewrite-Historie liegt als Bundle außerhalb des Repos
  (`~/herold/herold-tts-pre-rewrite-*.bundle`) und kann nach Verifikation gelöscht werden.
- Commits mehrerer am selben Tag haben identische Timestamps; die Reihenfolge ergibt sich
  weiterhin aus der Graph-Topologie, nicht aus der Uhrzeit.
