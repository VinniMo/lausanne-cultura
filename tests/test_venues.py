"""Venue readers (D! Club, MAD, Théâtre de Beaulieu) and French dates,
tested on pages cut from the real sites on 13 October 2026 ("today").

Run with: python -m unittest discover tests
"""
import os
import unittest
from datetime import date

import scraper
from sources import beaulieu, dclub, mad, reader_for
from sources.common import french_dates

HERE = os.path.join(os.path.dirname(__file__), "fixtures", "lieux")
TODAY = date(2026, 10, 13)


def read(reader, name, url):
    with open(os.path.join(HERE, f"{name}.html"), encoding="utf-8") as fh:
        return [scraper.complete_event(r) for r in reader.read(fh.read(), url, None, TODAY)]


class FrenchDatesTest(unittest.TestCase):
    def test_formats_seen_on_the_sites(self):
        self.assertEqual(french_dates("jeudi 15 octobre 2026"), [date(2026, 10, 15)])
        self.assertEqual(french_dates("28–29 octobre 2026"), [date(2026, 10, 28), date(2026, 10, 29)])
        self.assertEqual(french_dates("31 octobre – 1 novembre 2026"), [date(2026, 10, 31), date(2026, 11, 1)])
        self.assertEqual(french_dates("30 décembre – 2 janvier 2027"), [date(2026, 12, 30), date(2027, 1, 2)])
        self.assertEqual(french_dates("1er mars 2027"), [date(2027, 3, 1)])

    def test_no_date_without_month_and_year(self):
        self.assertEqual(french_dates("Porte: 23:00"), [])
        self.assertEqual(french_dates("16 octobre"), [])


class DClubTest(unittest.TestCase):
    def setUp(self):
        self.events = read(dclub, "dclub", "https://dclub.ch/agenda/")

    def test_nights_with_room_door_time_and_line_up(self):
        first = self.events[0]
        self.assertEqual((first["date"], first["time"]), ("2026-10-13", "23:00"))
        self.assertEqual(first["title"], "COACHING EPFL · DJ Kemuel")
        self.assertEqual(first["location"], "D! Club")
        self.assertEqual(first["category"], "Clubbing")
        self.assertTrue(first["image"].startswith("https://dclub.ch/wp-content/"))

    def test_the_abc_bar_and_shared_pages_stay_apart(self):
        rooms = {(e["date"], e["location"]) for e in self.events}
        self.assertIn(("2026-10-15", "Bar Club ABC"), rooms)
        self.assertEqual(len({e["id"] for e in self.events}), len(self.events))
        magic = next(e for e in self.events if e["title"].startswith("Marco Smacchia"))
        self.assertEqual(magic["time"], "15:30")


class MadTest(unittest.TestCase):
    def setUp(self):
        self.events = read(mad, "mad", "https://mad.ch/agenda/")

    def test_past_nights_are_skipped_and_floors_named(self):
        self.assertEqual([e["date"] for e in self.events],
                         ["2026-10-15", "2026-10-16", "2026-10-16", "2026-10-18"])
        self.assertEqual({e["location"] for e in self.events}, {"MAD – Mainfloor", "MAD – Jetlag"})

    def test_free_entry_written_in_the_line_up(self):
        gameboy = self.events[-1]
        self.assertEqual(gameboy["title"], "Gameboy the mad gay party")
        self.assertEqual(gameboy["price"], "Entrée libre")
        self.assertEqual(len({e["id"] for e in self.events}), 4)


class BeaulieuTest(unittest.TestCase):
    def test_single_dates_and_short_runs(self):
        events = read(beaulieu, "beaulieu", "https://beaulieu-lausanne.com/agenda/?cat=theatre")
        self.assertEqual([(e["date"], e["end_date"]) for e in events],
                         [("2026-10-16", ""), ("2026-10-28", "2026-10-29"), ("2026-10-31", "2026-11-01")])
        self.assertEqual(events[0]["title"], "Stephan Eicher « Poussière d’Or »")
        self.assertEqual(events[0]["location"], "Théâtre de Beaulieu")
        self.assertTrue(events[0]["url"].startswith("https://beaulieu-lausanne.com/agenda/"))

    def test_routing(self):
        self.assertIs(reader_for("https://beaulieu-lausanne.com/agenda/?cat=theatre"), beaulieu)
        self.assertIs(reader_for("https://dclub.ch/agenda/"), dclub)
        self.assertIs(reader_for("https://www.mad.club/agenda/"), mad)


if __name__ == "__main__":
    unittest.main()
