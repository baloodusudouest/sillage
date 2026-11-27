"""Tests d'écran de Sillage, sur PC et sur iPhone, contre un faux Immich."""
from __future__ import annotations

import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from tests.faux_immich import CAMILLE

playwright = pytest.importorskip("playwright.sync_api")
RACINE = Path(__file__).resolve().parents[2]
MDP = "essai-essai-essai"
ECRANS = {"pc": {"width": 1280, "height": 860}, "iphone": {"width": 390, "height": 760}}


DOSSIER = {}


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    DOSSIER["ui"] = tmp_path_factory.mktemp("ui")
    proc = subprocess.Popen([sys.executable, "-m", "tests.interface.serveur", str(DOSSIER["ui"]), str(port)], cwd=RACINE)
    adresse = f"http://127.0.0.1:{port}"
    for _ in range(200):
        try:
            if urllib.request.urlopen(adresse + "/health", timeout=1).status == 200:
                break
        except OSError:
            time.sleep(0.1)
    else:
        proc.terminate()
        pytest.fail("Le Sillage de démonstration n'a pas démarré.")
    yield adresse
    proc.terminate()


@pytest.fixture(scope="module", params=list(ECRANS))
def page(base, request):
    with playwright.sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport=ECRANS[request.param])
        pg.set_default_timeout(10000)
        erreurs = []
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        pg.goto(base + "/")
        pg.fill("#mot-de-passe", MDP)
        pg.click("button[type=submit]")
        pg.wait_for_selector("ul[aria-label=Personnes]")
        pg.base, pg.ecran = base, request.param
        yield pg
        assert erreurs == []
        b.close()


def sans_debordement(pg):
    assert pg.evaluate("document.documentElement.scrollWidth - innerWidth") <= 0


def test_la_liste_et_la_recherche(page):
    page.goto(page.base + "/#/sillages")
    assert page.locator("ul[aria-label=Personnes] li").count() == 2
    page.fill("input[type=search]", "camil")
    assert page.locator("ul[aria-label=Personnes] li").count() == 1
    page.fill("input[type=search]", "zzz")
    assert page.get_by_text("Personne ne porte ce nom.").is_visible()
    sans_debordement(page)


def test_010_tuile_a_verifier(page):
    """0.10 : les personnes sans date de naissance dans Immich, d'un toucher."""
    page.goto(page.base + "/#/sillages")
    page.fill("input[type=search]", "")
    tuile = page.locator(".averifier")
    assert "1 personne sans date de naissance" in tuile.inner_text()
    tuile.click()
    assert page.locator("ul[aria-label=Personnes] li").all_inner_texts()[0].startswith("Hugo")
    assert page.locator("ul[aria-label=Personnes] li").count() == 1
    tuile.click()
    assert page.locator("ul[aria-label=Personnes] li").count() == 2


def test_010_une_video_se_lit(page):
    page.goto(page.base + "/#/chemin/" + CAMILLE)
    page.get_by_role("button", name="Noël chez les grands-parents, 6 photos").click()
    page.get_by_role("button", name="Photo 1 (vidéo)").click()
    v = page.locator(".plein video")
    v.wait_for()
    assert v.get_attribute("src").startswith("/api/video/") and v.get_attribute("controls") is not None
    page.keyboard.press("Escape")
    page.keyboard.press("Escape")


def test_le_chemin_temps_forts_puis_tout(page):
    page.goto(page.base + "/#/chemin/" + CAMILLE)
    page.wait_for_selector(".etape")
    assert page.locator("h1").inner_text() == "Camille ROUSSEL"
    assert [t.strip() for t in page.locator(".chapitre").all_inner_texts()] == ["0 à 9 ans", "10 à 19 ans", "20 à 29 ans", "30 à 39 ans"]
    assert page.locator(".etape").count() == 8                     # les temps forts seulement
    page.get_by_role("button", name="Tout", exact=True).click()
    assert page.locator(".etape").count() == 11
    assert page.locator(".etape.petite").count() == 2
    assert page.get_by_text("d'avant sa naissance").is_visible()
    sans_debordement(page)


