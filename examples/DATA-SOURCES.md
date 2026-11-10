# Example data sources

The Countries and EU Cities data are adapted from [GeoNames](https://www.geonames.org/)
under [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/).
The source files were downloaded on 9 November 2026. The [GeoNames dump documentation](https://download.geonames.org/export/dump/readme.txt)
describes the fields and license.

| Original file | SHA256 |
| --- | --- |
| [cities15000.zip](https://download.geonames.org/export/dump/cities15000.zip) | `955ad298b67a60996a15b4c4c84c8ca6923bafed195622227f24fd22a31042f4` |
| [countryInfo.txt](https://download.geonames.org/export/dump/countryInfo.txt) | `79f8f59ea01cbb40438bf1856dd6c2ff201f03f8fc72d0530b2646aaf603ef04` |

The Countries example keeps the two-letter code and country name in
`CODE:Name` format. The SQLite example selects the city ID, names, coordinates,
country, administrative code and population. It joins country names and ISO3
codes from the country file, maps capital feature codes, and keeps 5,398 rows
from the 27 EU member states. The debugger software uses a separate 0BSD license.

To reproduce the data from these archives, run the following from the debugger
repository with a fresh destination directory:

```bash
python3 scripts/import_geonames_examples.py cities15000.zip countryInfo.txt /path/to/new-examples
```

Membership follows the [official EU country list](https://european-union.europa.eu/principles-countries-history/eu-countries_en).
