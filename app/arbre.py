"""0.22 : l'arbre de famille d'une personne, pour la vue 3D (constellation et hélice).

L'arbre vient de carnet (`GET /sillage/arbre`, jeton commun), qui le tient de Treemich. Sillage n'en garde rien sur
disque : il le lit, le garde dix minutes en mémoire, et en tire la partie reliée à la personne (ou aux invités).

Pour un invité, tout est décidé ici, côté serveur (règle du conseil du 27/11/2026, retenue par Julien) : ce qui est
caché n'est jamais envoyé au navigateur.
- personne décédée (date de décès connue, ou décès sans date), ou née il y a plus de 100 ans : nom, visage et dates ;
- personne vivante majeure : nom, visage, année de naissance seulement ;
- personne mineure, ou dont l'âge n'est pas connu (aucune date) : prénom seulement, ni visage ni date ;
- case « jamais aux invités » cochée dans carnet : rien (un point sans nom), ses liens restent pour que l'arbre tienne.
Les identifiants de Treemich et de carnet ne sortent jamais vers un invité : chaque personne y a un identifiant opaque.
"""
from __future__ import annotations

import re
from collections import deque
from datetime import date

ANNEE = re.compile(r"^(\d{4})")
CENTENAIRE = 100
MAJEUR = 18


def annee(texte: str | None) -> int | None:
    m = ANNEE.match(texte or "")
    return int(m.group(1)) if m else None


def voisins(liens: list[dict]) -> dict[str, set[str]]:
    v: dict[str, set[str]] = {}
    for l in liens:
        v.setdefault(l["de"], set()).add(l["vers"])
        v.setdefault(l["vers"], set()).add(l["de"])
    return v


def a_des_liens(graphe: dict, tid: str) -> bool:
    return any(tid in (l["de"], l["vers"]) for l in graphe.get("liens") or [])


def relies(graphe: dict, departs: list[str]) -> set[str]:
    """Toutes les personnes reliées (par n'importe quel chemin de liens) à l'une des personnes de départ."""
    v = voisins(graphe.get("liens") or [])
    vus, file_ = set(), deque(d for d in departs if d)
    while file_:
        x = file_.popleft()
        if x in vus:
            continue
        vus.add(x)
        file_.extend(v.get(x, ()))
    return vus


def generations(ids: set[str], liens: list[dict], depart: str) -> dict[str, int]:
    """Rang de génération de chaque personne (0 = la plus ancienne). Parcours depuis la personne de départ : un parent
    est une génération au-dessus, un enfant au-dessous, un conjoint ou un frère au même rang. Le premier rang trouvé
    reste (une boucle ou un doublon de Treemich ne fait pas tourner en rond)."""
    pas: dict[str, list[tuple[str, int]]] = {}
    for l in liens:
        if l["de"] not in ids or l["vers"] not in ids:
            continue
        if l["type"] == "parent":
            pas.setdefault(l["de"], []).append((l["vers"], 1))
            pas.setdefault(l["vers"], []).append((l["de"], -1))
        else:
            pas.setdefault(l["de"], []).append((l["vers"], 0))
            pas.setdefault(l["vers"], []).append((l["de"], 0))
    rang: dict[str, int] = {}
    for racine in [depart] + sorted(ids - {depart}):
        if racine in rang or racine not in ids:
            continue
        rang[racine] = 0
        file_ = deque([racine])
        while file_:
            x = file_.popleft()
            for y, d in pas.get(x, ()):
                if y not in rang:
                    rang[y] = rang[x] + d
                    file_.append(y)
    bas = min(rang.values(), default=0)
    return {k: r - bas for k, r in rang.items()}


def statut(p: dict, aujourd_hui: date) -> str:
    """« decede », « vivant » (majeur), « mineur » ou « inconnu » (aucune date de naissance)."""
    if p.get("decede") or p.get("deces"):
        return "decede"
    a = annee(p.get("naissance"))
    if a is None:
        return "inconnu"
    age = aujourd_hui.year - a
    if age > CENTENAIRE:
        return "decede"
    return "mineur" if age < MAJEUR else "vivant"


def prenom(nom: str) -> str:
    return (nom or "").strip().split(" ")[0]
