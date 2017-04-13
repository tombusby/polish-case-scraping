# -*- coding: utf-8 -*-
import scrapy, urlparse
from scrapy.http.request import Request


class WiktionarySpider(scrapy.Spider):
    name = "wiktionary"
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
        print "\tPROCESSING:", response.url
