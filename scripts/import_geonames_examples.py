#!/usr/bin/env python3
"""Create the common example data from official GeoNames dump files."""
import argparse
import io
from pathlib import Path
import sqlite3
from zipfile import ZipFile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cities_archive', type=Path)
    parser.add_argument('country_info', type=Path)
    parser.add_argument('examples_directory', type=Path)
    args = parser.parse_args()

    countries = {}
    for line in args.country_info.read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            iso2, iso3, _, _, name, *_ = line.split('\t')
            countries[iso2] = (iso3, name.strip())

    eu = set("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split())
    cities = []
    with ZipFile(args.cities_archive) as archive:
        with io.TextIOWrapper(archive.open('cities15000.txt'), encoding='utf-8') as stream:
            for line in stream:
                fields = line.rstrip('\r\n').split('\t')
                if len(fields) != 19:
                    raise ValueError('Invalid GeoNames record')
                iso2 = fields[8]
                if iso2 not in eu or iso2 not in countries:
                    continue
                iso3, country = countries[iso2]
                capital = {'PPLC': 'primary', 'PPLA': 'admin'}.get(fields[7], '')
                cities.append((int(fields[0]), fields[1], fields[2], float(fields[4]),
                               float(fields[5]), country, iso2, iso3, fields[10],
                               capital, int(fields[14])))

    output = args.examples_directory
    database = output / 'eu-cities/data/eu-cities-sqlite.db'
    country_file = output / 'countries/data/countries.txt'
    database.parent.mkdir(parents=True, exist_ok=True)
    country_file.parent.mkdir(parents=True, exist_ok=True)
    # Create a fresh snapshot instead of modifying existing example data.
    with database.open('xb'):
        pass
    with sqlite3.connect(database) as connection:
        connection.executescript('''
            CREATE TABLE cities_new (
                city_id INTEGER PRIMARY KEY, city TEXT NOT NULL, city_ascii TEXT NOT NULL,
                latitude REAL NOT NULL, longitude REAL NOT NULL, country_name TEXT NOT NULL,
                iso2 TEXT NOT NULL, iso3 TEXT NOT NULL, admin_name TEXT NOT NULL,
                capital TEXT NOT NULL, population INTEGER NOT NULL
            );
            CREATE INDEX cities_new_iso2_city_idx ON cities_new (iso2, city);
        ''')
        connection.executemany('INSERT INTO cities_new VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', cities)
    with country_file.open('x', encoding='utf-8') as stream:
        for code, (_, name) in sorted(countries.items()):
            stream.write(f'{code}:{name}\n')
    print(f'{len(cities)} cities, {sum(row[6] == "GR" for row in cities)} Greek cities, '
          f'{len(countries)} country records')


if __name__ == '__main__':
    main()
