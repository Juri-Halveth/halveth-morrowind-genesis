"""Source-bound character direction for the local Morrowind dialogue model.

Runtime observations and original roleplay direction remain separate. No world
action, quest stage or past encounter is invented by this module.
"""
import hashlib


VOICES = (
    'Spricht anschaulich und stellt eine kurze Gegenfrage.',
    'Spricht ruhig und waegt zwei konkrete Moeglichkeiten ab.',
    'Spricht direkt, mit trockenem Humor und wenig Ausschmueckung.',
    'Spricht aufmerksam und knuepft an das letzte Gespraech an.',
    'Spricht lebhaft, mit einem passenden Vergleich aus dem eigenen Beruf.',
    'Spricht bedacht und nennt zuerst den praktischen naechsten Schritt.',
)
SERVICE_LABELS = {
    'Barter': 'Handel', 'Spells': 'Zauberverkauf', 'Spellmaking': 'Zaubererstellung',
    'Enchanting': 'Verzauberung', 'Training': 'Ausbildung', 'Repair': 'Reparaturen',
    'Travel': 'Reisen',
}


def profile(npc, history=()):
    """Return a stable creative direction plus current, explicitly bound facts."""
    if not isinstance(npc, dict):
        return None
    identity = '\0'.join(str(npc.get(key, '')) for key in ('worldId', 'id', 'recordId'))
    seed = hashlib.sha256(identity.encode('utf-8')).digest()
    services = npc.get('services', [])
    services = services if isinstance(services, list) else []
    disposition = npc.get('disposition')
    if isinstance(disposition, (int, float)) and not isinstance(disposition, bool):
        attitude = 'zurueckhaltend' if disposition < 35 else 'zugewandt' if disposition >= 70 else 'abwartend'
    else:
        attitude = 'aus der aktuellen Begegnung noch offen'
    health = npc.get('health')
    wounded = (isinstance(health, dict) and isinstance(health.get('current'), (int, float))
               and isinstance(health.get('max'), (int, float)) and health['max'] > 0
               and health['current'] < health['max'] * .5)
    facts = {key: npc[key] for key in ('name', 'recordId', 'kind', 'cell', 'raceName',
             'className', 'classDescription', 'factions', 'disposition', 'health', 'isDead') if key in npc}
    creature = npc.get('kind') == 'creature'
    return {
        'version': 1,
        'runtimeFacts': facts,
        'services': [SERVICE_LABELS[key] for key in SERVICE_LABELS if key in services],
        'conversationContinuity': sum(1 for item in history if item.get('role') == 'user'),
        'roleplayDirection': {
            'origin': 'HALVETH authored interpretation; not original biography',
            'voice': VOICES[seed[0] % len(VOICES)],
            'attitudeFromDisposition': attitude,
            'currentConcern': 'eigene sichtbare Verletzung' if wounded else 'die aktuelle Frage und der eigene Beruf',
            'perspective': ('Beschreibe beobachtbares Verhalten dieses Wesens. Erfinde keine menschliche Biografie oder Rede fuer ein Tier.'
                            if creature else 'Antworte als diese Figur aus ihrem Beruf, ihren Zugehoerigkeiten und belegten Erinnerungen.'),
            'branchRule': 'Biete bei einem Problem hoechstens zwei passende Gespraechsansaetze an. Eine Idee veraendert keine Quest.',
            'continuityRule': 'Erinnere nur tatsaechliche Nachrichten dieser Figur. Lokale Gefuehle und Stil sind Rollenspiel, keine neuen historischen Tatsachen.',
        },
    }
