# VERSION: 1.2
#
# LICENSING INFORMATION
# This is free and unencumbered software released into the public domain.
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
# For more information, please refer to <https://unlicense.org>

import math
import re
import time
from datetime import datetime, timedelta
from unicodedata import normalize

from helpers import retrieve_url
from novaprinter import prettyPrinter


class btdig(object):
    url = "https://btdig.com"
    name = "btdig"
    supported_categories = {"all": "all"}

    class DateParser:
        def __init__(self):
            now = datetime.now()
            self.date_parsers = {
                r"(\d+)\s+seconds?": lambda m: now - timedelta(seconds=int(m[1])),
                r"(\d+)\s+minutes?": lambda m: now - timedelta(minutes=int(m[1])),
                r"(\d+)\s+hours?": lambda m: now - timedelta(hours=int(m[1])),
                r"(\d+)\s+days?": lambda m: now - timedelta(days=int(m[1])),
                r"(\d+)\s+weeks?": lambda m: now - timedelta(days=int(m[1]) * 7),
                r"(\d+)\s+months?": lambda m: now - timedelta(days=int(m[1]) * 30),
                r"(\d+)\s+years?": lambda m: now - timedelta(days=int(m[1]) * 365),
            }

        def parse(self, data):
            timestamp = -1
            for pattern, calc in self.date_parsers.items():
                m = re.search(pattern, data, re.IGNORECASE)
                if m:
                    timestamp = int(calc(m).timestamp())
                    break
            return timestamp

    def search(self, what, cat="all"):
        url = f"{self.url}/search?q={what.replace(' ', '+')}&order=0"
        html = retrieve_url(url)

        results_match = re.search(
            r'<span style="color:rgb\(100, 100, 100\);padding:2px 10px">(\d+) results found',
            html,
        )
        if results_match:
            total_results = int(results_match.group(1))
            total_pages = math.ceil(total_results / 10)
        else:
            total_pages = 1  # assuming single page

        self.parse_page(html)

        for page in range(1, total_pages):
            time.sleep(1)  # sleep for 1 second between requests
            url = f"{self.url}/search?q={what.replace(' ', '+')}&p={page}&order=0"
            html = retrieve_url(url)
            self.parse_page(html)

    def parse_page(self, html_content):
        result_blocks = re.finditer(
            r'<div class="one_result".*?(?=<div class="one_result"|$)',
            html_content,
            re.DOTALL,
        )

        age_parser = self.DateParser()
        for block in result_blocks:
            block_content = block.group(0)

            magnet_match = re.search(
                r'<a href="(magnet:\?xt=urn:btih:[^"]+)"', block_content
            )
            name_match = re.search(
                r'<div class="torrent_name".*?><a.*?>(.*?)<\/a>',
                block_content,
                re.DOTALL,
            )
            size_match = re.search(
                r'<span class="torrent_size"[^>]*>(.*?)<\/span>', block_content
            )
            desc_link_match = re.search(
                r'<a.*? href="https:\/\/(?:www\.)?btdig\.com([^"]+)"', block_content
            )
            age_match = re.search(
                r'<span class="torrent_age"[^>]*>(.*?)<\/span>', block_content
            )

            if (
                magnet_match
                and name_match
                and size_match
                and desc_link_match
                and age_match
            ):
                result = {
                    "link": magnet_match.group(1),
                    "name": re.sub(r"<.*?>", "", name_match.group(1)).strip(),
                    "size": normalize("NFKD", size_match.group(1)),   # replace \xa0 with space
                    "engine_url": self.url,
                    "desc_link": self.url + desc_link_match.group(1),
                    "pub_date": age_parser.parse(age_match.group(1)),
                    "seeds": "-1",
                    "leech": "-1",
                }
                prettyPrinter(result)
