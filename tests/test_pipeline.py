import unittest
from pipeline import build_rows, host, valid_name

class PipelineTests(unittest.TestCase):
    def test_site_home_canonicalization(self):
        self.assertEqual(host('https://www.abos-immobilien.de/kontakt/'), 'abos-immobilien.de')

    def test_bad_title(self):
        self.assertFalse(valid_name('Kontakt'))
        self.assertFalse(valid_name('Startseite'))
        self.assertTrue(valid_name('ABOS Immobilien GmbH'))

    def test_directory_merge_and_classification(self):
        scraped = [
            {'name':'Kontakt', 'website':'https://www.abos-immobilien.de/kontakt/',
             'page_text':'WEG-Verwaltung in Berlin. Heizkostenabrechnung',
             'scrape_status':'OK', 'source_pages':['https://www.abos-immobilien.de/kontakt/']},
            {'name':'Hausverwaltungen Berlin 2026',
             'website':'https://www.dastelefonbuch.de/Branchen/Hausverwaltung/Berlin',
             'scrape_status':'OK', 'page_text':'Hausverwaltung Berlin'}
        ]
        directory = [{
            'company_name':'ABOS Immobilien GmbH', 'website':'https://www.abos-immobilien.de',
            'city':'Berlin (annuaire)', 'email':'info@abos-immobilien.de',
            'source_url':'https://vdiv-bb.de/mitglieder/'
        }]
        rows = build_rows(scraped,directory)
        self.assertEqual(len(rows),2)
        abos = next(r for r in rows if r['domain']=='abos-immobilien.de')
        self.assertEqual(abos['company_name'],'ABOS Immobilien GmbH')
        self.assertEqual(abos['classification'],'LIKELY')
        self.assertTrue(abos['score_max']>=abos['score_min'])
        self.assertIsNone(abos['units_managed'])
        directory_listing = next(r for r in rows if r['domain']=='dastelefonbuch.de')
        self.assertEqual(directory_listing['classification'],'EXCLUDED')

    def test_unknown_units_not_zero(self):
        r = build_rows([{'name':'Müller Hausverwaltung GmbH',
              'website':'https://mueller-example.de/', 'scrape_status':'OK',
              'page_text':'Wir bieten Mietverwaltung in Berlin'}],[])[0]
        self.assertIsNone(r['units_managed'])
        self.assertGreater(r['score_max'],r['score_min'])

if __name__=='__main__': unittest.main()

class ListingTests(unittest.TestCase):
    def test_comparison_article_not_company(self):
        row = build_rows([{"name":"Top 7 Hausverwaltungen in Berlin 2026",
            "website":"https://immodo-berlin.de/blog/beste-hausverwaltungen-berlin/",
            "scrape_status":"OK", "page_text":"Top 7 Hausverwaltungen in Berlin, WEG Verwaltung"}],[])[0]
        self.assertEqual(row["classification"], "EXCLUDED")
