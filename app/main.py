"""Sillage : le chemin de vie d'une personne, lu dans Immich. Lecture seule.

Routes : /health (publique), /api/session, /api/connexion, /api/deconnexion, /api/personnes,
/api/chemin/{personne} (et /marque), /api/portrait/{personne},
/api/vignette/{photo}, /api/services, /api/reglages, /api/restaurer, /externe/sauvegarde (jeton commun), puis l'interface.
Invités : /api/invite/{jeton} (et /album/{photo}, /vignette/{photo}, /signalement/{photo}).
Millésime : /externe/signalements et /externe/signalements/traite (jeton commun).
Gazette : /externe/personnes/{immich_id}/etapes (jeton commun, 0.20).

0.17 : les invités signalent une date fausse (« Pas la bonne année ? ») ou datent une photo de « Aidez-moi à dater ».
Côté invité, une photo n'est jamais nommée par son identifiant Immich : identifiant opaque propre à Sillage
(HMAC court par invitation et photo). Millésime lit les avis en attente et les ferme ; Sillage n'écrit rien dans Immich.

0.16 : les réglages d'usage (mots des temps forts, dossiers muets, place des vignettes, tags de Millésime) se changent
dans l'écran Réglages, sans redémarrer ; leur ancienne variable n'est lue qu'au premier démarrage. L'Anneau collecte
les réglages chaque nuit (/externe/sauvegarde) ; « Restaurer les réglages » en relit une sauvegarde. Anciens noms
retirés : MAISON_PASSWORD seul, MAISON_JETON seul vers carnet, adresse d'Immich par l'annuaire seul (puis même hôte, port 2283).

0.14 : les scans datés par Millésime (tag « Date estimée/AAAA ±N ») entrent dans le chemin, dits « vers 1975 » ;
ceux qui attendent une date (tag des non datées) restent à part, comptés. La date de décès d'une personne
vient de carnet seulement (qui la tient de Treemich, d'iCloud ou de sa fiche) : Sillage ne la saisit pas (0.14.1).

0.15 : variables communes de la maison (app/maison.py, copie du socle) : MAISON_PASSWORD, jeton commun envoyé à carnet,
adresse d'Immich pour le navigateur lue dans l'annuaire de l'Anneau (tuile « Immich »).

0.13 : la frise d'une invitation est préparée dès que Home Assistant la pose, gardée dans la base, et refaite
chaque nuit (SILLAGE_HEURE_FRISES, 2 h par défaut) avec les photos ajoutées : l'invité ne fait jamais attendre Immich.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
import unicodedata
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from starlette.background import BackgroundTask

from . import __version__, chemin as calcul, maison
from .base import ISSUES, SORTES, Base, quand_tz
from .cache import Cache
from .auth import COMMUN, DUREE, Sessions, en_https
from .config import APPLI, IMMICH_PORT, REGLAGES, VARIABLES, Config, charger
from .immich import ErreurImmich, Immich

ETAT: dict = {}
PUBLIQUES = ("/api/connexion", "/api/session")
IMAGES = ("/api/portrait/", "/api/vignette/")
MEMOIRE = 600            # secondes pendant lesquelles un chemin ou la liste des personnes est gardé
LUES_MAX = 50            # M26 : personnes dont les photos restent en mémoire (les plus anciennes partent)
UUID = re.compile(r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
VERROU = threading.Lock()
log = logging.getLogger("sillage")
ANNUAIRE = maison.Annuaire()      # 0.15 : adresses des services lues dans l'Anneau (jeton commun), gardées dix minutes
# 0.16 : réglages qui ne sortent jamais par /externe/sauvegarde (aucun aujourd'hui : rien de secret dans ceux de Sillage ;
# maison.est_secret écarte de toute façon un nom qui ressemble à un secret)
EXCLUS: tuple[str, ...] = ()
JOUR = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 0.17 : dates signalées par les invités
OPAQUE = re.compile(r"^[0-9a-f]{24}$")    # identifiant d'une photo côté invité (jamais l'identifiant Immich)
LIMITE_AVIS = 100                         # avis en attente par invitation au-delà desquels Sillage refuse (429)
AIDEZ_MAX = 12                            # photos de « Aidez-moi à dater »
MOT_MAX = 120                             # longueur du mot libre d'un avis
GARDE_TRAITES = 90                        # jours pendant lesquels un avis traité reste avant d'être effacé
REGARDEE_JOURS = 30                       # jours pendant lesquels l'invité lit « Julien a regardé, la date reste »
ETAPES_MAX = 60                           # 0.20 : étapes rendues à la Gazette par /externe/personnes/…/etapes
MERCI = "Merci, c'est transmis à Julien"
TROP = "Julien a déjà beaucoup de photos à regarder : revenez un peu plus tard."


def adresse_immich(hote: str = "") -> str:
    """Adresse d'Immich pour le navigateur (lien « Ouvrir dans Immich ») : l'annuaire de l'Anneau (tuile « Immich »,
    adresse privée si la page vient de Tailscale). 0.16 : plus de variable de repli ; vide, l'interface vise le même
    hôte que Sillage sur le port d'Immich (`immich_port`, 2283)."""
    return ANNUAIRE.adresse("Immich", prive=maison.est_prive(hote))


def _reglage(cle: str):
    """0.16 : la valeur actuelle d'un réglage d'usage (écran Réglages)."""
    return ETAT["reglages"].get(cle)


def _fichier_generation(cfg: Config) -> Path:
    return cfg.data / "session_generation"


def _lire_generation(cfg: Config) -> int:
    try:
        return int(_fichier_generation(cfg).read_text().strip())
    except (OSError, ValueError):
        return 0


@asynccontextmanager
async def cycle(app: FastAPI):
    cfg = ETAT.get("cfg") or charger()
    cfg.data.mkdir(parents=True, exist_ok=True)
    ETAT.setdefault("immich", Immich(cfg.immich_url, cfg.immich_cle))
    # 0.16 : réglages d'usage ; au premier démarrage, chaque ancienne variable posée est reprise une fois
    reglages_ = maison.Reglages(cfg.data / "reglages.json", REGLAGES, VARIABLES)
    for k in reglages_.repris:
        log.warning("Réglage « %s » repris de %s (première fois) ; il se change désormais dans Réglages.", k, VARIABLES[k])
    ETAT.update(cfg=cfg, sessions=Sessions(APPLI, cfg.password, _lire_generation(cfg)),
                personnes=None, lues={}, albums={}, connues={}, derniere_lecture=None, toutes=None, invites={}, reperes=None,
                reglages=reglages_, base=Base(cfg.data / "sillage.db"),
                cache=Cache(cfg.data / "vignettes", reglages_.get("cache_mo")),
                fond=[], verrous={}, nuit=None)
    # 0.17 : clé des identifiants de photos montrés aux invités, tirée une fois et gardée dans la base
    if not ETAT["base"].reglage("cle_photos"):
        ETAT["base"].poser_reglage("cle_photos", secrets.token_hex(32))
    ETAT["cle_photos"] = bytes.fromhex(ETAT["base"].reglage("cle_photos"))
    _effacer_avis_traites()
    # Les invitations posées sans frise (base d'avant la 0.13, arrêt pendant une préparation) sont préparées au démarrage ;
    # 0.17 : celles d'avant la 0.17 aussi (sans dates des photos ni « Aidez-moi à dater »)
    manquantes = [i["jeton"] for i in ETAT["base"].invitations()
                  if i["jeton"] not in ETAT["base"].preparees() or "_dates" not in (ETAT["base"].frise(i["jeton"]) or ({},))[0]]
    if manquantes:
        _en_fond(_preparer, manquantes)
    # 0.18 : santé des tâches de fond (socle 0.9.0) — chaque boucle se déclare, chaque tour est suivi dans /health
    maison.TACHES.declarer(TACHE_NUIT, periode_s=86400, type="reguliere")
    maison.TACHES.declarer(TACHE_PREPARATION, type="demande")
    nuit = asyncio.create_task(_chaque_nuit())
    # 0.18 : copie cohérente de la base chaque nuit (heure de Paris), dans <données>/copies
    copie = asyncio.create_task(maison.planifier_copie(APPLI, [cfg.data / "sillage.db"], cfg.data / "copies",
                                                       maison.HEURES_COPIE[APPLI]))
    yield
    nuit.cancel()
    copie.cancel()
    for fil in ETAT["fond"]:
        fil.join(timeout=10)
    ETAT["base"].fermer()


