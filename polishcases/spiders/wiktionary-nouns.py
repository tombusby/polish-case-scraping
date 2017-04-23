# -*- coding: utf-8 -*-
import scrapy, urlparse
from scrapy.http.request import Request


class WiktionaryNounSpider(scrapy.Spider):
    name = "wiktionary-noun"
    allowed_domains = ["en.wiktionary.org"]
    start_urls = ['https://en.wiktionary.org/wiki/Category:Polish_nouns']

    def parse(self, response):
        # Get the domain name and the protocol from the response URL
        reponse_url_components = urlparse.urlparse(response.url)
        base_url = "{}://{}".format(reponse_url_components.scheme, reponse_url_components.netloc)
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
        case_forms = self._get_case_forms(response)
        return {
            'word': word,
            'gender': gender,
            'url': response.url,
            'case_forms': case_forms
        }

    def _get_case_forms(self, response):
        forms = {}
        declension_table = response.xpath('.//h2[./span[@id="Polish"]]/following::div[contains(@class, "inflection-table-noun")][1]//table')
        headers = declension_table.xpath('.//tr[1]/th[string-length(text()) > 0]/text()').extract()
        for row in declension_table.xpath('.//tr[position()>1]'):
            case_name = row.css('th::text').extract()[0]
            case_forms = row.xpath('.//td//text()').extract()
            for number, case_form in zip(headers, case_forms):
                if number not in forms:
                    forms[number] = {}
                forms[number][case_name] = case_form
        return forms
