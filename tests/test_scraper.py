"""Collection rules, tested on small hand-written pages (no network).

Run with: python -m unittest discover tests
"""
import json
import unittest
from unittest import mock

import scraper

LISTING = """<html><body>
<a href="/fr/evenements/midweek-jazz-jam_Ab12/">Midweek Jazz Jam</a>
<a href="/fr/evenements/midweek-jazz-jam_Ab12/#infos">doublon</a>
<a href="/fr/evenements/karaoke-open-mic_Cd34">Karaoké</a>
<a href="/fr/evenements/lausanne">pas un événement</a>
<a href="https://ailleurs.ch/fr/evenements/x_Ef56">autre site</a>
</body></html>"""
GUIDLE = "https://www.guidle.com/fr/evenements/lausanne"


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


class DetailPagesTest(unittest.TestCase):
    def test_links_are_filtered_and_deduplicated(self):
        soup = scraper.BeautifulSoup(LISTING, "lxml")
        links = scraper._detail_links(soup, GUIDLE, r"^/fr/evenements/[^/]+_[A-Za-z0-9]+/?$")
        self.assertEqual(links, ["https://www.guidle.com/fr/evenements/midweek-jazz-jam_Ab12/",
                                 "https://www.guidle.com/fr/evenements/karaoke-open-mic_Cd34"])

    def test_listing_page_follows_event_pages(self):
        pages = {
            GUIDLE: LISTING,
            "https://www.guidle.com/fr/evenements/midweek-jazz-jam_Ab12/":
                event_page("Midweek Jazz Jam", "2026-10-21T20:30:00+02:00", "Jumeaux Jazz Club"),
            "https://www.guidle.com/fr/evenements/karaoke-open-mic_Cd34":
                event_page("Karaoké & open mic", "2026-10-18T19:00:00+02:00", "Barberousse"),
        }
        with mock.patch.object(scraper, "_fetch", side_effect=lambda url: pages[url]):
            events, method = scraper.scrape_one(GUIDLE)
        self.assertTrue(method.startswith("pages-detail"))
        self.assertEqual([e["location"] for e in events], ["Jumeaux Jazz Club", "Barberousse"])

    def test_failed_detail_page_is_skipped(self):
        def fetch(url):
            if url.endswith("karaoke-open-mic_Cd34"):
                raise scraper.FetchError("404")
            if url == GUIDLE:
                return LISTING
            return event_page("Midweek Jazz Jam", "2026-10-21T20:30:00+02:00", "Jumeaux Jazz Club")
        with mock.patch.object(scraper, "_fetch", side_effect=fetch):
            events, _ = scraper.scrape_one(GUIDLE)
        self.assertEqual(len(events), 1)


class UndatedTest(unittest.TestCase):
    def test_events_without_a_date_are_not_kept(self):
        found = [
            {"id": "a", "title": "Avec date", "date": "2026-10-21"},
            {"id": "b", "title": "Sans date", "date": ""},
            {"id": "c", "title": "Date illisible", "date": "bientôt"},
        ]
        with mock.patch.object(scraper, "scrape_one", return_value=(found, "html")), \
                mock.patch.object(scraper.db, "log_scrape") as log:
            events = scraper.scrape_sources(["https://lieu.ch/agenda"])
        self.assertEqual([e["id"] for e in events], ["a"])
        log.assert_called_once_with("scraper", "https://lieu.ch/agenda", "ok", 1,
                                    "html · 2 sans date écartés")

    def test_source_with_only_undated_events_counts_as_empty(self):
        with mock.patch.object(scraper, "scrape_one", return_value=([{"id": "b", "title": "x", "date": ""}], "html")), \
                mock.patch.object(scraper.db, "log_scrape") as log:
            self.assertEqual(scraper.scrape_sources(["https://lieu.ch/agenda"]), [])
        self.assertEqual(log.call_args.args[2:4], ("empty", 0))


if __name__ == "__main__":
    unittest.main()
