"""0.17 : dates signalées par les invités (« Pas la bonne année ? », « Aidez-moi à dater ») et contrat 1 avec Millésime
(/externe/signalements). Noms, photos et jetons inventés."""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app import main

from .faux_immich import CAMILLE, ident, photo
from .test_api import _attendre_le_fond, avec_jeton_ha, c, marque, monde, op, sejour  # noqa: F401 (fixtures)

JETON = "jeton-commun-essai"
H = {"Authorization": f"Bearer {JETON}"}


@pytest.fixture
def porte(monkeypatch):
    for v in ("MAISON_JETON", "MAISON_JETON_ANCIEN"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("MAISON_JETON", JETON)


def inviter(client, chambre="ami", noms=("Camille ROUSSEL",)):
    jeton = sejour(client, avec_jeton_ha(), chambre=chambre, noms=list(noms))["chemin"].split("/")[-1]
    _attendre_le_fond()
    return jeton


def signaler(client, jeton, photo_, **corps):
    corps.setdefault("annee", 1986)
    return client.post(f"/api/invite/{jeton}/signalement/{photo_}", json=corps)


def ids_immich(faux):
    return {p["id"] for liste in faux.photos.values() for p in liste}


def sans_id_immich(faux, *reponses):
    """Aucun identifiant Immich dans ce que l'invité reçoit."""
    for r in reponses:
        assert not any(i in r.text for i in ids_immich(faux)), r.text


def test_signaler_une_photo_de_sa_vue(monde):
    client, faux = monde
    jeton = inviter(client)
    phare = op(jeton, "bapteme2")
    r = signaler(client, jeton, phare, annee=1986, environ=True, mot="  baptême\nde Léa  ")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["message"] == "Merci, c'est transmis à Julien" and j["photos_redatees"] == 0
    assert j["signalements"] == {phare: {"etat": "signale", "annee": 1986, "environ": True, "mot": "baptême de Léa"}}
    vue = client.get(f"/api/invite/{jeton}")
    assert vue.json()["signalements"][phare]["etat"] == "signale"
    # Une photo de l'album s'ouvre et se signale aussi
    album = client.get(f"/api/invite/{jeton}/album/{phare}")
    autre = next(p["id"] for p in album.json()["photos"] if p["id"] != phare)
    assert signaler(client, jeton, autre, annee=1988).status_code == 200
    sans_id_immich(faux, r, vue, album, client.delete(f"/api/invite/{jeton}/signalement/{autre}"))
    # La photo doit être de la vue de cette invitation
    autre_jeton = inviter(client, chambre="ado")
    assert signaler(client, jeton, ident("bapteme2")).status_code == 404               # jamais par l'identifiant Immich
    assert signaler(client, jeton, op(autre_jeton, "bapteme2")).status_code == 404     # celui d'une autre invitation
    assert signaler(client, jeton, op(jeton, "corbeille")).status_code == 404          # pas dans la vue
    assert signaler(client, "jeton-inconnu", phare).status_code == 404
    # Année entre 1900 et l'année en cours, souvenir de 120 caractères au plus
    for mauvaise in (1899, date.today().year + 1, "vers 1980", True, None, 1986.5):
        assert signaler(client, jeton, phare, annee=mauvaise).status_code == 422, mauvaise
    assert signaler(client, jeton, phare, annee="1990").status_code == 200
    assert signaler(client, jeton, phare, mot="x" * 121).status_code == 422
    assert signaler(client, jeton, phare, mot=12).status_code == 422
    assert signaler(client, jeton, phare, mot="x" * 120).status_code == 200
    # Rien n'est écrit dans Immich
    assert {(m, ch) for m, ch in faux.demandes if m != "GET"} <= {("POST", "/search/metadata")}


def test_renvoyer_remplace_et_changer_d_avis(monde, porte):
    client, _ = monde
    jeton = inviter(client)
    phare = op(jeton, "bapteme2")
    signaler(client, jeton, phare, annee=1986)
    premier = client.get("/externe/signalements", headers=H).json()["signalements"]
    signaler(client, jeton, phare, annee=1985, environ=True)
    (avis,) = client.get("/externe/signalements", headers=H).json()["signalements"]   # un seul avis actif par photo
    assert (avis["annee"], avis["environ"]) == (1985, True) and avis["id"] != premier[0]["id"]
    r = client.delete(f"/api/invite/{jeton}/signalement/{phare}")
    assert r.status_code == 200 and r.json()["retires"] == 1 and r.json()["signalements"] == {}
    assert client.get("/externe/signalements", headers=H).json()["signalements"] == []
    assert client.delete(f"/api/invite/{jeton}/signalement/{phare}").json()["retires"] == 0
    assert client.delete(f"/api/invite/{jeton}/signalement/{ident('bapteme2')}").status_code == 404
    # Traité : changer d'avis ne retire plus rien (l'avis traité reste pour le merci)
    signaler(client, jeton, phare, annee=1985)
    client.post("/externe/signalements/traite", headers=H, json={"asset": ident("bapteme2"), "issue": "acceptee"})
    assert client.delete(f"/api/invite/{jeton}/signalement/{phare}").json()["retires"] == 0


def test_limite_de_100_avis_en_attente(monde):
    client, _ = monde
    jeton = inviter(client)
    base = main.ETAT["base"]
    for i in range(99):
        assert base.signaler(jeton, f"photo-inventee-{i}", 1990, False, "", None, ["Camille"], [CAMILLE], 100)
    assert signaler(client, jeton, op(jeton, "bapteme2")).status_code == 200            # le 100e passe
    r = signaler(client, jeton, op(jeton, "plage"))
    assert r.status_code == 429 and r.json()["detail"] == "Julien a déjà beaucoup de photos à regarder : revenez un peu plus tard."
    assert signaler(client, jeton, op(jeton, "bapteme2"), annee=1987).status_code == 200   # remplacer reste permis
    client.delete(f"/api/invite/{jeton}/signalement/{op(jeton, 'bapteme2')}")
    assert signaler(client, jeton, op(jeton, "plage")).status_code == 200               # une place s'est libérée


def test_invitation_expiree_refusee_ses_avis_restent(monde, porte):
    client, _ = monde
    jeton = inviter(client)
    signaler(client, jeton, op(jeton, "bapteme2"))
    main.ETAT["base"]._c.execute("UPDATE invites SET expire = '2000-01-01T00:00:00'")
    main.ETAT["base"]._c.commit()
    assert signaler(client, jeton, op(jeton, "plage")).status_code == 404
    assert client.delete(f"/api/invite/{jeton}/signalement/{op(jeton, 'bapteme2')}").status_code == 404
    (avis,) = client.get("/externe/signalements", headers=H).json()["signalements"]    # reste jusqu'à son traitement
    assert avis["invites"] == ["Camille"]


def test_externe_jeton_et_contrat(monde, monkeypatch):
    client, _ = monde
    for v in ("MAISON_JETON", "MAISON_JETON_ANCIEN"):
        monkeypatch.delenv(v, raising=False)
    corps = {"asset": ident("bapteme2"), "issue": "acceptee"}
    assert client.get("/externe/signalements").status_code == 404                       # jeton commun vide : porte fermée
    assert client.post("/externe/signalements/traite", json=corps).status_code == 404
    monkeypatch.setenv("MAISON_JETON", JETON)
    for h in ({}, {"Authorization": "Bearer faux"}, {"Authorization": "Bearer jeton-ha"}):
        assert client.get("/externe/signalements", headers=h).status_code == 401
        assert client.post("/externe/signalements/traite", headers=h, json=corps).status_code == 401
    assert client.get("/externe/signalements", headers=H).json() == {"contrat": 1, "signalements": []}
    jeton = inviter(client)
    signaler(client, jeton, op(jeton, "bapteme2"), annee=1986, environ=True, mot="baptême de Léa")
    r = client.get("/externe/signalements", headers={"X-Maison-Jeton": JETON}).json()
    (avis,) = r["signalements"]
    assert r["contrat"] == 1
    assert set(avis) == {"id", "asset", "annee", "environ", "mot", "date_affichee", "invites", "le"}
    assert isinstance(avis["id"], str) and avis["asset"] == ident("bapteme2")
    assert (avis["annee"], avis["environ"], avis["mot"]) == (1986, True, "baptême de Léa")
    assert avis["date_affichee"] == "1987-06-07" and avis["invites"] == ["Camille"]
    assert datetime.fromisoformat(avis["le"]).tzinfo is not None                        # « 2026-11-18T10:00:00+01:00 »
    # Demandes mal formées
    for mauvais in ({"asset": ident("bapteme2"), "issue": "acceptée"}, {"asset": "pas-un-id", "issue": "ecartee"},
                    {"issue": "ecartee"}, {"asset": ident("bapteme2")}):
        assert client.post("/externe/signalements/traite", headers=H, json=mauvais).status_code == 422


def test_traite_ferme_tous_les_avis_de_la_photo_et_se_rejoue(monde, porte):
    client, _ = monde
    seul = inviter(client)
    duo = inviter(client, chambre="ado", noms=("Camille ROUSSEL", "Hugo MARCHAND"))
    assert signaler(client, seul, op(seul, "mariage2"), annee=2018).status_code == 200
    assert signaler(client, duo, op(duo, "mariage2"), annee=2019).status_code == 200
    assert signaler(client, seul, op(seul, "plage"), annee=1996).status_code == 200
    avis = client.get("/externe/signalements", headers=H).json()["signalements"]
    assert sorted(a["invites"] for a in avis if a["asset"] == ident("mariage2")) == [["Camille"], ["Camille", "Hugo"]]
    r = client.post("/externe/signalements/traite", headers=H, json={"asset": ident("mariage2"), "issue": "acceptee"})
    assert r.status_code == 200 and r.json() == {"fermes": 2}
    r = client.post("/externe/signalements/traite", headers=H, json={"asset": ident("mariage2"), "issue": "acceptee"})
    assert r.status_code == 200 and r.json() == {"fermes": 0}                          # rejouable sans effet
    assert [a["asset"] for a in client.get("/externe/signalements", headers=H).json()["signalements"]] == [ident("plage")]
    # Chez l'invité : la marque s'efface, le merci compte la photo redatée
    for jeton in (seul, duo):
        v = client.get(f"/api/invite/{jeton}").json()
        assert op(jeton, "mariage2") not in v["signalements"] and v["photos_redatees"] == 1
    assert client.get(f"/api/invite/{seul}").json()["signalements"][op(seul, "plage")]["etat"] == "signale"
    # Un nouvel avis après traitement repart en attente
    assert signaler(client, seul, op(seul, "mariage2"), annee=2017).status_code == 200
    assert client.post("/externe/signalements/traite", headers=H, json={"asset": ident("mariage2"), "issue": "corrigee"}).json() == {"fermes": 1}
    assert client.get(f"/api/invite/{seul}").json()["photos_redatees"] == 2


def test_ecarte_dit_la_date_reste_pendant_30_jours(monde, porte):
    client, _ = monde
    jeton = inviter(client)
    phare = op(jeton, "bapteme2")
    signaler(client, jeton, phare)
    client.post("/externe/signalements/traite", headers=H, json={"asset": ident("bapteme2"), "issue": "ecartee"})
    v = client.get(f"/api/invite/{jeton}").json()
    assert v["signalements"] == {phare: {"etat": "regardee"}} and v["photos_redatees"] == 0
    il_y_a = (datetime.now().astimezone() - timedelta(days=31)).isoformat(timespec="seconds")
    main.ETAT["base"]._c.execute("UPDATE signalement SET traite_le = ?", (il_y_a,))
    main.ETAT["base"]._c.commit()
    assert client.get(f"/api/invite/{jeton}").json()["signalements"] == {}


def test_un_recit_garde_passe_a_revoir(monde, c, porte):
    client, _ = monde
    assert c.put(f"/api/recit/{CAMILLE}", json={"texte": "Mon texte relu."}).json()["a_revoir"] is None
    jeton = inviter(client)
    signaler(client, jeton, op(jeton, "plage"))
    client.post("/externe/signalements/traite", headers=H, json={"asset": ident("plage"), "issue": "ecartee"})
    _attendre_le_fond()
    assert c.get(f"/api/recit/{CAMILLE}").json()["a_revoir"] is None                   # écarté : rien ne change
    signaler(client, jeton, op(jeton, "bapteme2"))
    client.post("/externe/signalements/traite", headers=H, json={"asset": ident("bapteme2"), "issue": "corrigee"})
    _attendre_le_fond()
    r = c.get(f"/api/recit/{CAMILLE}").json()
    assert r["a_revoir"] and r["texte"] == "Mon texte relu."
    assert c.put(f"/api/recit/{CAMILLE}", json={"texte": "Mon texte relu, revu."}).json()["a_revoir"] is None   # gardé : marque effacée


def test_aidez_moi_a_dater(monde, c, porte):
    client, faux = monde
    lots = [f"lot{i:02d}" for i in range(14)]
    faux.photos[CAMILLE] += [photo(n, "2026-01-10T10:00:00", "Scans/Lot C") for n in lots]
    faux.photos[CAMILLE].append(photo("vers78", "1978-07-01T12:00:00", "Scans/Lot C"))
    faux.tags = {"t1": ("Lots/Non datée", [ident(n) for n in lots] + [ident("vers78")]),
                 "t2": ("Date estimée/1978 ±3", [ident("vers78")])}             # estimé : sort de la liste
    main.ETAT["reglages"].changer({"tag_non_datee": "Lots/Non datée"})
    main.ETAT["reperes"] = None
    c.get(f"/api/chemin/{CAMILLE}")
    marque(c, sorte="retiree", poser=ident("lot00"))                           # écartée par Julien : pas proposée
    jeton = inviter(client)
    v = client.get(f"/api/invite/{jeton}")
    aidez = [p["id"] for p in v.json()["aidez"]]
    assert len(aidez) == 12 and set(aidez) <= {op(jeton, n) for n in lots[1:]}
    assert op(jeton, "vers78") not in aidez
    sans_id_immich(faux, v)
    assert client.get(f"/api/invite/{jeton}/vignette/{aidez[0]}?petite=true").status_code == 200
    assert signaler(client, jeton, aidez[0], annee=1965, environ=True).status_code == 200
    (avis,) = client.get("/externe/signalements", headers=H).json()["signalements"]
    assert avis["date_affichee"] is None and avis["asset"] in {ident(n) for n in lots}
    # À plusieurs invités : la liste est faite des photos de l'un ou de l'autre
    duo = inviter(client, chambre="ado", noms=("Camille ROUSSEL", "Hugo MARCHAND"))
    assert len(client.get(f"/api/invite/{duo}").json()["aidez"]) == 12


def test_avis_traites_effaces_apres_90_jours(monde):
    client, _ = monde
    jeton = inviter(client)
    base = main.ETAT["base"]
    for asset in ("a-vieux", "a-recent", "a-attente"):
        base.signaler(jeton, asset, 1990, False, "", None, ["Camille"], [CAMILLE], 100)
    base.traiter("a-vieux", "acceptee")
    base.traiter("a-recent", "ecartee")
    il_y_a = (datetime.now().astimezone() - timedelta(days=91)).isoformat(timespec="seconds")
    base._c.execute("UPDATE signalement SET traite_le = ? WHERE asset = 'a-vieux'", (il_y_a,))
    base._c.commit()
    main._effacer_avis_traites()
    assert sorted(a["asset"] for a in base.signalements_de(jeton)) == ["a-attente", "a-recent"]
    # La mise à jour de la nuit efface aussi
    base._c.execute("UPDATE signalement SET traite_le = ? WHERE asset = 'a-recent'", (il_y_a,))
    base._c.commit()
    main._rafraichir_tout()
    assert [a["asset"] for a in base.signalements_de(jeton)] == ["a-attente"]
