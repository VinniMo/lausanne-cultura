"""Collection rules, tested on small hand-written pages (no network).

Run with: python -m unittest discover tests
"""
import dataclasses
import json
import os
import tempfile
import unittest
from unittest import mock

import db
import scraper

LISTING = """<html><body>
<a href="/fr/evenement/midweek-jazz-jam/">Midweek Jazz Jam</a>
<a href="/fr/evenement/midweek-jazz-jam/#infos">doublon</a>
<a href="/fr/evenement/karaoke-open-mic">Karaoké</a>
<a href="/fr/decouvrir/barberousse/">pas un événement</a>
<a href="https://ailleurs.ch/fr/evenement/x">autre site</a>
</body></html>"""


def event_page(name, start, venue, offers=None, graph=False):
    item = {"@type": ["Event", "MusicEvent"], "name": name, "startDate": start,
            "location": {"@type": "Place", "name": venue,
                         "address": {"streetAddress": "Rue de Genève 19", "postalCode": "1003",
                                     "addressLocality": "Lausanne"}}}
    if offers is not None:
        item["offers"] = offers
    data = {"@context": "https://schema.org", "@graph": [{"@type": "WebPage"}, item]} if graph else item
    return f'<html><script type="application/ld+json">{json.dumps(data)}</script></html>'


class JsonLdTest(unittest.TestCase):
    def test_graph_type_list_offers_and_swiss_time(self):
        html = event_page("Midweek Jazz Jam", "2026-10-21T18:30:00Z", "Jumeaux Jazz Club",
                          offers={"price": 0, "priceCurrency": "CHF"}, graph=True)
        [evt] = scraper._extract_jsonld_events(scraper.BeautifulSoup(html, "lxml"), "https://x.ch/e")
        self.assertEqual(evt["time"], "20:30")  # 18:30 UTC = 20:30 in Lausanne (summer time)
        self.assertEqual(evt["price"], "Gratuit")
        self.assertEqual(evt["location"], "Jumeaux Jazz Club")
        self.assertEqual(evt["address"], "Rue de Genève 19, 1003, Lausanne")
        self.assertEqual(evt["url"], "https://x.ch/e")

    def test_price_range_and_unknown(self):
        self.assertEqual(scraper._extract_price({"lowPrice": 15, "highPrice": 30, "priceCurrency": "CHF"}), "CHF 15–30")
        self.assertEqual(scraper._extract_price(None), "")


class IcsTest(unittest.TestCase):
    def test_vevent_with_folding_utc_and_all_day(self):
        ics = ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nSUMMARY:Jam d\\, octobre\r\n"
               "DTSTART:20261021T183000Z\r\nLOCATION:Satellite\\, EPFL\r\n"
               "DESCRIPTION:Une longue\r\n  description\r\nURL:https://memento.epfl.ch/e/1\r\nEND:VEVENT\r\n"
               "BEGIN:VEVENT\r\nSUMMARY:Expo\r\nDTSTART;VALUE=DATE:20261101\r\n"
               "DTEND;VALUE=DATE:20261130\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
        jam, expo = scraper.parse_ics(ics)
        self.assertEqual((jam["title"], jam["date"], jam["time"]), ("Jam d, octobre", "2026-10-21", "20:30"))
        self.assertEqual(jam["location"], "Satellite")
        self.assertEqual(jam["description"], "Une longue description")
        self.assertEqual((expo["date"], expo["time"], expo["end_date"]), ("2026-11-01", "", "2026-11-30"))


AGGREGATOR = "https://agenda.example.ch/fr/evenement/"
WITH_DETAIL_PAGES = dataclasses.replace(
    scraper.config, DETAIL_LINK_PATTERNS=(("agenda.example.ch", r"^/fr/evenement/[a-z0-9-]+/?$"),))


class DetailPagesTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(scraper, "config", WITH_DETAIL_PAGES)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_links_are_filtered_and_deduplicated(self):
        soup = scraper.BeautifulSoup(LISTING, "lxml")
        links = scraper._detail_links(soup, AGGREGATOR, r"^/fr/evenement/[a-z0-9-]+/?$")
        self.assertEqual(links, ["https://agenda.example.ch/fr/evenement/midweek-jazz-jam/",
                                 "https://agenda.example.ch/fr/evenement/karaoke-open-mic"])

    def test_listing_page_follows_event_pages(self):
        pages = {
            AGGREGATOR: LISTING,
            AGGREGATOR + "midweek-jazz-jam/":
                event_page("Midweek Jazz Jam", "2026-10-21T20:30:00+02:00", "Jumeaux Jazz Club"),
            AGGREGATOR + "karaoke-open-mic":
                event_page("Karaoké & open mic", "2026-10-18T19:00:00+02:00", "Barberousse"),
        }
        with mock.patch.object(scraper, "_fetch", side_effect=lambda url: pages[url]):
            events, method, complete = scraper.scrape_one(AGGREGATOR)
        self.assertTrue(method.startswith("pages-detail"))
        self.assertTrue(complete)
        self.assertEqual([e["location"] for e in events], ["Jumeaux Jazz Club", "Barberousse"])

    def test_failed_detail_page_is_skipped(self):
        def fetch(url):
            if url.endswith("karaoke-open-mic"):
                raise scraper.FetchError("404")
            if url == AGGREGATOR:
                return LISTING
            return event_page("Midweek Jazz Jam", "2026-10-21T20:30:00+02:00", "Jumeaux Jazz Club")
        with mock.patch.object(scraper, "_fetch", side_effect=fetch):
            events, _, complete = scraper.scrape_one(AGGREGATOR)
        self.assertEqual(len(events), 1)
        self.assertFalse(complete)

    def test_listing_cut_at_max_detail_pages_is_incomplete(self):
        page = event_page("Midweek Jazz Jam", "2026-10-21T20:30:00+02:00", "Jumeaux Jazz Club")
        fetch = lambda url: LISTING if url == AGGREGATOR else page
        with mock.patch.object(scraper, "_fetch", side_effect=fetch), \
                mock.patch.object(scraper, "config", dataclasses.replace(WITH_DETAIL_PAGES, MAX_DETAIL_PAGES=1)):
            events, _, complete = scraper.scrape_one(AGGREGATOR)
        self.assertEqual(len(events), 1)
        self.assertFalse(complete)


class UnknownFormatTest(unittest.TestCase):
    def test_page_without_a_known_format_gives_no_event(self):
        # Guessing from the layout turned menus and headings into dateless events.
        html = ('<html><body><div class="card"><h3>Billetterie et abonnements</h3></div>'
                '<article class="event"><h3>Concert : Trio Nova</h3></article></body></html>')
        with mock.patch.object(scraper, "_fetch", return_value=html):
            events, method, _ = scraper.scrape_one("https://salle.ch/agenda")
        self.assertEqual((events, method), ([], "aucun format reconnu"))


def lt_card(title, dates, venue=None, teaser=""):
    place = f'<span class="gmtLocation">{venue}</span>' if venue else ""
    return f"""<div class="teaser teaser--hoverable teaser--post-type-event">
      <a href="https://www.lausanne-tourisme.ch/fr/evenement/{title.lower().replace(' ', '-')}/">
        <img class="teaser__image" src="https://static.lausanne-tourisme.ch/image/upload/x"/>
        <div class="teaser__suptitle"><span><div class="date__date">{dates}</div></span></div>
        <div class="teaser__subtitle">{place}</div>
        <div class="teaser__title">{title}</div><div class="teaser__content">{teaser}</div>
      </a></div>"""


LT_PAGE = "<html><main>" + "".join([
    lt_card("Monsoon Wedding", "01.11.2026", "Cinémathèque suisse", "Portrait de famille inoubliable..."),
    lt_card("Giacometti", "27.05.2026 - 16.12.2026", "Fondation Gianadda"),
    lt_card("Karaoké", "18.10.2026"),
    lt_card("Fête sans date", ""),
    lt_card("", "18.10.2026"),
]) + "</main></html>"


