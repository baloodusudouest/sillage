"""0.26 : « Quoi de neuf » dans les sillages : pour Julien (30 jours), pour les invités (depuis leur séjour précédent)
et pour La Récidive de la Gazette (GET /externe/nouveautes). Personnes, photos et jetons inventés."""
from __future__ import annotations

import time
from datetime import date, timedelta

import pytest

from app import main

from .faux_immich import CAMILLE, photo
from .test_api import avec_jeton_ha, monde, sejour  # noqa: F401 (fixtures)
from .test_sillages_prets import _carnet, _finir

JETON = "jeton-commun-essai"
H = {"Authorization": f"Bearer {JETON}"}
VIEUX = "2020-01-01T10:00:00.000Z"


def _jour(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def _ajoutee(n: int) -> str:
    return _jour(n) + "T12:00:00.000Z"


@pytest.fixture
def porte(monkeypatch):
    for v in ("MAISON_JETON", "MAISON_JETON_ANCIEN"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("MAISON_JETON", JETON)


def _anciennes(faux):
    for p in faux.photos[CAMILLE]:
        p["createdAt"] = VIEUX


def _arrivees(faux, il_y_a: int = 2):
    """Deux arrivées dans Immich : une photo de plus au mariage de 2019 (retrouvée), et une fête de la veille (nouvelle étape)."""
    faux.photos[CAMILLE] += [
        photo("mariage3", "2019-06-15T18:00:00", visage=0.2, createdAt=_ajoutee(il_y_a)),
        photo("fete1", f"{_jour(il_y_a + 1)}T19:00:00", f"{_jour(il_y_a + 1)[:4]}/Fête", createdAt=_ajoutee(il_y_a)),
        photo("fete2", f"{_jour(il_y_a + 1)}T20:00:00", f"{_jour(il_y_a + 1)[:4]}/Fête", createdAt=_ajoutee(il_y_a)),
    ]


def _entrer(client):
    assert client.post("/api/connexion", json={"mot_de_passe": main.ETAT["cfg"].password}).status_code == 200


def test_quoi_de_neuf_de_julien(monde, monkeypatch):
    client, faux_ = monde
    _entrer(client)
    monkeypatch.setattr(main, "PAUSE_SILLAGES", 0)
    _anciennes(faux_)
    _carnet()
    client.post("/api/sillages/preparer")
    _finir()
    assert client.get("/api/nouveautes").json()["personnes"] == []                 # rien de neuf
    _arrivees(faux_)
    r = client.get(f"/api/chemin/{CAMILLE}/verifier").json()
    assert r["mis_a_jour"] and len(r["nouvelles"]) == 3                             # marquées dans le chemin
    j = client.get("/api/nouveautes").json()
    assert j["jours"] == 30 and len(j["personnes"]) == 1
    p = j["personnes"][0]
    assert p["personne"] == CAMILLE and p["nom"] == "Camille R." and p["ajoutee_le"] == _jour(0)   # 0.26.5 : entrée dans le sillage
    par_debut = {e["debut"][:4]: e for e in p["etapes"]}
    noel = par_debut[_jour(3)[:4]]
    assert noel["nouvelle"] is True and noel["photos"] == 2 and noel["retrouvee"] is False
    mariage = par_debut["2019"]
    assert mariage["nouvelle"] is False and mariage["photos"] == 1 and mariage["retrouvee"] is True
    assert "nouvelles" not in mariage                                               # pas la liste des photos ici
    # le sillage préparé, rouvert, garde ses photos marquées
    assert len(client.get(f"/api/chemin/{CAMILLE}").json()["nouvelles"]) == 3


def test_plus_de_30_jours_ce_n_est_plus_neuf(monde, monkeypatch):
    c, faux_ = monde
    _entrer(c)
    monkeypatch.setattr(main, "PAUSE_SILLAGES", 0)
    _anciennes(faux_)
    _arrivees(faux_, il_y_a=40)
    _carnet()
    c.post("/api/sillages/preparer")
    _finir()
    assert c.get("/api/nouveautes").json()["personnes"] == []
    assert c.get(f"/api/chemin/{CAMILLE}").json()["nouvelles"] == []


def test_plafond_et_resume(monkeypatch):
    etapes = [{"cle": str(i), "nom": f"É{i}", "debut": f"20{10 + i}-01-01", "photos": [{"id": f"{i}-{k}"} for k in range(i + 1)]}
              for i in range(9)]
    ajouts = {p["id"]: "2026-11-20" for e in etapes for p in e["photos"]}
    n = main._nouveautes(etapes, ajouts, "2026-11-01")
    assert len(n["etapes"]) == main.NOUVEAUTES_MAX and n["etapes"][0]["photos"] == 9   # les plus fournies d'abord
    assert n["autres_etapes"] == 3 and n["autres_photos"] == 1 + 2 + 3


def test_la_gazette_lit_les_nouveautes(monde, porte):
    client, faux = monde
    _anciennes(faux)
    _arrivees(faux, il_y_a=5)
    assert client.get(f"/externe/nouveautes?personne={CAMILLE}&depuis={_jour(10)}").status_code == 401
    r = client.get(f"/externe/nouveautes?personne={CAMILLE}&depuis={_jour(10)}", headers=H)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["contrat"] == 1 and {e["annee"] for e in j["etapes"]} == {2019, int(_jour(6)[:4])}
    assert {e["photos"] for e in j["etapes"]} == {1, 2}
    # depuis après les arrivées : plus rien
    assert client.get(f"/externe/nouveautes?personne={CAMILLE}&depuis={_jour(1)}", headers=H).json()["etapes"] == []
    assert client.get(f"/externe/nouveautes?personne={CAMILLE}&depuis=hier", headers=H).status_code == 422
    assert client.get(f"/externe/nouveautes?personne=inconnu&depuis={_jour(1)}", headers=H).json()["etapes"] == []


def test_invite_du_nouveau_depuis_son_dernier_sejour(monde):
    client, faux = monde
    _anciennes(faux)
    h = avec_jeton_ha()
    # premier séjour : rien de neuf (pas de séjour précédent)
    jeton = sejour(client, h, noms=["Camille ROUSSEL"])["chemin"].rsplit("/", 1)[1]
    _attendre()
    assert client.get(f"/api/invite/{jeton}").json()["nouveautes"] is None
    # ce séjour-là est fini depuis dix jours ; des photos arrivent ; nouveau séjour
    with main.ETAT["base"]._verrou, main.ETAT["base"]._c:
        main.ETAT["base"]._c.execute("UPDATE sejours SET du = ?, fin = ?", (_jour(14), _jour(10)))
    _arrivees(faux, il_y_a=3)
    jeton2 = sejour(client, h, noms=["Camille ROUSSEL"], chambre="autre",
                    jusqu_au=(date.today() + timedelta(days=3)).isoformat())["chemin"].rsplit("/", 1)[1]
    _attendre()
    n = client.get(f"/api/invite/{jeton2}").json()["nouveautes"]
    assert n["depuis"] == _jour(10)
    assert {e["photos"] for e in n["etapes"]} == {1, 2}
    assert all(len(e["phare"]) == 24 for e in n["etapes"])                           # identifiants opaques seulement
    assert not any(CAMILLE in str(e) for e in n["etapes"])


def _attendre():
    for fil in list(main.ETAT["fond"]):
        fil.join(timeout=10)


def test_j_ai_vu(monde, monkeypatch):
    """0.26.4 : « J'ai vu » cache ce qui est déjà arrivé (partout) ; une arrivée suivante revient."""
    client, faux_ = monde
    _entrer(client)
    monkeypatch.setattr(main, "PAUSE_SILLAGES", 0)
    _anciennes(faux_)
    _arrivees(faux_)
    _carnet()
    client.post("/api/sillages/preparer")
    _finir()
    assert len(client.get("/api/nouveautes").json()["personnes"]) == 1
    r = client.post("/api/nouveautes/vu").json()
    assert r["ok"] and r["vu_le"]
    j = client.get("/api/nouveautes").json()
    assert j["personnes"] == [] and j["vu_le"] == r["vu_le"]
    assert client.get(f"/api/chemin/{CAMILLE}").json()["nouvelles"] == []             # plus marquées non plus
    faux_.photos[CAMILLE].append(photo("demain", f"{_jour(1)}T10:00:00", "2026/Après", createdAt=_ajoutee(-1)))
    time.sleep(1.1)
    client.get(f"/api/chemin/{CAMILLE}/verifier")
    p = client.get("/api/nouveautes").json()["personnes"]
    assert len(p) == 1 and sum(e["photos"] for e in p[0]["etapes"]) == 1


def test_photo_entree_tard_dans_le_sillage(monde, monkeypatch):
    """0.26.5 : une photo envoyée avant « J'ai vu » mais reconnue plus tard dans Immich (visage attribué ensuite)
    entre dans le sillage après : elle est nouvelle (heure où Sillage la voit), pas cachée par « J'ai vu »."""
    client, faux_ = monde
    _entrer(client)
    monkeypatch.setattr(main, "PAUSE_SILLAGES", 0)
    _anciennes(faux_)
    _carnet()
    client.post("/api/sillages/preparer")
    _finir()
    client.post("/api/nouveautes/vu")
    # envoyée il y a deux jours, reconnue maintenant : elle apparaît dans les photos de Camille
    faux_.photos[CAMILLE].append(photo("reconnue", "2018-08-08T10:00:00", "2018/Été", createdAt=_ajoutee(2)))
    time.sleep(1.1)                                                                   # l'heure à la seconde
    client.get(f"/api/chemin/{CAMILLE}/verifier")
    p = client.get("/api/nouveautes").json()["personnes"]
    assert len(p) == 1 and p[0]["etapes"][0]["photos"] == 1 and p[0]["etapes"][0]["retrouvee"] is True
    assert len(client.get(f"/api/chemin/{CAMILLE}").json()["nouvelles"]) == 1