app = FastAPI(title=APPLI, version=__version__, lifespan=cycle, docs_url=None, redoc_url=None)


@app.middleware("http")
async def garde(request: Request, appel):
    chemin = request.url.path
    if chemin.startswith("/ha/"):
        # 0.5 : Home Assistant prépare les invitations des chambres, avec son propre jeton
        jeton = ETAT["cfg"].jeton_ha
        if not jeton or not hmac.compare_digest(request.headers.get("authorization", "").encode(), f"Bearer {jeton}".encode()):
            return JSONResponse({"detail": "Jeton manquant ou invalide."}, status_code=401)
    elif chemin.startswith("/api/") and chemin not in PUBLIQUES and not chemin.startswith("/api/invite/") \
            and not ETAT["sessions"].connecte(request.cookies):
        return JSONResponse({"detail": "Connexion nécessaire."}, status_code=401)
    reponse = await appel(request)
    if chemin.startswith(("/api/", "/ha/")) and not chemin.startswith(IMAGES) and "/vignette/" not in chemin:
        reponse.headers["Cache-Control"] = "no-store"
    return reponse


@app.exception_handler(ErreurImmich)
async def _immich(_: Request, exc: ErreurImmich):
    return JSONResponse({"detail": str(exc)}, status_code=502)


@app.get("/health")
def sante(request: Request):
    # 0.18 : + version_socle, taches, copie_base (socle 0.9.0) ; messages d'erreur seulement avec le jeton commun
    # ou une session valide
    return {"ok": True, "version": __version__, "frises_pretes": len(ETAT["base"].preparees()),
            **maison.sante(request, jeton_commun=maison.jetons(), session_ok=ETAT["sessions"].connecte(request.cookies))}


# ================================================================ connexion

@app.get("/api/session")
def session(request: Request):
    s = ETAT["sessions"]
    return {"connecte": s.connecte(request.cookies), "version": __version__}


@app.post("/api/connexion")
async def connexion(request: Request, corps: dict = Body(...)):
    s = ETAT["sessions"]
    if ETAT["cfg"].attente_connexion:
        await asyncio.sleep(s.attente())
    if not s.verifier_mot_de_passe(str(corps.get("mot_de_passe", ""))):
        raise HTTPException(401, "Mot de passe incorrect.")
    r = JSONResponse({"ok": True})
    r.set_cookie(s.cookie, s.creer(), max_age=DUREE, httponly=True, samesite="strict", secure=en_https(request))
    return r


@app.post("/api/deconnexion")
def deconnexion():
    s = ETAT["sessions"]
    s.generation += 1
    try:
        _fichier_generation(ETAT["cfg"]).write_text(str(s.generation))
    except OSError:
        pass
    r = JSONResponse({"ok": True})
    r.delete_cookie(s.cookie)
    r.delete_cookie(COMMUN)      # « Se déconnecter » ferme aussi la connexion commune
    return r


# ================================================================ personnes

def _de_carnet() -> tuple[dict[str, dict], str]:
    """Les fiches de carnet liées à une personne d'Immich : identifiant Immich → fiche. Une lecture seule,
    avec le jeton de Sillage. Rend aussi la raison quand carnet ne répond pas (alors : Immich seul)."""
    cfg = ETAT["cfg"]
    if not cfg.jeton:
        return {}, ""
    try:
        with httpx.Client(timeout=10, transport=ETAT.get("carnet_transport")) as client:
            r = client.get(cfg.carnet_url + "/sillage/personnes", headers={"Authorization": f"Bearer {cfg.jeton}"})
        if r.status_code == 401:
            return {}, "carnet refuse le jeton de Sillage."
        r.raise_for_status()
        return {p["immich_id"]: p for p in r.json()["personnes"] if p.get("immich_id")}, ""
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        log.warning("carnet ne répond pas : %s", exc.__class__.__name__)
        return {}, "carnet ne répond pas."


def _personnes(frais: bool = False) -> dict[str, dict]:
    """Les personnes que Sillage connaît, gardées dix minutes : celles des fiches de carnet liées à Immich,
    et les personnes nommées et non masquées d'Immich. Le nom de la fiche passe devant celui d'Immich ;
    la date de naissance est toujours celle d'Immich."""
    garde_ = ETAT["personnes"]
    if garde_ and not frais and time.monotonic() - garde_[0] < MEMOIRE:
        return garde_[1]
    fiches, erreur = _de_carnet()
    liste = {}
    for p in ETAT["immich"].personnes():
        fiche = fiches.get(p["id"])
        if fiche:
            liste[p["id"]] = {**p, "name": fiche.get("nom") or p.get("name") or "", "carnet": True,
                              "proche": bool(fiche.get("proche")), "decede": bool(fiche.get("decede")),
                              **_fin(fiche)}
        elif (p.get("name") or "").strip() and not p.get("isHidden"):
            liste[p["id"]] = {**p, "carnet": False}
    ETAT["personnes"] = (time.monotonic(), liste)
    ETAT["carnet"] = {"regle": bool(ETAT["cfg"].jeton), "erreur": erreur, "fiches": len(fiches)}
    ETAT["derniere_lecture"] = time.time()
    return liste


def _fin(fiche: dict) -> dict:
    """0.14 : la date de décès d'une personne, celle de carnet quand la fiche en a une complète.
    0.14.1 : plus de saisie dans Sillage ; la date se met dans carnet ou dans Treemich."""
    de_carnet = calcul.jour(fiche.get("deces"))
    return {"fin": de_carnet.isoformat(), "fin_source": "carnet"} if de_carnet else {}


def _tag_de_chambre_noire() -> tuple[str, str]:
    """0.16 : le tag des scans non datés que pose Chambre noire (GET /externe/noms, jeton commun), quand Réglages le
    laisse vide. Rend (tag, raison si Chambre noire ne le donne pas) ; sans jeton commun, rien n'est demandé."""
    cfg = ETAT["cfg"]
    if not cfg.jeton:
        return "", ""
    try:
        with httpx.Client(timeout=5, transport=ETAT.get("chambre_noire_transport")) as client:
            r = client.get(cfg.chambre_noire_url + "/externe/noms", headers={"Authorization": f"Bearer {cfg.jeton}"})
        if r.status_code in (401, 404):
            return "", "Chambre noire refuse le jeton commun."
        r.raise_for_status()
        j = r.json()
        return (str(j.get("tag_non_datee") or "").strip() if j.get("regle") else ""), ""
    except (httpx.HTTPError, ValueError, AttributeError) as exc:
        log.warning("Chambre noire ne répond pas : %s", exc.__class__.__name__)
        return "", "Chambre noire ne répond pas."


