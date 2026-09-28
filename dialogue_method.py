"""Small, versioned conversation adapter for hypothesis-revision-cycle.v1."""
from __future__ import annotations

import re

METHOD_ID = 'hypothesis-revision-cycle.v1'
METHOD_VERSION = '1.0.0'

_INQUIRY = re.compile(
    r'\b(?:hypothes\w*|gegenmodell\w*|vermut\w*|ursach\w*|vorhersag\w*|'
    r'warum|weshalb|wieso|vergleich\w*|(?:über|ueber)?pr[üu]f\w*)\b'
    r'|\b(?:was passiert|was wäre|was waere|woran erkenne|woher weiß|woher weiss)\b',
    re.IGNORECASE,
)


def dialogue_method(message: str, *, npc: bool = False) -> tuple[str, dict]:
    """Return bounded prompt guidance and its descriptive context, never actions.

    The lexical cue selects a response style, not truth or a permission. Ordinary
    greetings and conversation do not receive the investigative response format.
    """
    active = bool(_INQUIRY.search(message))
    context = {
        'id': METHOD_ID,
        'version': METHOD_VERSION,
        'active': active,
        'selection': 'QUESTION_CUE' if active else 'ORDINARY_CONVERSATION',
        'presentation': 'NPC_IN_CHARACTER' if npc else 'JARVIS_CONCISE',
        'authorityEffect': 'NONE',
    }
    guidance = (
        'Zeitbezug: Trenne belegte vergangene Ereignisse, die aktuelle beobachtete '
        'Spiellage und zukünftige Vorhersagen. Ein früherer Gesprächssatz ist eine '
        'Äußerung, kein Beleg einer ausgeführten Tat; eine Vorhersage bleibt bedingt. '
        'Eine alte Erinnerung ist keine neue Beobachtung. '
    )
    if active:
        guidance += (
            'Bei dieser prüfenden Frage verwende die Arbeitsweise '
            'hypothesis-revision-cycle.v1: Benenne die Vermutung als Hypothese, '
            'eine plausible andere Erklärung als Gegenmodell und eine konkrete '
            'Beobachtung, die beide unterscheiden würde. Nenne vor einer '
            'vorgeschlagenen Prüfung die nötige Minimum-Evidenz und die Bedingung, '
            'unter der du deine Einschätzung ändern würdest. Gib als Ergebnis '
            'nur den belegten Stand und den offenen Rest wieder. Fehlt eine '
            'entscheidende Beobachtung, bleibt die Frage offen. '
            'Fasse das passend zur Frage in wenigen natürlichen Sätzen zusammen; '
            'keine sechsteilige Checkliste und keine erfundene Messung. '
            'Eine Prüfidee führt selbst keine Aktion aus. '
        )
    else:
        guidance += (
            'Dies ist ein gewöhnliches Gespräch: Antworte natürlich auf das '
            'Anliegen, ohne Hypothesenformular oder methodische Checkliste. '
        )
    if npc:
        guidance += (
            'Bleibe als NPC in deiner Rolle und deinem belegten Wissensrahmen. '
            'Drücke Zweifel und Prüfideen in der Sprache dieser Figur aus; '
            'nenne keine Methodik-IDs, Softwareprozesse oder Prüfprotokolle. '
        )
    return guidance, context