def test_une_etape_et_ses_photos(page):
    page.goto(page.base + "/#/chemin/" + CAMILLE)
    page.get_by_role("button", name="Mariage de Camille et Hugo, 40 photos").click()
    assert page.locator(".galerie li").count() == 40
    page.get_by_role("button", name="Photo 1", exact=True).click()
    assert page.get_by_role("group", name="Photo 1 sur 40").is_visible()
    page.keyboard.press("ArrowLeft")
    assert page.get_by_role("group", name="Photo 40 sur 40").is_visible()
    page.get_by_role("button", name="Photo suivante").click()
    assert page.get_by_role("group", name="Photo 1 sur 40").is_visible()
    assert page.get_by_role("link", name="Ouvrir dans Immich").get_attribute("href").startswith("http://photos.exemple/photos/")
    # La croix se ferme en cliquant en son centre : rien ne la recouvre (le compteur passait dessus)
    croix = page.get_by_role("button", name="Fermer la photo").bounding_box()
    assert page.evaluate("([x, y]) => document.elementFromPoint(x, y).closest('button')?.getAttribute('aria-label')",
                         [croix["x"] + croix["width"] / 2, croix["y"] + croix["height"] / 2]) == "Fermer la photo"
    for dy in (0.15, 0.5, 0.85):
        assert page.evaluate("([x, y]) => document.elementFromPoint(x, y).closest('button')?.getAttribute('aria-label')",
                             [croix["x"] + croix["width"] / 2, croix["y"] + croix["height"] * dy]) == "Fermer la photo"
    sans_debordement(page)
    page.keyboard.press("Escape")
    assert page.locator(".plein").count() == 0 and page.locator(".galerie").is_visible()


def test_012_voir_tout_l_album(page):
    page.goto(page.base + "/#/chemin/" + CAMILLE)
    page.reload()                                               # repart d'une page sans étape ouverte
    page.get_by_role("button", name="Mariage de Camille et Hugo, 40 photos").click()
    # 0.12.2 : toutes les croix au même endroit (étape, photo, album, photo de l'album)
    place = lambda nom: tuple(round(v) for k, v in page.get_by_role("button", name=nom, exact=True).bounding_box().items() if k in ("x", "y"))
    coin = place("Fermer l'étape")
    page.get_by_role("button", name="Photo 1", exact=True).click()
    assert place("Fermer la photo") == coin and page.get_by_role("button", name="Fermer l'étape").count() == 0
    page.get_by_role("button", name="Voir tout l'album").click()
    album = page.get_by_role("dialog", name="Album Mariage de Camille et Hugo")
    album.wait_for()
    album.locator(".grille li").first.wait_for()
    assert album.locator(".grille li").count() == 40
    assert place("Fermer l'album") == coin and page.get_by_role("button", name="Fermer la photo").count() == 0
    album.get_by_role("button", name="Photo 3", exact=True).click()
    assert place("Revenir à l'album") == coin
    assert album.get_by_role("group", name="Photo 3 sur 40").is_visible()
    page.keyboard.press("ArrowRight")
    assert album.get_by_role("group", name="Photo 4 sur 40").is_visible()
    page.keyboard.press("Escape")                               # revient à la grille de l'album
    assert album.locator(".grille").is_visible()
    sans_debordement(page)
    page.keyboard.press("Escape")                               # ferme l'album, la photo de l'étape reste ouverte
    assert album.count() == 0 and page.locator(".plein").is_visible()
    page.keyboard.press("Escape")                               # la photo : l'étape reste ouverte, comme le test précédent la laisse
    assert page.locator(".galerie").is_visible()

    page.keyboard.press("Escape")
    assert page.locator(".galerie").count() == 0