def _reperes(frais: bool = False) -> tuple[dict[str, tuple[int, int]], set[str]]:
    """0.14 : les scans datés par Millésime (photo → (année, marge)) et ceux qui attendent une date, lus par leurs
    tags et gardés dix minutes. Sans droit de lire les tags, le chemin se fait sans eux (Connexion le dit).
    0.16 : les deux tags viennent de Réglages ; celui des non datées vide, il est demandé à Chambre noire."""
    garde_ = ETAT.get("reperes")
    if garde_ and not frais and time.monotonic() - garde_[0] < MEMOIRE:
        return garde_[1], garde_[2]
    tag_estimee = str(_reglage("tag_estimee") or "").strip().rstrip("/")
    tag_non_datee, source, raison = str(_reglage("tag_non_datee") or "").strip(), "reglages", ""
    if not tag_non_datee:
        tag_non_datee, raison = _tag_de_chambre_noire()
        source = "chambre-noire" if tag_non_datee else ""
    estimees: dict[str, tuple[int, int]] = {}
    non_datees: set[str] = set()
    etat = {"lu": False, "erreur": "", "estimees": 0, "non_datees": 0,
            "regle": bool(tag_estimee or tag_non_datee), "tag_non_datee": tag_non_datee, "source": source,
            "chambre_noire": raison}
    if etat["regle"]:
        try:
            tags = ETAT["immich"].etiquettes()
            for t in tags:
                valeur = t.get("value") or ""
                trouve = calcul.estimation(valeur, tag_estimee)
                if trouve:
                    for i in ETAT["immich"].ids_du_tag(t["id"]):
                        estimees[i] = trouve
                elif tag_non_datee and valeur == tag_non_datee:
                    non_datees.update(ETAT["immich"].ids_du_tag(t["id"]))
            etat.update(lu=True, estimees=len(estimees), non_datees=len(non_datees - set(estimees)))
            if tag_non_datee and not any((t.get("value") or "") == tag_non_datee for t in tags):
                d_ou = "réglé dans Réglages" if source == "reglages" else "donné par Chambre noire"
                etat["erreur"] = f"Le tag des scans non datés {d_ou} est introuvable dans Immich."
        except ErreurImmich as exc:
            log.warning("Tags illisibles : %s", exc)
            etat["erreur"] = str(exc)
    ETAT["reperes"] = (time.monotonic(), estimees, non_datees)
    ETAT["reperes_etat"] = etat
    return estimees, non_datees


@app.get("/api/personnes")
def personnes(frais: bool = False):
    """La liste d'ouverture. Avec carnet : ses fiches d'abord, les autres personnes d'Immich se trouvent par la recherche."""
    aujourd_hui = date.today()
    sortie = []
    for p in _personnes(frais).values():
        naissance = calcul.jour(p.get("birthDate"))
        sortie.append({"id": p["id"], "nom": p["name"].strip(), "naissance": naissance.isoformat() if naissance else None,
                       "age": calcul.age(naissance, aujourd_hui) if naissance and not p.get("decede") and not p.get("fin") else None,
                       "fin": p.get("fin"), "carnet": bool(p.get("carnet")), "proche": bool(p.get("proche")),
                       "decede": bool(p.get("decede") or p.get("fin"))})
    par_carnet = any(p["carnet"] for p in sortie)
    return {"personnes": sorted(sortie, key=lambda p: calcul._plat(p["nom"])), "par_carnet": par_carnet,
            "carnet": ETAT.get("carnet", {})}


def _mots() -> tuple[str, ...]:
    return tuple(m.strip().lower() for m in _reglage("mots") if m.strip())


def _muets() -> tuple[str, ...]:
    return tuple(m.strip() for m in _reglage("dossiers_muets") if m.strip())


def _noms_d_albums(photos: list[str]) -> dict[str, str]:
    """Le nom d'album de chaque photo phare, lu une fois puis gardé (huit lectures de front)."""
    connus: dict[str, str] = ETAT["albums"]
    a_lire = [p for p in photos if p not in connus]
    if a_lire:
        with ThreadPoolExecutor(max_workers=8) as file_:
            for photo, nom in zip(a_lire, file_.map(ETAT["immich"].album_de, a_lire)):
                connus[photo] = nom
    return {p: connus[p] for p in photos if connus.get(p)}


def _chemin(personne: str, frais: bool = False, hote: str = "") -> dict:
    """Le chemin d'une personne. Les photos lues dans Immich sont gardées dix minutes : une correction
    recalcule le chemin sans rien relire."""
    fiche = _personnes().get(personne)
    if not fiche:
        raise HTTPException(404, "Personne inconnue de Sillage.")
    resultat = _calcul_du_chemin(personne, fiche, frais)
    resultat["immich"] = adresse_immich(hote)                    # annuaire de l'Anneau
    resultat["immich_port"] = IMMICH_PORT                          # 0.16 : repli sans variable, calculé par l'interface
    return resultat


def _calcul_du_chemin(personne: str, fiche: dict, frais: bool = False) -> dict:
    """0.20 : le calcul du chemin seul (sans l'adresse d'Immich), pour l'écran et pour /externe/personnes/…/etapes."""
    garde_ = ETAT["lues"].get(personne)
    if not garde_ or frais or time.monotonic() - garde_[0] > MEMOIRE:
        if frais:
            ETAT["albums"].clear()
            _reperes(frais=True)
        garde_ = (time.monotonic(), list(ETAT["immich"].photos_de(personne)))
        with VERROU:
            lues = ETAT["lues"]
            lues.pop(personne, None)
            lues[personne] = garde_                    # M26 : la dernière lue passe en fin de table
            while len(lues) > LUES_MAX:
                del lues[next(iter(lues))]             # la plus anciennement lue part
            ETAT["connues"].update({p["id"]: p.get("checksum") or "" for p in garde_[1] if calcul.visible(p)})
    estimees, non_datees = _reperes()
    return calcul.calculer(fiche, garde_[1], _noms_d_albums, _mots(), ETAT["base"].marques(personne), _muets(),
                           estimees=estimees, non_datees=non_datees)


@app.get("/api/chemin/{personne}")
def chemin(personne: str, request: Request, frais: bool = False):
    return _chemin(personne, frais, request.headers.get("host", ""))


@app.post("/api/chemin/{personne}/marque")
def marquer(personne: str, request: Request, corps: dict = Body(...)):
    """Une correction : « ce n'est pas elle », retirer une photo, choisir la photo phare, nommer ou masquer une étape.
    `effacer` : les photos dont on retire la marque ; `poser` : la photo qui la reçoit (aucune : on ne fait que retirer).
    Rien n'est écrit dans Immich."""
    if personne not in _personnes():
        raise HTTPException(404, "Personne inconnue de Sillage.")
    sorte, valeur = str(corps.get("sorte", "")), str(corps.get("valeur") or "").strip()[:200]
    if sorte not in SORTES:
        raise HTTPException(422, "Correction inconnue.")
    connues = ETAT["connues"]
    demandees = [str(i) for i in (corps.get("effacer") or [])] + ([str(corps["poser"])] if corps.get("poser") else [])
    if not demandees or any(not connues.get(i) for i in demandees):
        raise HTTPException(404, "Photo inconnue de Sillage : relis le chemin.")
    if sorte == "titre" and corps.get("poser") and not valeur:
        raise HTTPException(422, "Le nom est vide.")
    ETAT["base"].marquer(personne, sorte, [connues[str(i)] for i in (corps.get("effacer") or [])],
                         connues[str(corps["poser"])] if corps.get("poser") else None, valeur)
    # 0.13 : les frises d'invités où paraît cette personne sont refaites avec la correction
    _oublier([i["jeton"] for i in ETAT["base"].invitations() if any(p["id"] == personne for p in i["personnes"])])
    return _chemin(personne, hote=request.headers.get("host", ""))


# ================================================================ invités des chambres (0.5)

