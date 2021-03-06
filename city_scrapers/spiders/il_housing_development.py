from city_scrapers_core.constants import BOARD
from city_scrapers_core.items import Meeting
from city_scrapers_core.spiders import CityScrapersSpider
from io import BytesIO, StringIO
import re
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from dateutil.parser import parse


class IlHousingDevelopmentSpider(CityScrapersSpider):
    name = "il_housing_development"
    agency = "Illinois Housing Development Authority"
    timezone = "America/Chicago"
    start_urls = ["https://www.ihda.org/about-ihda/public-meetings-and-notices/"]
    location = {
        "name": "Cape Cod Conference Room",
        "address": "111 E. Wacker, 11th floor boardroom, Chicago, IL 60601",
    }

    def __init__(self, *args, **kwargs):
        self.minutes_map = dict()  # Populated by self._parse_minutes()
        self.agenda_map = dict()  # Populated by self._parse_agenda()

    def parse(self, response):
        """
        `parse` should always `yield` Meeting items

        Change the `_parse_title`, `_parse_start`, etc methods to fit your scraping
        needs.
        """
        for link in response.xpath('//a[contains(text(), "Minutes")]'):
            yield response.follow(link.attrib["href"], callback=self._parse_minutes)

        for link in response.xpath('//a[contains(text(), "Meeting Dates")]'):
            yield response.follow(
                link.attrib["href"], callback=self._parse_pdf_schedule
            )
            break

    def _parse_pdf_schedule(self, response):
        """
        The table format of the meeting PDF makes it difficult to get the name/time of the
        meeting along with the its associated dates. Instead we'll parse them separately, and then
        pair them back together.
        """
        lp = LAParams(line_margin=0.1)
        out_str = StringIO()
        extract_text_to_fp(BytesIO(response.body), out_str, laparams=lp)
        pdf_text = out_str.getvalue()
        dates = re.findall(r'[A-Z][a-z]{1,8} \d{1,2}(?:th|rd|st)', pdf_text)
        names_and_times = re.findall(
            r'([A-Z\s]*)(\(\d{1,2}:00[ ]?[a|p][\.]?m[\.]?\))', pdf_text
        )
        # Clean up names and times
        names_and_times = iter(
            (name.strip().replace("\n", ""), time.replace("(", "").replace(")", ""))
            for name, time in names_and_times
        )

        meetings = []
        meeting = next(names_and_times)
        previous_date = None

        for date in dates:
            if previous_date is not None and parse(date) < parse(previous_date):
                meeting = next(names_and_times)
            meetings.append(
                {"title": meeting[0], "start": parse(f"{date} {meeting[1]}")}
            )
            previous_date = date

        for item in meetings:
            meeting = Meeting(
                title=item["title"],
                description=self._parse_description(item),
                classification=BOARD,
                start=item["start"],
                end=None,
                all_day=False,
                time_notes=self._parse_time_notes(item),
                location=self.location,
                links=self._parse_links(item),
                source=self._parse_source(response),
            )

            meeting["status"] = self._get_status(meeting)
            meeting["id"] = self._get_id(meeting)

            yield meeting

    def _parse_minutes(self, response):
        print(response)

    def _parse_description(self, item):
        """Parse or generate meeting description."""
        return ""

    def _parse_time_notes(self, item):
        """Parse any additional notes on the timing of the meeting"""
        return ""

    def _parse_links(self, item):
        """Parse or generate links."""
        return [{"href": "", "title": ""}]

    def _parse_source(self, response):
        """Parse or generate source."""
        return response.url