def test_corriger_une_etape_et_une_photo(page):
    page.goto(page.base + "/#/chemin/" + CAMILLE)
    page.get_by_role("button", name=re.compile("^Communion")).click()
    page.get_by_role("button", name="Corriger l'étape").click()
    page.get_by_label("Nom de l'étape").fill("Communion de Camille")
    page.get_by_role("button", name="Nommer", exact=True).click()
    page.get_by_role("heading", name="Communion de Camille").wait_for()
    page.get_by_role("button", name="Rendre le nom d'origine").click()
    page.get_by_role("heading", name="Communion", exact=True).wait_for()
    # Une photo : la choisir comme phare, puis en retirer une autre
    # (les deux écrans partagent le même serveur : chacun choisit sa photo)
    page.get_by_role("button", name="Photo 3" if page.ecran == "pc" else "Photo 2", exact=True).click()
    page.get_by_role("button", name="En faire la photo phare").click()
    page.get_by_role("button", name="Photo phare", exact=True).wait_for()
    page.get_by_role("button", name="Photo suivante").click()
    page.get_by_role("button", name="Ce n'est pas cette personne").click()
    page.get_by_role("group", name=re.compile("Photo [34] sur 6")).wait_for()
    sans_debordement(page)
    page.keyboard.press("Escape")
    # Masquer l'étape : elle quitte le chemin, on la retrouve par « Tes corrections »
    page.get_by_role("button", name="Masquer cette étape").click()
    page.get_by_role("button", name="Remettre l'étape dans le chemin").wait_for()
    page.keyboard.press("Escape")
    page.get_by_role("button", name=re.compile("^Communion")).wait_for(state="detached")
    page.get_by_role("button", name="Afficher 1 étape masquée").click()
    page.get_by_role("button", name=re.compile("^Communion")).wait_for()
    page.get_by_role("button", name="Afficher 1 photo mise de côté").click()
    page.get_by_text("Pas cette personne").wait_for()
    page.get_by_role("button", name="Remettre").click()
    page.get_by_role("button", name=re.compile("mise de côté")).wait_for(state="detached")
    sans_debordement(page)
    # On remet tout pour l'écran suivant
    page.get_by_role("button", name=re.compile("^Communion")).click()
    page.get_by_role("button", name="Corriger l'étape").click()
    page.get_by_role("button", name="Remettre l'étape dans le chemin").click()
    page.get_by_role("button", name="Masquer cette étape").wait_for()
    page.keyboard.press("Escape")


def test_connexion_et_reglages(page):
    # 0.21 : écran commun des fiches « Connexion » (4 services : des tuiles, la fiche s'ouvre au toucher)
    page.goto(page.base + "/#/connexion")
    page.locator("#tuile-immich").click()
    page.get_by_role("button", name="Vérifier").click()
    page.get_by_text("Répond, version 3.4.1. 2 personnes nommées.").wait_for()
    sans_debordement(page)
    page.locator("#tuile-millesime").click()
    page.get_by_role("button", name="Vérifier").click()
    page.get_by_text("2 scans datés par estimation, dits « vers … » ; 1 en attente de date, hors du chemin.").wait_for()   # 0.14
    page.locator("#tuile-carnet").click()
    page.get_by_role("button", name="Vérifier").click()                           # 0.22 : relié (faux carnet de démonstration)
    page.get_by_text(re.compile(r"^Répond\. 0 fiche")).wait_for()
    page.goto(page.base + "/#/reglages")
    from app import __version__
    page.get_by_text(f"Sillage {__version__}").wait_for()
    sans_debordement(page)
    # 0.16 : les réglages du chemin se changent ici ; un mauvais nombre est refusé avec un message clair
    playwright.expect(page.locator("#r-non-datee")).to_have_value("Lots/Non datée")
    page.fill("#r-cache", "beaucoup")
    page.get_by_role("button", name="Garder").click()
    page.get_by_text("Place des vignettes : un nombre entier").wait_for()
    page.fill("#r-cache", "400")
    page.get_by_role("button", name="Garder").click()
    page.get_by_text("Gardé. Les chemins").wait_for()
    sans_debordement(page)
    # 0.25 : sillages préparés d'avance (le carnet de démonstration n'a aucune fiche)
    bloc = page.locator("section", has=page.get_by_role("heading", name="Sillages préparés"))
    bloc.get_by_text("0 sur 0 prêt").wait_for()
    bloc.get_by_role("button", name="Préparer les sillages maintenant").click()
    bloc.get_by_text("Préparation lancée, en fond.").wait_for()
    sans_debordement(page)