def _toutes() -> list[dict]:
    """Toutes les personnes nommées d'Immich (masquées comprises), gardées dix minutes : pour retrouver un invité."""
    garde_ = ETAT["toutes"]
    if not garde_ or time.monotonic() - garde_[0] > MEMOIRE:
        garde_ = (time.monotonic(), [p for p in ETAT["immich"].personnes() if (p.get("name") or "").strip()])
        ETAT["toutes"] = garde_
    return garde_[1]


def _trouver(nom: str) -> dict | None:
    """La personne d'Immich qui porte exactement ce nom (comme l'intégration des chambres : à l'identique,
    puis sans accents ni majuscules). Deux personnes du même nom : aucune, on ne devine pas."""
    import unicodedata
    voulu = unicodedata.normalize("NFC", nom.strip())
    for egal in (lambda p: unicodedata.normalize("NFC", p["name"].strip()) == voulu,
                 lambda p: calcul._plat(p["name"].strip()) == calcul._plat(voulu)):
        trouves = [p for p in _toutes() if egal(p)]
        if len(trouves) == 1:
            return trouves[0]
        if len(trouves) > 1:
            return None
    return None


@app.post("/ha/sejour")
def sejour(corps: dict = Body(...)):
    """Home Assistant prépare l'invitation d'une chambre pour son séjour : les noms des invités, le dernier jour.
    Rend le chemin de la page à afficher (/invite/<jeton>), valable jusqu'au lendemain midi. Sans nom : l'invitation
    de la chambre est retirée. Rien n'est écrit dans Immich."""
    chambre = str(corps.get("chambre", "")).strip()[:40]
    if not chambre:
        raise HTTPException(422, "Chambre manquante.")
    noms = [str(n).strip() for n in (corps.get("noms") or []) if str(n).strip()][:4]
    if not noms:
        ETAT["base"].retirer_invites(chambre)
        return {"chemin": "", "trouves": [], "manquants": [], "expire": None}
    try:
        dernier = date.fromisoformat(str(corps.get("jusqu_au", ""))[:10])
    except ValueError:
        raise HTTPException(422, "Date de fin illisible (AAAA-MM-JJ).")
    if not date.today() <= dernier <= date.today() + timedelta(days=400):
        raise HTTPException(422, "Date de fin hors du séjour possible.")
    expire = datetime.combine(dernier + timedelta(days=1), datetime.min.time()).replace(hour=12).isoformat(timespec="seconds")
    try:
        du = date.fromisoformat(str(corps.get("du") or "")[:10]).isoformat() if corps.get("du") else ""
    except ValueError:
        du = ""                                          # 0.6 : facultative, ne bloque rien
    trouves, manquants = [], []
    for n in noms:
        p = _trouver(n)
        (trouves.append({"id": p["id"], "nom": n}) if p else manquants.append(n))
    jeton = ETAT["base"].poser_invite(chambre, trouves or [{"id": "", "nom": n} for n in noms], expire, du)
    if not ETAT["base"].frise(jeton):                # nouvelle invitation : sa frise se prépare tout de suite, en fond
        _en_fond(_preparer, [jeton])
    return {"chemin": f"/invite/{jeton}", "trouves": [t["nom"] for t in trouves], "manquants": manquants, "expire": expire}


def _pour_invite(c: dict, photos_etapes: dict | None = None) -> dict:
    """Ce qu'un invité voit d'un chemin : les étapes visibles, la photo phare de chacune. Ni corrections,
    ni photos mises de côté, ni lien vers Immich. 0.12.1 : `photos_etapes` (phare → photos de l'étape, images seules)
    est rempli à part, pour « Voir l'album » ; il ne part jamais tel quel vers l'invité."""
    chapitres = []
    for ch in c["chapitres"]:
        if photos_etapes is not None:
            for e in ch["etapes"]:
                if not e["masquee"]:
                    photos_etapes.setdefault(e["phare"], []).extend(p["id"] for p in e.get("photos", []) if not p["video"])
        etapes = [{k: e.get(k) for k in ("cle", "nom", "debut", "fin", "quand", "fois", "age", "vers", "nombre", "phare", "temps_fort")}
                  for e in ch["etapes"] if not e["masquee"]]
        if etapes:
            chapitres.append({"cle": ch["cle"], "titre": ch["titre"], "etapes": etapes})
    return {"nom": c["personne"]["nom"], "chapitres": chapitres, "etapes": sum(len(ch["etapes"]) for ch in chapitres)}


def _personnes_sur(photo: dict) -> set[str]:
    return {x["id"] for x in photo.get("people") or [] if x.get("id")}


def _ensemble(gens: list[dict], fiches: dict, lire_marques, photos_etapes: dict | None = None) -> dict | None:
    """0.7 : la frise de plusieurs invités. Les moments communs (photos où ils sont tous), et pour chacun ses photos
    seul ou avec les hôtes de la maison (réglage « hôtes ») : une photo où il y a quelqu'un d'autre n'est pas prise.
    Chaque étape dit à qui elle est (`qui` : « ensemble » ou le rang de l'invité), par décennie du calendrier."""
    hotes = {h["id"] for h in ETAT["base"].reglage("hotes", [])}
    ids = [g["id"] for g in gens]
    noms = [g["nom"] for g in gens]
    marques_communes: dict = {}
    for g in gens:
        for empreinte, m in lire_marques(g["id"]).items():
            marques_communes.setdefault(empreinte, {}).update(m)
    groupes = [("ensemble", {"id": ids[0], "name": ", ".join(noms[:-1]) + " et " + noms[-1]},
                list(ETAT["immich"].photos_ensemble(ids)), marques_communes)]
    for rang, g in enumerate(gens):
        permis = {g["id"]} | hotes
        a_lui = [p for p in ETAT["immich"].photos_de(g["id"]) if _personnes_sur(p) <= permis]
        groupes.append((rang, {**fiches.get(g["id"], {"id": g["id"]}), "name": g["nom"]}, a_lui, lire_marques(g["id"])))
    chapitres: dict[str, dict] = {}
    for qui, fiche, photos, marques in groupes:
        if not photos:
            continue
        estimees, non_datees = _reperes()
        for ch in _pour_invite(calcul.calculer(fiche, photos, _noms_d_albums, _mots(), marques, _muets(),
                                               decennies=True, estimees=estimees, non_datees=non_datees), photos_etapes)["chapitres"]:
            dest = chapitres.setdefault(ch["cle"], {"cle": ch["cle"], "titre": ch["titre"], "etapes": []})
            dest["etapes"] += [{**e, "cle": f"{qui}-{e['cle']}", "qui": qui} for e in ch["etapes"]]
    if not any(ch["etapes"] for ch in chapitres.values()):
        return None
    ordre = sorted(chapitres.values(), key=lambda ch: min(e["debut"] for e in ch["etapes"]))
    for ch in ordre:
        ch["etapes"].sort(key=lambda e: (e["debut"], str(e["qui"])))
    return {"nom": groupes[0][1]["name"], "ensemble": True, "invites": noms, "chapitres": ordre,
            "etapes": sum(len(ch["etapes"]) for ch in ordre)}


