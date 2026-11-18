"""0.20 : les étapes du chemin d'une personne pour la fiche complète de la Gazette
(GET /externe/personnes/{immich_id}/etapes, jeton commun, contrat 1). Noms, photos et jetons inventés."""
from __future__ import annotations

import pytest

from .faux_immich import ANONYME, CACHEE, CAMILLE, HUGO, ident, photo
from .test_api import c, marque, monde  # noqa: F401 (fixtures)

JETON = "jeton-commun-essai"
H = {"Authorization": f"Bearer {JETON}"}


@pytest.fixture
def porte(monkeypatch):
    for v in ("MAISON_JETON", "MAISON_JETON_ANCIEN"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("MAISON_JETON", JETON)


def etapes_de(client, qui):
    r = client.get(f"/externe/personnes/{qui}/etapes", headers=H)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["contrat"] == 1
    return j["etapes"]


def test_0_20_porte_du_jeton_commun(monde, monkeypatch):
    client, faux = monde                                    # pas de session : /externe/ ne passe pas par elle
    for v in ("MAISON_JETON", "MAISON_JETON_ANCIEN"):
        monkeypatch.delenv(v, raising=False)
    adresse = f"/externe/personnes/{CAMILLE}/etapes"
    assert client.get(adresse, headers=H).status_code == 404            # jeton commun vide : porte fermée
    monkeypatch.setenv("MAISON_JETON", JETON)
    assert client.get(adresse).status_code == 401
    assert client.get(adresse, headers={"Authorization": "Bearer jeton-ha"}).status_code == 401
    assert faux.demandes == []                                           # rien n'est lu dans Immich sans le bon jeton
    assert client.get(adresse, headers=H).status_code == 200


def test_0_20_etapes_nommees_les_plus_fournies_d_abord(monde, porte):
    client, faux = monde
    # Baptême : 3 photos (vidéo comprise) ; mariage : 2 (corbeille, archive et verrou écartés) ;
    # la plage n'a pas de nom (dossier qui ne dit rien) : rien à proposer, elle n'est pas rendue ;
    # la photo d'avant la naissance n'est pas dans le chemin.
    assert etapes_de(client, CAMILLE) == [
        {"nom": "Baptême de Camille", "annee": 1987, "photos": 3},
        {"nom": "Mariage de Camille et Hugo", "annee": 2019, "photos": 2},
    ]
    # Lecture seule d'Immich
    assert {(m, ch) for m, ch in faux.demandes if m != "GET"} <= {("POST", "/search/metadata")}


def test_0_20_corrections_de_julien_suivies(monde, c, porte):
    client, _ = monde
    c.get(f"/api/chemin/{CAMILLE}")
    marque(c, sorte="titre", poser=ident("plage"), valeur="Été à la mer")          # nommée à la main : rendue
    marque(c, sorte="masquee", poser=ident("mariage2"))                             # masquée : jamais rendue
    marque(c, sorte="retiree", poser=ident("bapteme3"))                             # retirée : plus comptée
    assert etapes_de(client, CAMILLE) == [
        {"nom": "Baptême de Camille", "annee": 1987, "photos": 2},
        {"nom": "Été à la mer", "annee": 1995, "photos": 1},
    ]


def test_0_20_personne_inconnue_liste_vide(monde, porte):
    client, faux = monde
    for qui in (ident("personne-inconnue"), ANONYME, CACHEE, "pas-un-identifiant", CAMILLE.upper()):
        r = client.get(f"/externe/personnes/{qui}/etapes", headers=H)
        assert r.status_code == 200 and r.json() == {"contrat": 1, "etapes": []}, (qui, r.text)
    assert not any(ch == "/search/metadata" for _, ch in faux.demandes)             # aucun chemin calculé


def test_0_20_soixante_au_plus(monde, porte):
    client, faux = monde
    # 70 étapes nommées, une par année ; une sur dix a trois photos : elles passent devant, puis l'ordre des dates
    faux.photos[HUGO] = []
    for i in range(70):
        annee = 1950 + i
        n = 3 if i % 10 == 0 else 1
        faux.photos[HUGO] += [photo(f"h{i}-{k}", f"{annee}-07-1{k}T10:00:00", f"{annee}/{annee}-07-10 Fête {i:02d}")
                              for k in range(n)]
    r = etapes_de(client, HUGO)
    assert len(r) == 60
    assert [e["photos"] for e in r[:7]] == [3] * 7 and all(e["photos"] == 1 for e in r[7:])
    assert [e["annee"] for e in r[:7]] == [1950, 1960, 1970, 1980, 1990, 2000, 2010]
    assert [e["annee"] for e in r[7:10]] == [1951, 1952, 1953]
    assert r[0]["nom"] == "Fête 00" and all(isinstance(e["annee"], int) for e in r)