def test_016_restaurer_les_reglages(page):
    """0.16 : choisir une date, voir les différences (avant → sauvegardé), confirmer (faux Anneau sans réseau)."""
    page.goto(page.base + "/#/reglages")
    page.get_by_role("button", name="Voir les sauvegardes").click()
    page.locator("ul[aria-label='Différences avec la sauvegarde']").wait_for()
    assert page.locator("#r-date option").all_inner_texts() == ["2026-11-15", "2026-11-14"]
    page.get_by_text("Place des vignettes (Mo)", exact=True).last.wait_for()
    sans_debordement(page)
    page.get_by_role("button", name="Restaurer ces réglages").click()
    page.get_by_role("button", name="Confirmer").click()
    page.get_by_text("Réglages du 2026-11-15 restaurés.").wait_for()
    playwright.expect(page.locator("#r-cache")).to_have_value("300")
    playwright.expect(page.locator("#r-muets")).to_have_value("Fourre-tout")
    playwright.expect(page.locator("#r-non-datee")).to_have_value("Lots/Non datée")
    sans_debordement(page)


# ------------------------------------------------------------ 0.5 : la page d'un invité

def invitations():
    import json
    racine = Path(DOSSIER["ui"])
    for _ in range(100):
        if (racine / "invites.json").exists():
            return json.loads((racine / "invites.json").read_text())
        time.sleep(0.1)
    pytest.fail("Les invitations de démonstration n'ont pas été créées.")


def test_050_l_invite_voit_son_chemin_sans_mot_de_passe(page):
    jetons = invitations()
    page.context.clear_cookies()                                                        # pas de session : l'invité n'a pas le mot de passe
    page.goto(page.base + jetons["seule"])
    page.get_by_text("Votre chemin", exact=True).wait_for()
    assert page.locator("h1").inner_text().lower() == "votre chemin"                    # 0.7 : une ligne, plus de titre
    assert page.locator("nav[aria-label='Sections']").count() == 0                       # ni navigation, ni corrections, ni Immich
    assert page.get_by_role("button", name="Corriger l'étape").count() == 0 and page.get_by_text("Immich").count() == 0
    assert page.locator(".etape").count() == 8                                          # les temps forts d'abord
    page.get_by_role("button", name="Tout", exact=True).click()
    assert page.locator(".etape").count() == 11
    for src in page.locator(".etape img").evaluate_all("els => els.slice(0, 3).map(e => e.src)"):
        assert page.request.get(src).status == 200                                       # les photos phares passent par le jeton
    page.locator(".etape .ouvrir").first.click()                                        # 0.8 : la photo phare en grand
    page.get_by_role("dialog").wait_for()
    assert page.locator(".grand img").evaluate("i => i.getBoundingClientRect().width") > page.locator(".etape img").first.evaluate("i => i.getBoundingClientRect().width") * 0.9
    # 0.12.1 : « Voir l'album » montre au moins les photos de l'étape, même hors de tout album
    page.get_by_role("button", name="Voir l'album").click()
    grille = page.locator(".album .grille li")
    grille.first.wait_for()
    assert grille.count() >= 1
    for src in page.locator(".album .grille img").evaluate_all("els => els.map(e => e.src)"):
        assert page.request.get(src).status == 200
    page.keyboard.press("Escape")                                                       # ferme l'album
    page.keyboard.press("Escape")
    assert page.get_by_role("dialog").count() == 0
    sans_debordement(page)