class LausanneTourismeTest(unittest.TestCase):
    def test_cards_give_dates_ranges_venues_and_links(self):
        with mock.patch.object(scraper, "_fetch", return_value=LT_PAGE):
            events, method, complete = scraper.scrape_one("https://www.lausanne-tourisme.ch/fr/evenement/")
        self.assertEqual((method, complete), ("lecteur lausanne-tourisme.ch", True))
        film, expo, karaoke, undated = events  # the card without a title is skipped
        self.assertEqual((film["date"], film["end_date"], film["location"]), ("2026-11-01", "", "Cinémathèque suisse"))
        self.assertEqual(film["category"], "Cinéma")  # the venue wins over "famille"
        self.assertEqual(film["url"], "https://www.lausanne-tourisme.ch/fr/evenement/monsoon-wedding/")
        self.assertEqual((expo["date"], expo["end_date"]), ("2026-05-27", "2026-12-16"))
        self.assertEqual((karaoke["location"], karaoke["time"], karaoke["price"]), ("", "", ""))
        self.assertEqual(undated["date"], "")


class DuplicatesTest(unittest.TestCase):
    def ev(self, title, source, venue="Théâtre de Beaulieu", day="2026-10-28"):
        return {"id": f"{title}|{venue}|{day}|{source}", "title": title, "date": day,
                "location": venue, "source": source}

    def test_same_event_from_two_sources_keeps_the_later_one(self):
        events = [self.ev("OCL: Grand Concert 2", AGENDA), self.ev("Les Grands Concerts n°2 | Christie", VENUE)]
        self.assertEqual([e["source"] for e in scraper._drop_duplicates(events)], [VENUE])

    def test_aliases_name_the_same_hall(self):
        events = [self.ev("OCL: Les Entractes 1", AGENDA, venue="Casino de Montbenon"),
                  self.ev("Les Entractes n°1 | Schubert", VENUE, venue="Salle Paderewski")]
        self.assertEqual(len(scraper._drop_duplicates(events)), 1)

    def test_different_events_are_kept(self):
        cases = [
            [self.ev("Jazz Jam", AGENDA), self.ev("Jazz Jam du mardi", AGENDA)],  # same source
            [self.ev("Jazz Jam", AGENDA), self.ev("Jazz Jam", VENUE + "x", venue="Les Docks")],  # other venue
            [self.ev("Concert de midi", AGENDA), self.ev("Concert du soir", VENUE)],  # only a generic word
            [self.ev("Jazz Jam", AGENDA), self.ev("Jazz Jam", VENUE, day="2026-10-29")],  # other day
        ]
        for events in cases:
            with self.subTest(events=[e["title"] for e in events]):
                self.assertEqual(len(scraper._drop_duplicates(events)), 2)


class FetchTest(unittest.TestCase):
    def test_text_without_declared_charset_is_read_as_utf8(self):
        resp = scraper.requests.Response()
        resp.status_code, resp._content = 200, "SUMMARY:L'OCL fête Beethoven".encode("utf-8")
        resp.headers["Content-Type"] = "text/calendar"
        with mock.patch.object(scraper.requests, "get", return_value=resp):
            self.assertEqual(scraper._fetch("https://x.ch/a.ics"), "SUMMARY:L'OCL fête Beethoven")


