"""Réglages lus dans l'environnement du conteneur. Aucune valeur personnelle dans le code."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import maison

APPLI = "sillage"


@dataclass(frozen=True)
class Config:
    password: str
    immich_url: str
    immich_cle: str
    data: Path
    static: Path
    immich_adresse: str = ""         # adresse d'Immich dans le navigateur (lien « Ouvrir dans Immich ») ; 0.15 : repli de l'annuaire
    mots: tuple[str, ...] = ()       # mots qui font d'une étape un temps fort ; vide : la liste par défaut
    immich_port: int = 0             # port d'Immich sur le NAS : sans adresse réglée, le lien vise le même hôte que Sillage
    carnet_url: str = ""             # adresse de carnet vue depuis la stack ; avec le jeton, la liste vient de carnet
    carnet_jeton: str = ""           # jeton envoyé à carnet : SILLAGE_CARNET_JETON, puis MAISON_JETON (0.15) ; vide : personnes d'Immich
    jeton_ha: str = ""               # 0.5 : jeton de Home Assistant pour /ha/sejour ; vide : adresse fermée
    muets: tuple[str, ...] = ()      # noms de dossier qui ne disent rien, en plus de la liste par défaut
    cache_mo: int = 500              # 0.10 : place des vignettes gardées sur disque (Mo) ; 0 : pas de cache
    heure_frises: int = 2            # 0.13 : heure de la mise à jour nocturne des frises des invités (heure du conteneur, TZ)
    tag_estimee: str = "Date estimée"   # 0.14 : début des tags posés par Millésime (« Date estimée/1975 ±3 ») ; vide : pas lu
    tag_non_datee: str = ""          # 0.14 : tag complet des scans pas encore datés (celui de Millésime) ; vide : pas lu
    attente_connexion: bool = True   # délai anti-essais ; coupé dans les tests


def charger() -> Config:
    mot_de_passe = maison.mot_de_passe("SILLAGE_PASSWORD")      # 0.15 : MAISON_PASSWORD, repli sur l'ancien nom
    if len(mot_de_passe) < 12:
        raise SystemExit("MAISON_PASSWORD (ou SILLAGE_PASSWORD) est absent ou trop court (12 caractères au moins) : "
                         "Sillage ne démarre pas.")
    cle = os.environ.get("SILLAGE_IMMICH_CLE", "").strip()
    if not cle:
        raise SystemExit("SILLAGE_IMMICH_CLE est absente : Sillage ne démarre pas (clé d'API Immich en lecture).")
    return Config(
        password=mot_de_passe,
        immich_url=os.environ.get("SILLAGE_IMMICH_URL", "http://immich_server:2283").rstrip("/"),
        immich_cle=cle,
        data=Path(os.environ.get("SILLAGE_DATA", "/data")),
        static=Path(__file__).parent / "static",
        immich_adresse=os.environ.get("SILLAGE_IMMICH_ADRESSE", "").rstrip("/"),
        immich_port=int(os.environ.get("SILLAGE_IMMICH_PORT") or 0) if (os.environ.get("SILLAGE_IMMICH_PORT") or "0").strip().isdigit() else 0,
        carnet_url=os.environ.get("SILLAGE_CARNET_URL", "http://carnet:8096").rstrip("/"),
        carnet_jeton=maison.jeton_a_envoyer("SILLAGE_CARNET_JETON"),   # 0.15 : l'ancien jeton d'abord, puis MAISON_JETON
        jeton_ha=os.environ.get("SILLAGE_JETON_HA", "").strip(),          # propre à Home Assistant : jamais le jeton commun
        muets=tuple(m.strip() for m in os.environ.get("SILLAGE_DOSSIERS_MUETS", "").split(",") if m.strip()),
        cache_mo=int(os.environ.get("SILLAGE_CACHE_MO") or 500) if (os.environ.get("SILLAGE_CACHE_MO") or "500").strip().isdigit() else 500,
        heure_frises=int(h) % 24 if (h := (os.environ.get("SILLAGE_HEURE_FRISES") or "2").strip()).isdigit() else 2,
        tag_estimee=os.environ.get("SILLAGE_TAG_ESTIMEE", "Date estimée").strip().rstrip("/"),
        tag_non_datee=os.environ.get("SILLAGE_TAG_NON_DATEE", "").strip(),
        mots=tuple(m.strip().lower() for m in os.environ.get("SILLAGE_MOTS", "").split(",") if m.strip()),
    )