def test_050_deux_invites_le_chemin_commun(page):
    jetons = invitations()
    page.context.clear_cookies()
    page.goto(page.base + jetons["couple"])
    page.get_by_text("Votre chemin ensemble").wait_for()
    assert page.locator(".legende li").all_inner_texts() == ["Camille", "Hugo", "Ensemble"]   # 0.7 : une couleur chacun (0.11 : des boutons)
    if page.get_by_role("button", name="Tout", exact=True).count():
        page.get_by_role("button", name="Tout", exact=True).click()
    titres = [t.strip() for t in page.locator(".chapitre").all_inner_texts()]
    assert "Années 2000" in titres and "Années 2010" in titres
    mariage = page.locator(".etape", has_text="Mariage de Camille et Hugo")
    assert "Ensemble" in mariage.inner_text().title()
    couleurs = set(page.locator(".etape.colore").evaluate_all("els => els.map(e => getComputedStyle(e.querySelector('.carte')).borderLeftColor)"))
    assert len(couleurs) == 3                                                           # Camille, Hugo, ensemble
    # 0.11 : un clic sur un prénom ne garde que ses étapes ; plusieurs à la fois ; « Tout montrer » revient à tout
    toutes = page.locator(".etape").count()
    page.locator(".legende").get_by_role("button", name="Ensemble").click()
    qui = set(t.strip().title() for t in page.locator(".etape .qui").all_inner_texts())
    assert qui == {"Ensemble"} and 0 < page.locator(".etape").count() < toutes
    page.locator(".legende").get_by_role("button", name="Camille").click()
    assert set(t.strip().title() for t in page.locator(".etape .qui").all_inner_texts()) <= {"Ensemble", "Camille"}
    assert page.locator(".legende").get_by_role("button", name="Camille").get_attribute("aria-pressed") == "true"
    page.locator(".legende").get_by_role("button", name="Tout montrer").click()
    assert page.locator(".etape").count() == toutes
    page.goto(page.base + jetons["inconnu"])
    page.get_by_text("Pas encore de souvenirs ici").wait_for()
    page.goto(page.base + "/invite/jeton-inconnu")
    page.get_by_text("n'est plus valable").wait_for()
    sans_debordement(page)


def test_060_onglet_chambres_apercu_des_invites(page):
    invitations()
    page.goto(page.base + "/#/chambres")
    if page.locator("#mot-de-passe").count():                                        # les tests de l'invité ont vidé les cookies
        page.fill("#mot-de-passe", MDP)
        page.click("button[type=submit]")
    page.get_by_role("heading", name="Chambres", exact=True).wait_for()
    choix = page.locator("[aria-label=Chambre] button")
    assert sorted(choix.all_inner_texts()) == ["Chambre Couple", "Chambre Inconnu", "Chambre Seule"]
    page.get_by_role("button", name="Chambre Couple").click()
    page.get_by_text("Votre chemin ensemble").wait_for()
    assert "Camille ROUSSEL et Hugo MARCHAND" in page.locator(".fiche").inner_text()
    page.get_by_role("button", name="Chambre Inconnu").click()
    page.get_by_text("pas de personne de ce nom dans Immich").wait_for()
    page.get_by_text("Pas encore de souvenirs ici").wait_for()
    assert page.locator("main main").count() == 0                                    # l'aperçu n'ouvre pas une seconde page
    sans_debordement(page)


# ------------------------------------------------------------ 0.14 : scans de Millésime, date de fin

def test_014_scans_vers(page):
    from tests.faux_immich import HUGO
    page.goto(page.base + "/#/chemin/" + HUGO)
    if page.locator("#mot-de-passe").count():                                        # les tests de l'invité ont vidé les cookies
        page.fill("#mot-de-passe", MDP)
        page.click("button[type=submit]")
        page.goto(page.base + "/#/chemin/" + HUGO)
    page.wait_for_selector(".etape")
    scans = page.locator(".etape", has_text="vers 1978")
    assert scans.count() == 1 and "2 photos" in scans.inner_text()
    assert scans.locator(".point.vers").count() == 1                                  # le point en pointillé
    assert page.get_by_text("1 scan pas encore daté").is_visible()
    assert page.get_by_role("button", name="Ajouter une date de décès").count() == 0   # 0.14.1 : pas de saisie dans Sillage
    sans_debordement(page)