def _calculer(inv: dict) -> dict:
    """La frise d'une invitation, lue dans Immich (le travail lent). Rend un dictionnaire gardable en JSON :
    ce que voit l'invité, plus les clés « _ » qui ne partent jamais vers lui."""
    gens = [p for p in inv["personnes"] if p["id"]]
    fiches = {p["id"]: p for p in _toutes()}
    lire_marques = ETAT["base"].marques
    commun, chacun, photos_etapes = None, [], {}
    if len(gens) > 1:
        commun = _ensemble(gens, fiches, lire_marques, photos_etapes)
    elif gens:
        g = gens[0]
        fiche = {**fiches.get(g["id"], {"id": g["id"]}), "name": g["nom"]}
        estimees, non_datees = _reperes()
        c = _pour_invite(calcul.calculer(fiche, ETAT["immich"].photos_de(g["id"]), _noms_d_albums, _mots(),
                                         lire_marques(g["id"]), _muets(), estimees=estimees, non_datees=non_datees), photos_etapes)
        chacun = [c] if c["etapes"] else []
    resultat = {"invites": [p["nom"] for p in inv["personnes"]], "commun": commun, "chacun": chacun,
                "accueil": commun is None and not chacun}
    phares = sorted({e["phare"] for c in ([commun] if commun else []) + chacun for ch in c["chapitres"] for e in ch["etapes"]})
    # Les photos où un invité est reconnu servent à « Voir l'album » (0.12.1) : lues ici, pas au clic de l'invité.
    # M25 (audit du 17/11/2026) : même filtre que le chemin (rien d'archivé, de masqué ni de verrouillé ; à plusieurs,
    # photo de tous les invités ou d'un seul avec les hôtes, jamais avec quelqu'un d'autre).
    hotes = {h["id"] for h in ETAT["base"].reglage("hotes", [])} if len(gens) > 1 else set()
    tous = {g["id"] for g in gens}
    # 0.17 : la date que l'invité voit de chaque photo (None : pas encore datée) et « Aidez-moi à dater » : les photos
    # d'un invité hors du chemin faute de date (tag des non datées, sans estimation), sauf celles que Julien a écartées.
    estimees, non_datees = _reperes()
    photos_gens: set[str] = set()
    dates: dict[str, str | None] = {}
    aidez: dict[str, str] = {}
    for g in gens:
        marques = lire_marques(g["id"])
        for p in ETAT["immich"].photos_de(g["id"]):
            if not calcul.visible(p) or not (len(gens) == 1 or tous <= _personnes_sur(p) or _personnes_sur(p) <= {g["id"]} | hotes):
                continue
            photos_gens.add(p["id"])
            sans_date = p["id"] in non_datees and p["id"] not in estimees
            quand = calcul.date_de(p)
            dates[p["id"]] = None if sans_date or quand is None else quand.date().isoformat()
            ecartee = {"pas_elle", "retiree"} & set(marques.get(p.get("checksum") or "", {}))
            if sans_date and not ecartee:
                aidez.setdefault(p["id"], p.get("localDateTime") or p.get("fileCreatedAt") or "")
    return {**resultat, "_phares": phares, "_gens": [g["id"] for g in gens], "_photos_etapes": photos_etapes,
            "_photos_gens": sorted(photos_gens), "_dates": dates,
            "_aidez": [i for i, _ in sorted(aidez.items(), key=lambda x: (x[1], x[0]))][:AIDEZ_MAX]}


def _en_memoire(jeton: str, contenu: dict) -> dict:
    """La frise gardée telle qu'elle sert : ensembles pour les contrôles ; les photos d'album déjà ouvertes restent permises."""
    avant = ETAT["invites"].get(jeton)
    vue = {**contenu, "_phares": set(contenu["_phares"]), "_photos_gens": set(contenu["_photos_gens"]),
           "_album": avant["_album"] if avant else set(), "_aidez_vus": set(contenu.get("_aidez", []))}
    # 0.17 : identifiant opaque → identifiant Immich, pour toutes les photos que la vue de l'invitation peut montrer
    # (phares, photos des étapes et de « Voir l'album », « Aidez-moi à dater »)
    permises = vue["_phares"] | vue["_photos_gens"] | vue["_aidez_vus"] \
        | {i for liste in contenu.get("_photos_etapes", {}).values() for i in liste}
    vue["_ids"] = {_opaque(jeton, a): a for a in permises}
    ETAT["invites"][jeton] = vue
    return vue


def _opaque(jeton: str, asset: str) -> str:
    """0.17 : l'identifiant d'une photo pour une invitation : stable, propre à Sillage, sans rien de l'identifiant Immich
    (HMAC de la clé gardée dans la base). Une autre invitation voit un autre identifiant pour la même photo."""
    return hmac.new(ETAT["cle_photos"], f"{jeton}|{asset}".encode(), hashlib.sha256).hexdigest()[:24]


def _asset(inv: dict, photo: str) -> str | None:
    """L'identifiant Immich derrière un identifiant opaque de cette invitation ; None s'il n'est pas de sa vue."""
    return inv["_ids"].get(photo) if OPAQUE.match(photo or "") else None


def _verrou(jeton: str) -> threading.Lock:
    with VERROU:
        return ETAT["verrous"].setdefault(jeton, threading.Lock())


def _preparer_un(jeton: str, refaire: bool = True) -> dict | None:
    """Calcule et garde la frise d'une invitation. Sans `refaire`, une frise déjà gardée (par un autre fil) suffit."""
    with _verrou(jeton):
        inv = ETAT["base"].invite(jeton)
        if not inv:
            ETAT["invites"].pop(jeton, None)
            return None
        if not refaire and (deja := ETAT["base"].frise(jeton)):
            return _en_memoire(jeton, deja[0])
        contenu = _calculer(inv)
        ETAT["base"].garder_frise(jeton, contenu)
        return _en_memoire(jeton, contenu)


def _chauffer(vue: dict) -> None:
    """Les photos phares d'une frise, lues d'avance dans Immich et gardées sur disque : l'invité les voit sans attendre."""
    for photo in sorted(vue["_phares"]):
        if not ETAT["cache"].lire(f"{photo}-preview"):
            try:
                _vignette(photo, "preview")
            except Exception as exc:                 # une image illisible n'arrête pas la préparation
                log.warning("Vignette %s non préparée : %s", photo, exc)


def _preparer(jetons: list[str]) -> None:
    for jeton in jetons:
        try:
            with maison.TACHES.tour(TACHE_PREPARATION):      # 0.18 : une frise = un tour suivi dans /health
                vue = _preparer_un(jeton)
                if vue:
                    _chauffer(vue)
        except Exception as exc:                     # Immich muet : la frise d'avant reste, la nuit suivante réessaie
            log.warning("Frise de l'invitation non préparée : %s", exc)


def _en_fond(travail, *args) -> None:
    fil = threading.Thread(target=travail, args=args, daemon=True)
    ETAT["fond"] = [f for f in ETAT["fond"] if f.is_alive()] + [fil]
    fil.start()


def _rafraichir_tout() -> None:
    """La mise à jour de la nuit : les noms d'albums et les personnes sont relus, chaque frise refaite."""
    ETAT["albums"].clear()
    ETAT["toutes"] = None
    _effacer_avis_traites()
    _preparer([i["jeton"] for i in ETAT["base"].invitations()])
    ETAT["nuit"] = datetime.now().isoformat(timespec="seconds")


TACHE_NUIT = "frises-de-nuit"              # 0.18 : nom de la boucle de nuit dans /health (taches)
TACHE_PREPARATION = "preparation-frises"   # 0.18 : préparation d'une frise d'invitation (à la demande)


def _prochaine(heure: int, maintenant: datetime) -> datetime:
    cible = maintenant.replace(hour=heure, minute=0, second=0, microsecond=0)
    return cible if cible > maintenant else cible + timedelta(days=1)


async def _chaque_nuit() -> None:
    while True:
        maintenant = datetime.now()
        await asyncio.sleep((_prochaine(ETAT["cfg"].heure_frises, maintenant) - maintenant).total_seconds())
        try:
            async with maison.TACHES.tour_async(TACHE_NUIT):   # 0.18 : un tour de la boucle de nuit
                await asyncio.to_thread(_rafraichir_tout)
        except Exception as exc:
            log.warning("Mise à jour de nuit des frises : %s", exc)


