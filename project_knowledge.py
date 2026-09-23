"""Small, offline-only project design references, separate from game lore."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import unicodedata

DEFAULT_PATH = Path(__file__).resolve().parent / 'data' / 'project-knowledge.json'
MAX_QUERY_CHARS = 4000
MAX_CHAT_CARDS = 3
MAX_CONTEXT_CHARS = 6500
_STOP = frozenset('''aber alle alles also am an auch auf aus bei bitte das dass dein deine den der des die dies diese diesen dieser dieses doch du durch ein eine einem einen einer eines er es etwas fur geht gibt haben hallo hat hier ich im in ist ja jarvis kann kein keine machen mal man mehr mich mir mit muss nach nicht noch oder ohne seine sich sie sind so soll und uns unser unsere vom von vor war was welche welcher wenn werden wie wir wird wo zu zum zur uber jetzt schon spiel spiele spielwelt welt morrowind halveth quellen quelle idee ideen vorschlag vorschlage'''.split())


def _tokens(text):
    normalized = unicodedata.normalize('NFKD', text.casefold())
    normalized = ''.join(char for char in normalized if not unicodedata.combining(char))
    return {word for word in re.findall(r'[^\W_]{3,}', normalized)
            if word not in _STOP}


def _matches(query_word, source_word):
    if query_word == source_word:
        return True
    # A bounded suffix match covers German inflections, without fuzzy inventions.
    return (min(len(query_word), len(source_word)) >= 5
            and abs(len(query_word) - len(source_word)) <= 4
            and (query_word.startswith(source_word) or source_word.startswith(query_word)))


class ProjectKnowledge:
    def __init__(self, path=DEFAULT_PATH):
        source = Path(path).read_bytes()
        if len(source) > 128 * 1024:
            raise ValueError('Projektwissen überschreitet die lokale Paketgrenze.')
        cards = json.loads(source)
        if not isinstance(cards, list) or len(cards) > 64:
            raise ValueError('Projektwissen muss eine begrenzte Kartenliste sein.')
        seen = set()
        self._cards = []
        self._index = []
        for card in cards:
            if not isinstance(card, dict) or card.get('type') != 'DESIGN_REFERENCE':
                raise ValueError('Projektwissen benötigt den Typ DESIGN_REFERENCE.')
            for field in ('id', 'title', 'topic', 'summary', 'designUse', 'url', 'license'):
                if not isinstance(card.get(field), str) or not 1 <= len(card[field]) <= 4000:
                    raise ValueError('Unvollständige Projektwissenskarte: ' + field)
            provenance = card.get('provenance')
            if (not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,95}', card['id'])
                    or card['id'] in seen or not isinstance(provenance, dict)):
                raise ValueError('Ungültige Projektkartenkennung oder Provenienz.')
            commit = provenance.get('commitSha', '')
            blob = provenance.get('gitBlobSha', '')
            repository = provenance.get('repository', '')
            source_path = provenance.get('path', '')
            if (not isinstance(commit, str) or not re.fullmatch(r'[a-f0-9]{40}', commit)
                    or not isinstance(blob, str) or not re.fullmatch(r'[a-f0-9]{40}', blob)
                    or not isinstance(repository, str) or not repository.startswith('Juri-Halveth/')
                    or not isinstance(source_path, str) or not source_path
                    or not card['url'].startswith(f'https://github.com/{repository}/blob/{commit}/{source_path}#L')):
                raise ValueError('Projektquelle ist nicht an einen öffentlichen Commit gebunden.')
            keywords = card.get('keywords', [])
            if (not isinstance(keywords, list) or len(keywords) > 32
                    or any(not isinstance(word, str) or len(word) > 80 for word in keywords)):
                raise ValueError('Ungültige Suchwörter der Projektkarte.')
            seen.add(card['id'])
            self._cards.append(card)
            self._index.append((
                _tokens(' '.join(keywords)),
                _tokens(card['title'] + ' ' + card['topic']),
                _tokens(card['summary'] + ' ' + card['designUse']),
            ))

    def __len__(self):
        return len(self._cards)

    def all(self):
        return copy.deepcopy(self._cards)

    def search(self, query, limit=MAX_CHAT_CARDS):
        if not isinstance(query, str) or len(query) > MAX_QUERY_CHARS:
            raise ValueError('Projektwissenssuche benötigt höchstens 4000 Zeichen.')
        if type(limit) is not int or not 1 <= limit <= 64:
            raise ValueError('Ungültige Kartengrenze.')
        words = _tokens(query)
        if not words:
            return []
        matches = []
        for card, groups in zip(self._cards, self._index):
            score = sum(weight for word in words for group, weight in zip(groups, (4, 2, 1))
                        if any(_matches(word, token) for token in group))
            if score:
                matches.append((score, card['id'], card))
        matches.sort(key=lambda row: (-row[0], row[1]))
        return copy.deepcopy([row[2] for row in matches[:limit]])

    def chat_references(self, query):
        selected = []
        for card in self.search(query, MAX_CHAT_CARDS):
            reference = {key: card[key] for key in (
                'id', 'title', 'type', 'summary', 'designUse', 'url', 'provenance')}
            candidate = selected + [reference]
            if len(json.dumps(candidate, ensure_ascii=False)) <= MAX_CONTEXT_CHARS:
                selected.append(reference)
        return selected