# ------------------------------------------------------------ 0.22 : arbre de famille en 3D

def _connecte(page, adresse):
    page.goto(page.base + adresse)
    if page.locator("#mot-de-passe").count():                                        # les tests de l'invité ont vidé les cookies
        page.fill("#mot-de-passe", MDP)
        page.click("button[type=submit]")
        page.goto(page.base + adresse)


def test_022_arbre_du_proprietaire(page):
    """0.24 : trois vues (Vie 3D à l'ouverture, avec « Proches » ou « Tout l'arbre » ; Éventail ; Arbre), carte d'une
    personne, et « Lien avec… » qui dit le lien et l'écrit en étapes."""
    _connecte(page, "/#/chemin/" + CAMILLE)
    page.wait_for_selector(".etape")
    page.get_by_role("button", name="Voir son arbre de famille").click()
    page.get_by_role("dialog", name="L'arbre de Camille ROUSSEL").wait_for()
    if page.get_by_role("button", name="Compris").count():
        page.get_by_role("button", name="Compris").click()
    for retiree in ("Constellation", "Sablier", "Hélice"):
        assert page.get_by_role("button", name=retiree, exact=True).count() == 0
    page.locator(".arbre canvas").wait_for()                                          # Vie 3D d'emblée
    # 0.26.1 : toucher le titre cache les réglages de la vue (et les remontre), gardé sur l'appareil
    page.get_by_role("button", name="Cacher les réglages de la vue").click()
    assert page.get_by_role("button", name="Éventail", exact=True).count() == 0
    assert page.evaluate("localStorage.getItem('sillage-arbre-replie')") == "1"
    sans_debordement(page)
    page.get_by_role("button", name="Montrer les réglages de la vue").click()
    assert page.get_by_role("button", name="Vie 3D", exact=True).get_attribute("aria-pressed") == "true"
    page.get_by_role("button", name="Tout l'arbre").click()
    assert page.get_by_role("button", name="Tout l'arbre").get_attribute("aria-pressed") == "true"
    assert page.evaluate("localStorage.getItem('sillage-arbre-vie-tout')") == "1"
    page.get_by_role("button", name="Proches").click()
    for vue in ("Éventail", "Arbre"):
        page.get_by_role("button", name=vue, exact=True).click()
        page.locator("svg.plan .personne").first.wait_for()
    assert page.get_by_role("button", name="Proches").count() == 0                   # seulement en Vie 3D
    page.get_by_role("button", name="Liste").click()
    page.locator(".panneau").get_by_role("button", name=re.compile("Hugo MARCHAND")).click()
    carte = page.locator(".carte")
    carte.get_by_text("Conjoint de Camille", exact=False).wait_for()
    assert carte.get_by_role("link", name="Voir son sillage").count() == 1
    assert carte.get_by_role("link", name="Ouvrir dans carnet").count() == 1
    # Hugo est maintenant au centre : « Lien avec… » Léa
    page.get_by_role("button", name="Lien avec…").click()
    page.locator(".panneau").get_by_role("button", name=re.compile("^Léa MARCHAND")).click()
    resultat = page.locator(".resultat")
    resultat.get_by_role("button", name="Fermer").wait_for()                          # 0.26.3 : deux boutons seulement
    assert resultat.get_by_role("button", name="Voir à plat").count() == 0           # déjà à plat
    lu = resultat.locator(".sr-only").text_content()                                  # le lien reste dit au lecteur d'écran
    assert "fille de Hugo" in lu and "sa fille Léa" in lu
    assert page.locator("svg.plan .personne[opacity='1']").count() == 2              # seul le chemin reste allumé
    page.keyboard.press("Escape")                                                     # efface le lien
    assert page.locator(".resultat").count() == 0
    # 0.23.1 : en éventail, le lien s'affiche en schéma, de la personne au centre jusqu'à la personne cherchée
    page.get_by_role("button", name="Éventail", exact=True).click()
    page.get_by_role("button", name="Lien avec…").click()
    page.locator(".panneau").get_by_role("button", name=re.compile("^Léa MARCHAND")).click()
    resultat.get_by_role("button", name="Voir à plat").wait_for()
    assert page.locator("svg.plan .personne").count() == 2                            # Hugo et Léa, rien d'autre
    assert "Fille" in page.locator("svg.plan").text_content()
    resultat.get_by_role("button", name="Fermer").click()
    assert page.locator(".resultat").count() == 0
    assert page.locator("svg.plan .personne").count() > 2                             # l'éventail revient
    # 0.26.2 : en Vie 3D, le chemin s'allume sur le cylindre de « Tout l'arbre » (pas de schéma)
    page.get_by_role("button", name="Vie 3D", exact=True).click()
    page.locator(".arbre canvas").wait_for()
    page.get_by_role("button", name="Lien avec…").click()
    page.locator(".panneau").get_by_role("button", name=re.compile("^Léa MARCHAND")).click()
    resultat.get_by_role("button", name="Voir à plat").wait_for()
    assert resultat.bounding_box()["height"] < 70                                    # pas de pavé sur l'arbre
    assert page.get_by_role("button", name="Proches").count() == 0
    assert page.locator(".arbre canvas").count() == 1
    page.keyboard.press("Escape")                                                     # efface le lien
    page.get_by_role("button", name="Proches").wait_for()
    page.keyboard.press("Escape")                                                     # ferme l'arbre
    assert page.get_by_role("dialog").count() == 0
    sans_debordement(page)