def _oublier(jetons: list[str]) -> None:
    """Une correction ou un changement d'hôtes : ces frises sont refaites tout de suite (en fond)."""
    if not jetons:
        return
    ETAT["base"].oublier_frises(jetons)
    for j in jetons:
        ETAT["invites"].pop(j, None)
    _en_fond(_preparer, jetons)


def _invitation(jeton: str) -> dict:
    """La frise de l'invitation : en mémoire, sinon dans la base ; calculée sur place seulement si elle n'est pas encore prête."""
    if not ETAT["base"].invite(jeton):
        ETAT["invites"].pop(jeton, None)
        raise HTTPException(404, "Cette invitation n'existe pas ou a expiré.")
    if jeton in ETAT["invites"]:
        return ETAT["invites"][jeton]
    garde_ = ETAT["base"].frise(jeton)
    if garde_:
        return _en_memoire(jeton, garde_[0])
    vue = _preparer_un(jeton, refaire=False)
    if not vue:
        raise HTTPException(404, "Cette invitation n'existe pas ou a expiré.")
    return vue


# ================================================================ réglages, sauvegarde et restauration (0.16)

def _tous_reglages() -> dict:
    """Les réglages d'usage : ceux du fichier reglages.json, et les hôtes de la maison (0.7, gardés dans la base)."""
    return {**ETAT["reglages"].tout(), "hotes": ETAT["base"].reglage("hotes", [])}


def _hotes_valides(valeur) -> list[dict]:
    """Les hôtes demandés (identifiants de personnes d'Immich), avec leur nom ; refuse un mauvais type ou un inconnu."""
    if not isinstance(valeur, list):
        raise HTTPException(400, "Hôtes : une liste d'identifiants de personnes est attendue.")
    voulus = [str(i.get("id") if isinstance(i, dict) else i) for i in valeur][:6]
    connues = _personnes()
    if any(i not in connues for i in voulus):
        raise HTTPException(422, "Personne inconnue d'Immich.")
    return [{"id": i, "nom": connues[i]["name"].strip()} for i in dict.fromkeys(voulus)]


def _changer(valeurs: dict) -> list[str]:
    """Change des réglages (écran ou restauration) et en tire les effets sans redémarrer. Rend les clés changées.
    Mauvais type → HTTPException 400, rien n'est changé."""
    avant = _tous_reglages()
    hotes = _hotes_valides(valeurs["hotes"]) if "hotes" in valeurs else None
    autres = {k: v for k, v in valeurs.items() if k in REGLAGES}
    if "cache_mo" in autres and (isinstance(autres["cache_mo"], bool) or not isinstance(autres["cache_mo"], (int, str))
                                 or not str(autres["cache_mo"]).strip().isdigit()):
        raise HTTPException(400, "Place des vignettes : un nombre entier de Mo, 0 ou plus, est attendu.")
    for k in ("tag_estimee", "tag_non_datee"):
        if k in autres and not isinstance(autres[k], str):
            raise HTTPException(400, "Tag : un texte est attendu.")
    try:
        ETAT["reglages"].changer(autres)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, f"Réglage refusé : {exc}.")
    if hotes is not None:
        ETAT["base"].poser_reglage("hotes", hotes)
    apres = _tous_reglages()
    changes = [k for k in apres if apres[k] != avant.get(k)]
    if "cache_mo" in changes:
        ETAT["cache"].regler(apres["cache_mo"])
    if {"tag_estimee", "tag_non_datee"} & set(changes):
        ETAT["reperes"] = None                       # les tags sont relus au prochain chemin
    if set(changes) - {"cache_mo"}:
        _oublier([i["jeton"] for i in ETAT["base"].invitations()])   # les frises des chambres sont refaites
    return changes


@app.get("/api/reglages")
def reglages():
    """Les réglages d'usage de Sillage (0.7 : les hôtes ; 0.16 : mots, dossiers muets, vignettes, tags de Millésime)."""
    return _tous_reglages()


@app.put("/api/reglages")
def regler(corps: dict = Body(...)):
    if not isinstance(corps, dict):
        raise HTTPException(400, "Un objet de réglages est attendu.")
    for k in _changer(corps):
        log.info("Réglage « %s » changé dans Réglages.", k)
    return reglages()


@app.get("/externe/sauvegarde")
def sauvegarde(request: Request):
    """0.16 : les réglages d'usage, collectés chaque nuit par l'Anneau. Jeton commun seulement ; aucun : porte fermée.
    Jamais de variable, de chemin ni de secret : rien que les réglages et la version."""
    _porte_commune(request)
    return maison.sauvegarde(APPLI, __version__, _tous_reglages(), exclus=EXCLUS)


def _porte_commune(request: Request) -> None:
    """Les adresses /externe/ : jeton commun seulement ; aucun jeton posé : porte fermée (404)."""
    acceptes = maison.jetons()
    if not acceptes:
        raise HTTPException(404, "Adresse fermée : MAISON_JETON n'est pas posé.")
    if not maison.jeton_valide(maison.jeton_propose(request.headers), acceptes):
        raise HTTPException(401, "Jeton refusé.")


def _chez_l_anneau(le: str = "") -> dict:
    """Une demande de sauvegarde à l'Anneau ; une panne devient un message clair (503), un manque un 404."""
    try:
        r = maison.lire_sauvegarde(APPLI, le, lire=ETAT.get("lire_sauvegarde"))
    except Exception as exc:                         # noqa: BLE001 — l'Anneau ne doit rien casser ici
        if getattr(exc, "code", None) == 404:
            raise HTTPException(404, "L'Anneau n'a pas de sauvegarde de Sillage" + (f" du {le}." if le else "."))
        raise HTTPException(503, f"L'Anneau ne répond pas ({exc.__class__.__name__}) : réessaie plus tard.")
    if not isinstance(r, dict):
        raise HTTPException(503, "L'Anneau a répondu quelque chose d'illisible.")
    return r


@app.get("/api/restaurer")
def restaurer_voir(le: str = ""):
    """Sans « le » : les dates des sauvegardes gardées par l'Anneau. Avec : ce qui changerait (actuel → sauvegardé)."""
    if not le:
        dates = [d for d in (_chez_l_anneau().get("dates") or []) if isinstance(d, str)]
        if not dates:
            raise HTTPException(404, "L'Anneau n'a encore aucune sauvegarde de Sillage.")
        return {"dates": dates}
    if not JOUR.match(le):
        raise HTTPException(400, "Date attendue sous la forme AAAA-MM-JJ.")
    s = _chez_l_anneau(le)
    return {"le": s.get("le", le), "version": s.get("version", ""),
            "differences": maison.differences(_tous_reglages(), s.get("reglages") or {}, EXCLUS)}


@app.post("/api/restaurer")
def restaurer(corps: dict = Body(...)):
    """Applique les réglages d'une sauvegarde qui diffèrent de l'actuel (réglages seulement : rien n'est écrit ailleurs)."""
    le = str((corps or {}).get("le", "")).strip()
    if not JOUR.match(le):
        raise HTTPException(400, "Date attendue sous la forme AAAA-MM-JJ.")
    s = _chez_l_anneau(le)
    diffs = maison.differences(_tous_reglages(), s.get("reglages") or {}, EXCLUS)
    changes = _changer({d["cle"]: d["sauve"] for d in diffs}) if diffs else []
    log.warning("Réglages restaurés depuis la sauvegarde du %s : %s.", le, ", ".join(changes) or "rien à changer")
    return reglages()


