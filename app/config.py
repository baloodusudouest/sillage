"""Réglages lus dans l'environnement du conteneur. Aucune valeur personnelle dans le code.

0.16 : les réglages d'usage (mots des temps forts, dossiers muets, place des vignettes, tags de Millésime) ne viennent
plus de la stack : ils se changent dans l'écran Réglages (fichier /data/reglages.json, classe maison.Reglages).
Leur ancienne variable n'est lue qu'une fois, au premier démarrage de la 0.16 (reprise), puis plus jamais.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import maison
from .chemin import MOTS

APPLI = "sillage"
IMMICH_PORT = 2283                     # 0.16 : port d'Immich sur le NAS, pour le lien quand l'Anneau ne connaît pas la tuile
CHAMBRE_NOIRE_URL = "http://chambre-noire:8100"   # 0.16 : Chambre noire vue depuis la stack (tag des scans non datés)

# 0.16 : réglages d'usage — clé → valeur par défaut (le type de la valeur par défaut fixe le type du réglage)
REGLAGES = {
    "mots": list(MOTS),                # mots qui font d'une étape un temps fort ; vide : la liste par défaut
    "dossiers_muets": [],              # noms de dossier qui ne disent rien, en plus de la liste par défaut
    "cache_mo": 500,                   # place des vignettes gardées sur disque (Mo) ; 0 : pas de cache
    "tag_estimee": "Date estimée",     # début des tags posés par Millésime (« Date estimée/1975 ±3 ») ; vide : pas lu
    "tag_non_datee": "",               # tag complet des scans pas encore datés ; vide : celui de Chambre noire, sinon pas lu
}
# Anciennes variables de la stack, lues une seule fois au premier démarrage (reprise), puis jamais plus
VARIABLES = {
    "mots": "SILLAGE_MOTS",
    "dossiers_muets": "SILLAGE_DOSSIERS_MUETS",
    "cache_mo": "SILLAGE_CACHE_MO",
    "tag_estimee": "SILLAGE_TAG_ESTIMEE",
    "tag_non_datee": "SILLAGE_TAG_NON_DATEE",
}


@dataclass(frozen=True)
class Config:
    password: str
    immich_url: str
    immich_cle: str
    data: Path
    static: Path
    carnet_url: str = ""             # adresse de carnet vue depuis la stack ; avec le jeton, la liste vient de carnet
    jeton: str = ""                  # 0.16 : MAISON_JETON, joint aux demandes à carnet et à Chambre noire ; vide : Immich seul
    jeton_ha: str = ""               # 0.5 : jeton de Home Assistant pour /ha/sejour ; vide : adresse fermée
    heure_frises: int = 2            # 0.13 : heure de la mise à jour nocturne des frises des invités (heure du conteneur, TZ)
    chambre_noire_url: str = CHAMBRE_NOIRE_URL
    attente_connexion: bool = True   # délai anti-essais ; coupé dans les tests
    preparer_au_demarrage: bool = False   # 0.25 : sillages manquants préparés au démarrage (vrai en service, coupé dans les tests)


def charger() -> Config:
    mot_de_passe = maison.mot_de_passe()                       # 0.16 : MAISON_PASSWORD seul
    if len(mot_de_passe) < 12:
        raise SystemExit("MAISON_PASSWORD est absent ou trop court (12 caractères au moins) : Sillage ne démarre pas.")
    cle = os.environ.get("SILLAGE_IMMICH_CLE", "").strip()
    if not cle:
        raise SystemExit("SILLAGE_IMMICH_CLE est absente : Sillage ne démarre pas (clé d'API Immich en lecture).")
    return Config(
        password=mot_de_passe,
        immich_url=os.environ.get("SILLAGE_IMMICH_URL", "http://immich_server:2283").rstrip("/"),
        immich_cle=cle,
        data=Path(os.environ.get("SILLAGE_DATA", "/data")),
        static=Path(__file__).parent / "static",
        carnet_url=os.environ.get("SILLAGE_CARNET_URL", "http://carnet:8096").rstrip("/"),
        jeton=maison.jeton_a_envoyer(),                                    # 0.16 : MAISON_JETON seul
        jeton_ha=os.environ.get("SILLAGE_JETON_HA", "").strip(),          # propre à Home Assistant : jamais le jeton commun
        heure_frises=int(h) % 24 if (h := (os.environ.get("SILLAGE_HEURE_FRISES") or "2").strip()).isdigit() else 2,
        preparer_au_demarrage=True,
    )