def test_022_arbre_de_l_invite_et_proposition(page):
    jetons = invitations()
    page.context.clear_cookies()
    page.goto(page.base + jetons["seule"])
    page.get_by_role("button", name="Votre arbre de famille").click()
    page.get_by_role("dialog", name="Votre arbre de famille").wait_for()
    page.locator(".arbre svg.plan .personne, .arbre canvas").first.wait_for()
    page.get_by_role("button", name="Liste").click()
    panneau = page.locator(".panneau")
    noms = panneau.locator("button > span:first-child").all_inner_texts()
    assert "Léa" in noms and "Léa MARCHAND" not in noms                               # mineure : prénom seulement
    assert "Personne non montrée" in noms                                             # case « jamais aux invités »
    panneau.get_by_role("button", name=re.compile("^Léa")).click()
    carte = page.locator(".carte")
    carte.get_by_text("Fille", exact=False).wait_for()
    assert carte.get_by_role("link").count() == 0                                     # ni sillage, ni carnet, ni Immich
    carte.get_by_role("button", name="Proposer une correction").click()
    carte.get_by_label("La bonne date").fill("2016-05-02")
    carte.get_by_role("button", name="Envoyer à Julien").click()
    carte.get_by_text("Merci, c'est transmis à Julien").wait_for()
    # « Lien avec… » aussi pour l'invité, sans les personnes non montrées
    page.get_by_role("button", name="Lien avec…").click()
    choix = page.locator(".panneau button > span:first-child").all_inner_texts()
    assert "Personne non montrée" not in choix
    page.locator(".panneau").get_by_role("button", name=re.compile("^Hugo")).click()
    page.locator(".resultat").get_by_role("button", name="Fermer").wait_for()
    assert "de Léa" in page.locator(".resultat .sr-only").text_content()
    sans_debordement(page)