@app.get("/api/chambres")
def chambres():
    """0.6 : les pages préparées par Home Assistant, pour l'onglet « Chambres » du propriétaire (lecture seule)."""
    sortie, pretes = [], ETAT["base"].preparees()
    for i in ETAT["base"].invitations():
        fin = (datetime.fromisoformat(i["expire"]).date() - timedelta(days=1)).isoformat()
        sortie.append({"chambre": i["chambre"], "jeton": i["jeton"], "du": i["du"], "au": fin,
                       "noms": [p["nom"] for p in i["personnes"]],
                       "introuvables": [p["nom"] for p in i["personnes"] if not p.get("id")],
                       "prete_le": pretes.get(i["jeton"], "")})
    return {"chambres": sortie, "heure_nuit": ETAT["cfg"].heure_frises}


def _annee(inv: dict, asset: str) -> int | None:
    """0.17 : l'année que l'invité voit pour cette photo ; None : pas encore datée."""
    d = inv.get("_dates", {}).get(asset)
    return int(d[:4]) if d else None


def _vue_invite(jeton: str, inv: dict) -> dict:
    """Ce qui part vers l'invité : la frise sans les clés « _ », chaque photo nommée par son identifiant opaque."""
    def chemin_(c: dict) -> dict:
        return {**c, "chapitres": [{**ch, "etapes": [{**e, "phare": _opaque(jeton, e["phare"]), "annee": _annee(inv, e["phare"])}
                                                      for e in ch["etapes"]]} for ch in c["chapitres"]]}
    vue = {k: v for k, v in inv.items() if not k.startswith("_")}
    vue["commun"] = chemin_(vue["commun"]) if vue.get("commun") else vue.get("commun")
    vue["chacun"] = [chemin_(c) for c in vue.get("chacun") or []]
    vue["aidez"] = [{"id": _opaque(jeton, a)} for a in inv.get("_aidez", [])]
    return vue


def _etat_avis(jeton: str) -> dict:
    """0.17 : ce que l'invité voit de ses avis : « signalé » (en attente), « regardée » (écarté par Julien depuis moins
    de 30 jours : la date reste), rien sinon ; et le nombre de ses avis acceptés ou corrigés (le merci)."""
    limite = datetime.now().astimezone() - timedelta(days=REGARDEE_JOURS)
    etats: dict[str, dict] = {}
    redatees = 0
    for a in ETAT["base"].signalements_de(jeton):            # du plus ancien au plus récent : le dernier décide
        cle = _opaque(jeton, a["asset"])
        if a["traite_le"] is None:
            etats[cle] = {"etat": "signale", "annee": a["annee"], "environ": a["environ"], "mot": a["mot"]}
            continue
        redatees += a["issue"] in ("acceptee", "corrigee")
        if etats.get(cle, {}).get("etat") == "signale":
            continue
        if a["issue"] == "ecartee" and quand_tz(a["traite_le"]) > limite:
            etats[cle] = {"etat": "regardee"}
        else:
            etats.pop(cle, None)
    return {"signalements": etats, "photos_redatees": redatees}


@app.get("/api/invite/{jeton}")
def invitation(jeton: str):
    return {**_vue_invite(jeton, _invitation(jeton)), **_etat_avis(jeton)}


def _mot(brut) -> str:
    """Le mot libre d'un avis, en texte brut : une ligne, sans caractère de commande ; 120 caractères au plus."""
    if brut is None:
        return ""
    if not isinstance(brut, str):
        raise HTTPException(422, "Le souvenir doit être un texte.")
    texte = "".join(" " if unicodedata.category(c) in ("Cc", "Zl", "Zp") else c for c in brut)
    texte = " ".join(texte.split())
    if len(texte) > MOT_MAX:
        raise HTTPException(422, f"Le souvenir est trop long ({MOT_MAX} caractères au plus).")
    return texte


@app.post("/api/invite/{jeton}/signalement/{photo}")
def signaler(jeton: str, photo: str, corps: dict = Body(...)):
    """0.17 : l'invité propose une année pour une photo de sa vue (ou de « Aidez-moi à dater »). Renvoyer remplace son
    avis ; 100 avis en attente par invitation au plus. Rien n'est écrit dans Immich : Millésime lit l'avis."""
    inv = _invitation(jeton)                                  # expirée : 404
    asset = _asset(inv, photo)
    if not asset:
        raise HTTPException(404, "Photo inconnue de cette invitation.")
    annee = corps.get("annee") if isinstance(corps, dict) else None
    if isinstance(annee, str) and annee.strip().isdigit():
        annee = int(annee.strip())
    if isinstance(annee, bool) or not isinstance(annee, int) or not 1900 <= annee <= date.today().year:
        raise HTTPException(422, f"Une année entre 1900 et {date.today().year} est attendue.")
    personnes = (ETAT["base"].invite(jeton) or {}).get("personnes", [])
    ligne = ETAT["base"].signaler(jeton, asset, annee, bool(corps.get("environ")), _mot(corps.get("mot")),
                                  inv.get("_dates", {}).get(asset), [p["nom"].split()[0] for p in personnes if p["nom"].split()],
                                  [p["id"] for p in personnes if p.get("id")], LIMITE_AVIS)
    if ligne is None:
        raise HTTPException(429, TROP)
    return {"message": MERCI, "photo": photo, **_etat_avis(jeton)}


@app.delete("/api/invite/{jeton}/signalement/{photo}")
def changer_d_avis(jeton: str, photo: str):
    """0.17 : l'invité retire son avis tant qu'il n'est pas traité."""
    inv = _invitation(jeton)
    asset = _asset(inv, photo)
    if not asset:
        raise HTTPException(404, "Photo inconnue de cette invitation.")
    return {"retires": ETAT["base"].retirer_signalement(jeton, asset), "photo": photo, **_etat_avis(jeton)}


@app.get("/api/invite/{jeton}/album/{photo}")
def album_invite(jeton: str, photo: str):
    """0.12 : l'album d'une photo phare, pour l'invité — seulement les photos de l'album où l'un des invités est
    reconnu (l'album peut contenir d'autres gens, d'autres moments). 0.17 : photos nommées par leur identifiant opaque."""
    inv = _invitation(jeton)
    asset = _asset(inv, photo)
    if not asset or asset not in inv["_phares"]:
        raise HTTPException(404, "Photo inconnue de cette invitation.")
    photo = asset
    # 0.12.1 : Immich ne dit pas qui est sur les photos d'un album : on croise avec les photos où un invité est reconnu.
    # Pas d'album, ou rien de commun : les photos de l'étape elle-même (celles que le compteur « 2 photos » annonce).
    a = ETAT["immich"].album_complet(photo)
    etape = list(dict.fromkeys(inv["_photos_etapes"].get(photo, []))) or [photo]
    dans_album = [p["id"] for p in (a or {}).get("photos", []) if not p["video"] and p["id"] in inv["_photos_gens"]]
    ids = list(dict.fromkeys(dans_album + [i for i in etape if i not in dans_album])) if dans_album else etape
    inv["_album"].update(ids)
    return {"nom": a["nom"] if a and dans_album else "", "total": len(ids),
            "photos": [{"id": _opaque(jeton, i), "video": False, "annee": _annee(inv, i)} for i in ids]}


@app.get("/api/invite/{jeton}/vignette/{photo}")
def vignette_invite(jeton: str, photo: str, petite: bool = False):
    """Seules les photos phares du chemin de l'invitation sont servies (0.12 : et celles de leurs albums déjà ouverts ;
    0.17 : et celles de « Aidez-moi à dater »). 0.17 : adresse par identifiant opaque, plus par identifiant Immich."""
    inv = _invitation(jeton)
    asset = _asset(inv, photo)
    if not asset or (asset not in inv["_phares"] and asset not in inv["_album"] and asset not in inv["_aidez_vus"]):
        raise HTTPException(404, "Photo inconnue de cette invitation.")
    return _vignette(asset, "thumbnail" if petite else "preview")


