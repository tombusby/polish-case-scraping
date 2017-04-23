# -*- coding: utf-8 -*-
import scrapy, urlparse, re, itertools
from scrapy.http.request import Request


class DeclensionTable(object):

    column_headers = []
    case_names = []
    table_data = None

    def __init__(self, table_node):
        self._process_column_headers(table_node)
        self._process_html_table_rows(table_node)

    def _clean_cell_text(self, cell):
        string = ''.join(cell.xpath('.//text()').extract())
        return ' '.join(string.split())

    def _extract_cell_text_and_expand_by_colspan(self, nodes):
        items = []
        for node in nodes:
            multiplier = node.xpath('.//@colspan').extract()
            multiplier = int(multiplier.pop()) if multiplier else 1
            cell_text = self._clean_cell_text(node)
            items += [cell_text] * multiplier
        return items

    def _process_column_headers(self, table_node):
        singular_or_plural = self._extract_cell_text_and_expand_by_colspan(table_node.xpath('.//tr[1]/th[position()>1]'))
        gender_headers = self._extract_cell_text_and_expand_by_colspan(table_node.xpath('.//tr[2]/th'))
        self.column_headers = zip(singular_or_plural, gender_headers)

    def _process_html_table_rows(self, table_node):
        def get_span_attr(cell, attr_name):
            span = cell.xpath('.//@{}'.format(attr_name)).extract()
            return int(span.pop()) if span else 1
        rows = table_node.xpath('.//tr[position()>2]')
        self.table_data = [[None] * len(rows) for _ in self.column_headers]
        x = y = 0
        for row in rows:
            self.case_names += row.xpath('./th[1]//text()').extract()
            for cell in row.xpath('./td'):
                while self.table_data[x][y] is not None:
                    x += 1
                colspan = get_span_attr(cell, 'colspan')
                rowspan = get_span_attr(cell, 'rowspan')
                cell_text = self._clean_cell_text(cell)
                for i, j in itertools.product(range(colspan), range(rowspan)):
                    self.table_data[x+i][y+j] = cell_text
                x += colspan
            x = 0
            y += 1
        self._expand_comma_separated()

    def _expand_comma_separated(self):
        new_column_headers = []
        new_table_data = []
        for (number, gender), row in zip(self.column_headers, self.table_data):
            new_case_names = []
            new_row = []
            for case, form in zip(self.case_names, row):
                for split_case in re.split("\s*,\s*", case):
                    new_case_names.append(split_case)
                    new_row.append(form)
            for split_gender in re.split("\s*,\s*", gender):
                new_column_headers.append((number, split_gender))
                new_table_data.append(new_row)
        self.case_names = new_case_names
        self.column_headers = new_column_headers
        self.table_data = new_table_data

    def export_dict(self):
        def ensure_dict_initialised(tree, field_list):
            current_node = tree
            for field in field_list:
                if field not in current_node.keys():
                    current_node[field] = {}
                current_node = current_node[field]
        output = {}
        for (number, gender), row in zip(self.column_headers, self.table_data):
            for case, form in zip(self.case_names, row):
               ensure_dict_initialised(output, [number, gender, case])
               output[number][gender][case] = form
        return output

class WiktionaryAdjectiveSpider(scrapy.Spider):
    name = 'wiktionary-adjective'
    allowed_domains = ['en.wiktionary.org']
    start_urls = ['https://en.wiktionary.org/wiki/Category:Polish_adjectives']

    def parse(self, response):
        # Get the domain name and the protocol from the response URL
        reponse_url_components = urlparse.urlparse(response.url)
        base_url = '{}://{}'.format(reponse_url_components.scheme, reponse_url_components.netloc)
        # Crawl the words on the page
        for url in response.css("#mw-pages li a::attr(href)").extract():
            yield Request(urlparse.urljoin(base_url, url), callback=self.parse_word)
        # Crawl the next page
        try:
            next_page = response.css('#mw-pages a[href*=pagefrom]::attr(href)').extract()[0]
            yield Request(urlparse.urljoin(base_url, next_page), callback=self.parse)
        except IndexError:
            pass

    def parse_word(self, response):
        word_details = response.xpath('.//h2[./span[@id="Polish"]]/following::p[./strong[contains(@class, "headword")]][1]')
        word = word_details.xpath('./strong[contains(@class, "headword")]/text()').extract()[0]
        gender = "".join(word_details.xpath('./span[contains(@class, "gender")]//text()').extract())
        declension_table = response.xpath('.//h2[./span[@id="Polish"]]/following::div[contains(@class, "inflection-table-adj")][1]//table')
        case_forms = DeclensionTable(declension_table).export_dict() if declension_table else {}
        return {
            'word': word,
            'gender': gender,
            'url': response.url,
            'case_forms': case_forms
        }