def test_026_quoi_de_neuf_du_proprietaire(page):
    """0.26 : bloc « Quoi de neuf » de la liste des sillages ; toucher une ligne ouvre le sillage sur l'étape, les photos
    nouvelles marquées. La réponse de /api/nouveautes est simulée (le carnet de démonstration n'a aucune fiche)."""
    import json
    _connecte(page, "/#/chemin/" + CAMILLE)
    page.wait_for_selector(".etape")
    ch = page.evaluate(f"fetch('/api/chemin/{CAMILLE}').then(r => r.json())")
    etape = next(e for c in ch["chapitres"] for e in c["etapes"] if e["nombre"] > 1)
    neuves = [p["id"] for p in etape["photos"][:2]]
    reponse = {"depuis": "2026-10-28", "jours": 30, "personnes": [{
        "personne": CAMILLE, "nom": "Camille ROUSSEL", "ajoutee_le": "2026-11-26", "autres_photos": 4, "autres_etapes": 2,
        "etapes": [{"cle": etape["cle"], "nom": etape["nom"], "debut": etape["debut"], "fin": etape["fin"], "photos": 2,
                    "nombre": etape["nombre"], "nouvelle": False, "retrouvee": True, "phare": etape["phare"],
                    "ajoutee_le": "2026-11-26"}]}]}
    page.route("**/api/nouveautes", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(reponse)))
    page.route(f"**/api/chemin/{CAMILLE}", lambda r: r.fulfill(
        status=200, content_type="application/json", body=json.dumps({**r.fetch().json(), "nouvelles": neuves})))
    page.goto(page.base + "/#/sillages")
    bloc = page.locator("section.neuf")
    bloc.get_by_text("Camille ROUSSEL").wait_for()
    bloc.get_by_text("et 4 photos dans 2 autres étapes").wait_for()
    sans_debordement(page)
    bloc.get_by_role("link", name=re.compile(r"^\+2 photos")).click()
    page.get_by_role("dialog").wait_for()                                             # l'étape est ouverte
    assert page.locator(".galerie .neuve").count() == 2
    assert page.locator(".etape .neuf").count() >= 1
    page.keyboard.press("Escape")
    # 0.26.4 : « J'ai vu » ferme le bloc
    page.route("**/api/nouveautes/vu", lambda r: r.fulfill(status=200, content_type="application/json", body='{"ok": true}'))
    page.goto(page.base + "/#/sillages")
    page.locator("section.neuf").get_by_role("button", name="J'ai vu").click()
    page.locator("section.neuf").wait_for(state="detached")
    page.unroute("**/api/nouveautes/vu")
    page.unroute("**/api/nouveautes")
    page.unroute(f"**/api/chemin/{CAMILLE}")


def test_026_du_nouveau_pour_l_invite(page):
    """0.26 : bloc « Du nouveau depuis votre dernier séjour » en haut de la page de l'invité (réponse simulée)."""
    import json
    jetons = invitations()
    page.context.clear_cookies()
    adresse = jetons["seule"]
    jeton = adresse.rsplit("/", 1)[1]

    def avec_neuf(route):
        d = route.fetch().json()
        c = (d["commun"] or d["chacun"][0])
        e = [x for ch in c["chapitres"] for x in ch["etapes"]][-1]
        d["nouveautes"] = {"depuis": "2026-08-17", "autres_photos": 3, "autres_etapes": 1,
                           "etapes": [{"cle": e["cle"], "nom": e["nom"], "debut": e["debut"], "photos": 5, "nouvelle": True,
                                       "retrouvee": False, "phare": e["phare"]}]}
        route.fulfill(status=200, content_type="application/json", body=json.dumps(d))
    page.route(f"**/api/invite/{jeton}", avec_neuf)
    page.goto(page.base + adresse)
    bloc = page.locator("section.neuf")
    bloc.get_by_text("Du nouveau depuis votre dernier séjour").wait_for()
    bloc.get_by_text("17 août 2026").wait_for()
    bloc.get_by_text("Et 3 photos de plus dans le chemin.").wait_for()
    sans_debordement(page)
    bloc.get_by_role("button").first.click()
    page.wait_for_timeout(600)
    page.unroute(f"**/api/invite/{jeton}")
