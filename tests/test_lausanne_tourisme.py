"""Lausanne Tourisme reader, tested on pages cut from the real site.

The fixtures in tests/fixtures/lausanne_tourisme/ were saved on 13 October
2026 (a Tuesday), which is "today" in these tests.

Run with: python -m unittest discover tests
"""
import os
import unittest
from datetime import date

import scraper
from sources import lausanne_tourisme as lt, reader_for

HERE = os.path.join(os.path.dirname(__file__), "fixtures", "lausanne_tourisme")
LISTING_URL = "https://www.lausanne-tourisme.ch/fr/evenement/"
TODAY = date(2026, 10, 13)


def page(name):
    with open(os.path.join(HERE, f"{name}.html"), encoding="utf-8") as fh:
        return fh.read()


def fake_site(missing=()):
    """fetch() serving the saved event pages; any other page is missing."""
    calls = []

    def fetch(url):
        calls.append(url)
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        if slug in missing or not os.path.exists(os.path.join(HERE, f"{slug}.html")):
            raise scraper.FetchError("404")
        return page(slug)
    return fetch, calls


def collect(missing=()):
    fetch, calls = fake_site(missing)
    raw = lt.read(page("liste"), LISTING_URL, fetch, TODAY, pause=0)
    return [scraper.complete_event(r) for r in raw], calls


def by_title(events, start):
    return [e for e in events if e["title"].startswith(start)]


class ListingTest(unittest.TestCase):
    def test_reads_every_dated_event_of_the_listing(self):
        items = lt.read_listing(page("liste"), LISTING_URL)
        self.assertEqual(len(items), 7)  # the eighth card has no date
        blue = next(i for i in items if i["title"].startswith("Blue Magic"))
        self.assertEqual((blue["start"], blue["end"]), (date(2026, 10, 15), date(2026, 10, 15)))
        self.assertEqual(blue["location"], "Folklor Club")
        self.assertEqual(blue["url"], LISTING_URL + "blue-magic-zombidou-leo-blackout/")
        self.assertTrue(blue["image"].startswith("https://static.lausanne-tourisme.ch/"))
        self.assertTrue(blue["description"].endswith("…"))

    def test_the_site_is_routed_to_this_reader(self):
        self.assertIs(reader_for(LISTING_URL), lt)
        self.assertIsNone(reader_for("https://mad.ch/agenda/"))


class EventPagesTest(unittest.TestCase):
    def setUp(self):
        lt._cache.clear()

    def test_weekly_karaoke_appears_on_its_tuesdays_only(self):
        events, _ = collect()
        karaoke = by_title(events, "🎤 MARDI")
        self.assertEqual([e["date"] for e in karaoke], ["2026-10-13", "2026-10-20", "2026-10-27"])
        self.assertEqual({e["time"] for e in karaoke}, {"19:00"})
        self.assertEqual(karaoke[0]["price"], "Gratuit")
        self.assertEqual(karaoke[0]["address"], "Rue de Genève 17, 1003 Lausanne")
        self.assertEqual(karaoke[0]["category"], "Clubbing")  # a bar night
        self.assertEqual(len({e["id"] for e in karaoke}), 3)

    def test_a_night_past_midnight_is_one_event(self):
        events, _ = collect()
        [blue] = by_title(events, "Blue Magic")
        self.assertEqual((blue["date"], blue["time"], blue["end_date"]), ("2026-10-15", "23:55", ""))
        self.assertEqual(blue["price"], "Dès 5 CHF")
        self.assertEqual(blue["category"], "Clubbing")
        self.assertNotIn("Source", blue["description"])

    def test_exhibition_open_every_day_is_one_card_without_time(self):
        events, _ = collect()
        [expo] = by_title(events, "Edouard Chapallaz")
        self.assertEqual((expo["date"], expo["end_date"], expo["time"]), ("2026-09-25", "2027-01-31", ""))
        self.assertEqual(expo["category"], "Exposition")

    def test_event_listed_date_by_date_keeps_the_next_two_weeks(self):
        events, _ = collect()
        self.assertEqual([e["date"] for e in by_title(events, "Water Pong")], ["2026-10-19", "2026-10-26"])

    def test_long_period_without_its_page_is_held_back(self):
        events, _ = collect(missing={"water-pong"})
        self.assertEqual(by_title(events, "Water Pong"), [])
        # Its page was never saved either: unknown days, not shown every evening.
        self.assertEqual(by_title(events, "Soirée entre copains"), [])

    def test_short_or_later_periods_keep_the_listing_dates(self):
        events, calls = collect()
        [luff] = by_title(events, "Lausanne Underground")
        self.assertEqual((luff["date"], luff["end_date"]), ("2026-10-14", "2026-10-18"))
        [baby] = by_title(events, "Baby Teeth")
        self.assertEqual((baby["date"], baby["end_date"]), ("2026-11-18", "2026-11-19"))
        self.assertNotIn(LISTING_URL + "baby-teeth-catol-teixeira/", calls)  # next month: page not read yet

    def test_pages_are_read_once_and_within_the_limit(self):
        fetch, calls = fake_site()
        lt.read(page("liste"), LISTING_URL, fetch, TODAY, pause=0)
        lt.read(page("liste"), LISTING_URL, fetch, TODAY, pause=0)
        # A page read once is remembered; a missing one is tried again next time.
        read_twice = {url for url in calls if calls.count(url) > 1}
        self.assertEqual({url.rstrip("/").rsplit("/", 1)[-1] for url in read_twice},
                         {"soiree-entre-copains-karaocook-quizz", "lausanne-underground-film-music-festival"})
        lt._cache.clear()
        fetch, calls = fake_site()
        lt.read(page("liste"), LISTING_URL, fetch, TODAY, max_pages=2, pause=0)
        self.assertEqual(len(calls), 2)


class OccurrencesTest(unittest.TestCase):
    def test_sunday_evening_until_one_in_the_morning(self):
        openings = [{"day": 0, "from": "1700", "until": "2359"}, {"day": 1, "from": "0000", "until": "0100"}]
        found = lt.occurrences(date(2026, 10, 12), date(2026, 10, 26), openings)
        self.assertEqual(found, [(date(2026, 10, 18), None, "17:00"), (date(2026, 10, 25), None, "17:00")])

    def test_two_evenings_run(self):
        openings = [{"day": 3, "from": "1930", "until": ""}, {"day": 4, "from": "1930", "until": ""}]
        found = lt.occurrences(date(2026, 11, 18), date(2026, 11, 19), openings)
        self.assertEqual([(d.day, t) for d, _, t in found], [(18, "19:30"), (19, "19:30")])

    def test_festival_without_hours_is_one_period(self):
        self.assertEqual(lt.occurrences(date(2026, 10, 14), date(2026, 10, 18), []),
                         [(date(2026, 10, 14), date(2026, 10, 18), "")])


if __name__ == "__main__":
    unittest.main()