class CategorizeTest(unittest.TestCase):
    def test_keyword_inside_another_word_does_not_count(self):
        cases = {
            "Exposition : Maison de la photographie": "Exposition",  # "rap"
            "Visite guidée de l'art populaire": "Culture",  # "pop"
            "Conférence : le rapport au climat": "Conférence",  # "rap"
            "Atelier de djembé pour enfants": "Famille",  # "dj"
            "Soirée after-work au musée": "Exposition",  # "after"
            "Ciné-club : Les Parapluies de Cherbourg": "Cinéma",  # "rap"
            "Marché pop-up de créateurs": "Marché",  # "pop"
        }
        for title, category in cases.items():
            with self.subTest(title=title):
                self.assertEqual(scraper.categorize(title), category)

    def test_plurals_capitals_missing_accents_and_compounds(self):
        cases = {
            "Les concerts du dimanche": "Musique",
            "THEATRE : Les Bonnes": "Théâtre",
            "Soirée jazz-rock": "Musique",
            "Battle hip-hop": "Musique",
            "D! Club : techno all night": "Clubbing",
            "Afterparty officielle": "Clubbing",
            "Marionnettes pour les petits": "Famille",
        }
        for title, category in cases.items():
            with self.subTest(title=title):
                self.assertEqual(scraper.categorize(title), category)

    def test_description_counts_too(self):
        self.assertEqual(scraper.categorize("Nuit blanche", "trois films en plein air"), "Cinéma")

    def test_single_kind_venue_decides_mixed_venue_does_not(self):
        self.assertEqual(scraper.categorize("School of Rock", "Un rockeur viré", "Cinémathèque suisse"), "Cinéma")
        self.assertEqual(scraper.categorize("Godzilla", "", "Cinémathèque suisse"), "Cinéma")
        self.assertEqual(scraper.categorize("Jeanneto", "", "Le Romandie"), "Musique")
        self.assertEqual(scraper.categorize("Grand Concert 2", "", "Théâtre de Beaulieu"), "Musique")
        self.assertEqual(scraper.categorize("Hamlet", "", "Théâtre Vidy-Lausanne"), "Théâtre")


VENUE = "https://salle.ch/agenda"
AGENDA = "https://agenda.ch/lausanne"


def show(id_, day="2026-10-20"):
    return {"id": id_, "title": id_, "date": day}


class RefreshTest(unittest.TestCase):
    """Each source's list decides which of its events stay stored."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for patcher in (mock.patch.object(db, "DB_PATH", os.path.join(tmp.name, "events.db")),
                        mock.patch.object(scraper, "today_local", return_value=scraper.datetime(2026, 10, 13).date())):
            patcher.start()
            self.addCleanup(patcher.stop)
        db.init_db()

    def collect(self, pages):
        """One pass where each source gives (events, complete), or None when it is down."""
        def scrape_one(url):
            if pages[url] is None:
                raise scraper.FetchError("down")
            events, complete = pages[url]
            return [dict(e) for e in events], "json-ld", complete
        with mock.patch.object(scraper, "scrape_one", side_effect=scrape_one):
            scraper.refresh_database(list(pages))

    def stored(self):
        return {e["id"]: e["source"] for e in db.list_all_events()}

    def test_events_record_their_source(self):
        self.collect({AGENDA: ([show("a"), show("b")], True), VENUE: ([show("b")], True)})
        self.assertEqual(self.stored(), {"a": AGENDA, "b": VENUE})  # the venue, listed last, wins

    def test_event_no_longer_announced_is_removed(self):
        self.collect({VENUE: ([show("a"), show("b"), show("c")], True)})
        self.collect({VENUE: ([show("a"), show("b")], True)})
        self.assertEqual(set(self.stored()), {"a", "b"})

    def test_event_still_announced_elsewhere_is_kept(self):
        self.collect({AGENDA: ([show("a")], True), VENUE: ([show("a"), show("b")], True)})
        self.collect({AGENDA: ([show("a")], True), VENUE: ([show("b")], True)})
        self.assertEqual(self.stored(), {"a": AGENDA, "b": VENUE})

    def test_doubtful_runs_remove_nothing(self):
        first = [show("a"), show("b"), show("c"), show("d")]
        for second in (None, ([], True), ([show("a")], False), ([show("a")], True)):
            with self.subTest(second=second):
                db.clear_events()
                self.collect({VENUE: (first, True)})
                self.collect({VENUE: second})  # down, empty, incomplete, sudden drop
                self.assertEqual(set(self.stored()), {"a", "b", "c", "d"})

    def test_past_events_do_not_hold_back_removal(self):
        old = [show(f"old{i}", "2026-09-01") for i in range(5)]
        self.collect({VENUE: (old + [show("a"), show("b")], True)})
        self.collect({VENUE: ([show("a")], True)})  # 1 of 2 upcoming: not a sudden drop
        self.assertEqual(set(self.stored()), {"a"})


if __name__ == "__main__":
    unittest.main()