# ================================================================ avis des invités, pour Millésime (0.17)

def _effacer_avis_traites() -> None:
    """Les avis traités depuis plus de 90 jours sont effacés (au démarrage et chaque nuit)."""
    n = ETAT["base"].effacer_traites(GARDE_TRAITES)
    if n:
        log.info("%s avis d'invités traités depuis plus de %s jours effacés.", n, GARDE_TRAITES)


@app.get("/externe/signalements")
def signalements(request: Request):
    """Contrat 1 avec Millésime : les avis des invités pas encore traités, avec l'identifiant Immich de la photo
    (il ne sort que par ici, derrière le jeton commun) et les prénoms de l'invitation."""
    _porte_commune(request)
    return {"contrat": 1, "signalements": [
        {"id": a["id"], "asset": a["asset"], "annee": a["annee"], "environ": a["environ"], "mot": a["mot"],
         "date_affichee": a["date_affichee"], "invites": a["invites"], "le": a["le"]}
        for a in ETAT["base"].signalements_en_attente()]}


@app.post("/externe/signalements/traite")
def signalement_traite(request: Request, corps: dict = Body(...)):
    """Contrat 1 : Millésime a traité une photo. Ferme tous ses avis en attente (toutes invitations) ; rejouable
    (la deuxième fois : 0 fermé). 0.19 : plus de récit à marquer « à revoir » (« Raconter » retiré)."""
    _porte_commune(request)
    asset = str((corps or {}).get("asset") or "") if isinstance(corps, dict) else ""
    issue = (corps or {}).get("issue") if isinstance(corps, dict) else None
    if not UUID.match(asset):
        raise HTTPException(422, "« asset » : un identifiant de photo d'Immich est attendu.")
    if issue not in ISSUES:
        raise HTTPException(422, "« issue » : acceptee, corrigee ou ecartee.")
    fermes, _personnes = ETAT["base"].traiter(asset, issue)
    return {"fermes": fermes}


# ================================================================ étapes d'une personne, pour la Gazette (0.20)

@app.get("/externe/personnes/{immich_id}/etapes")
def etapes_de(immich_id: str, request: Request):
    """Contrat 1 avec la Gazette (fiche complète d'une personne) : les étapes nommées du chemin de cette personne,
    mêmes règles que le chemin (photos visibles seulement, corrections de Julien comprises, étapes masquées et sans nom
    écartées), les plus fournies d'abord, 60 au plus. Personne inconnue de Sillage : liste vide (pas d'erreur)."""
    _porte_commune(request)
    fiche = _personnes().get(immich_id) if UUID.match(immich_id) else None
    if not fiche:
        return {"contrat": 1, "etapes": []}
    toutes = [e for ch in _calcul_du_chemin(immich_id, fiche)["chapitres"] for e in ch["etapes"]
              if e["nom"].strip() and not e["masquee"]]
    toutes.sort(key=lambda e: (-e["nombre"], e["debut"]))
    return {"contrat": 1, "etapes": [{"nom": e["nom"], "annee": int(e["debut"][:4]), "photos": e["nombre"]}
                                     for e in toutes[:ETAPES_MAX]]}


# ================================================================ images (derrière la session)

def _vignette(photo: str, taille: str) -> Response:
    """0.10 : la vignette d'une photo, gardée sur disque après la première lecture dans Immich."""
    cle = f"{photo}-{taille}"
    garde_ = ETAT["cache"].lire(cle)
    if garde_:
        return _image(*garde_)
    contenu, sorte = ETAT["immich"].image(f"/assets/{photo}/thumbnail", "la lecture d'une image", size=taille)
    ETAT["cache"].garder(cle, contenu, sorte)
    return _image(contenu, sorte)


def _image(contenu: bytes, sorte: str) -> Response:
    return Response(contenu, media_type=sorte, headers={"Cache-Control": "private, max-age=86400"})


@app.get("/api/portrait/{personne}")
def portrait(personne: str):
    if personne not in _personnes():
        raise HTTPException(404, "Personne inconnue de Sillage.")
    return _image(*ETAT["immich"].image(f"/people/{personne}/thumbnail", "la lecture d'un portrait"))


@app.get("/api/vignette/{photo}")
def vignette(photo: str, grande: bool = False):
    """Seules les photos d'un chemin déjà calculé sont servies : Sillage n'ouvre pas tout Immich."""
    if not UUID.match(photo) or photo not in ETAT["connues"]:
        raise HTTPException(404, "Photo inconnue de Sillage.")
    return _vignette(photo, "preview" if grande else "thumbnail")


@app.get("/api/album/{photo}")
def album(photo: str):
    """0.12 : toutes les photos de l'album qui contient cette photo du chemin ; elles deviennent lisibles par Sillage."""
    if not UUID.match(photo) or photo not in ETAT["connues"]:
        raise HTTPException(404, "Photo inconnue de Sillage.")
    a = ETAT["immich"].album_complet(photo)
    if not a:
        return {"nom": "", "photos": [], "total": 0}
    ETAT["connues"].update({p["id"]: ETAT["connues"].get(p["id"]) or p["checksum"] for p in a["photos"]})
    return {"nom": a["nom"], "total": a["total"], "photos": [{"id": p["id"], "video": p["video"]} for p in a["photos"]]}


@app.get("/api/video/{photo}")
def video(photo: str, request: Request):
    """0.10 : la lecture d'une vidéo du chemin, pour le propriétaire (pas pour les invités)."""
    if not UUID.match(photo) or photo not in ETAT["connues"]:
        raise HTTPException(404, "Vidéo inconnue de Sillage.")
    entetes = {"range": request.headers["range"]} if request.headers.get("range") else {}
    r = ETAT["immich"].flux(f"/assets/{photo}/video/playback", "la lecture d'une vidéo", entetes)
    garder = {k: r.headers[k] for k in ("content-type", "content-length", "content-range", "accept-ranges") if k in r.headers}
    return StreamingResponse(r.iter_bytes(65536), status_code=r.status_code, headers=garder, background=BackgroundTask(r.close))


# ================================================================ services

@app.get("/api/services")
def services():
    try:
        version, erreur = ETAT["immich"].version(), ""
        nombre = len(_personnes(frais=True))
        _reperes(frais=True)
    except ErreurImmich as exc:
        version, erreur, nombre = "", str(exc), 0
    return {"immich": {"repond": not erreur, "version": version, "erreur": erreur, "personnes": nombre,
                       "lecture_seule": True},
            "carnet": ETAT.get("carnet", {"regle": bool(ETAT["cfg"].jeton), "erreur": "", "fiches": 0}),
            "millesime": ETAT.get("reperes_etat", {"regle": bool(_reglage("tag_estimee") or _reglage("tag_non_datee")),
                                                   "lu": False, "erreur": "", "estimees": 0, "non_datees": 0,
                                                   "tag_non_datee": _reglage("tag_non_datee"), "source": "", "chambre_noire": ""}),
            "cache": ETAT["cache"].place()}


# ================================================================ interface

@app.get("/{chemin:path}")
def interface(chemin: str):
    statique = ETAT["cfg"].static
    fichier = (statique / chemin).resolve() if chemin else None
    if fichier and fichier.is_file() and statique.resolve() in fichier.parents:
        return FileResponse(fichier)
    index = statique / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return JSONResponse({"detail": "Interface non compilée."}, status_code=404)
