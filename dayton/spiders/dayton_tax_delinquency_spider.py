import csv
import glob
import urllib.request

import scrapy
from scrapy.selector import Selector

from dayton.spiders.reap_spider import unzip


class DelinquencySpider(scrapy.Spider):
    """This class is used to parse the delinquency tax information CSV files from the
    Montgomery County Treasurers Website and output any properties that have larger
    net delinquent taxes than the value of the property and building.

    The field descriptions from the file can be found here:
    www.mctreas.org/mctreas/data/delq%20file%20layout.pdf
    """

    DAYTON_DELINQUENT_PROPERTIES_OUTFILE = "delinquent_tax_processed.csv"
    name = 'dayton_tax_delinquency'
    allowed_domains = ['mctreas.org', 'mcohio.org']
    start_urls = [
        'http://www.mctreas.org/mctreas/fdpopup.cfm?dtype=DQ'
    ]

    def parse(self, response, **kwargs) -> None:
        """
        Parses the delinquency file given. Writes the matching records to the output
        file specified.

        Args:
            response: The HTTP response object from the crawled website.

        Returns:
            None

        Raises:
            ValueError if the necessary columns can't be found in the delinquency_file header
        """
        delinquent_link = Selector(response).xpath(
            '//*[@id="box1"]/td[1]/li/font/i/a/@href').extract()
        urllib.request.urlretrieve(response.urljoin(delinquent_link[0]),
                                   'delinquent.zip')
        unzip('delinquent.zip', 'delinquent')

        with open(self.DAYTON_DELINQUENT_PROPERTIES_OUTFILE, mode="w") as out_file:
            with open(glob.glob('delinquent/*.csv')[0], newline='') as delinquent_file:
                header = delinquent_file.readline()
                out_file.write(header)

                delinquent_file_reader = csv.reader(delinquent_file)
                out_file_writer = csv.writer(out_file)
                value_index = None
                owed_index = None
                tax_district_index = None
                for idx, val in enumerate(header.split(",")):
                    if val.strip(' "') == "ASMTTOTAL":
                        value_index = idx
                    elif val.strip(' "') == "NETDELQ":
                        owed_index = idx
                    elif val.strip(' "') == "TXDST":
                        tax_district_index = idx

                if not all([value_index, owed_index, tax_district_index]):
                    raise ValueError(
                        f"One of the indexes wasn't set: "
                        f"{value_index=} {owed_index=} {tax_district_index=}")

                for row in delinquent_file_reader:
                    if len(row) < len(header.split(",")):
                        continue
                    home_value: str = row[value_index].strip(' "')
                    tax_owed: str = row[owed_index].strip(' "')
                    tax_district: str = row[tax_district_index].strip(' "')
                    if not home_value or not tax_owed:
                        continue
                    home_value: float = float(home_value)
                    tax_owed: float = float(tax_owed)
                    is_in_dayton = bool(tax_district) and tax_district == "R72"
                    if home_value and tax_owed and tax_owed > home_value and is_in_dayton:
                        out_file_writer.writerow(row)


