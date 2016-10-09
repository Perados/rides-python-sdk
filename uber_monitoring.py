#!/usr/bin/env python

import csv
import pytz
import datetime
import pandas as pd

from example.utils import import_oauth2_credentials
from uber_rides.session import Session, OAuth2Credential
from uber_rides.client import UberRidesClient

from geopy.geocoders import Nominatim
geolocator = Nominatim()

CONVERSION_FACTOR = 1.60934

ADDRESS_COMBINATIONS = (
    ('home', 'office'),
    ('home', 'charles_de_gaulle_airport'),
    ('eiffel_tower', 'gare_du_nord'),
    ('la_defense', 'montparnasse_tower')
)

TZ = pytz.timezone('Europe/Paris')

ADRESSES_DICT = {
    'home': '83, avenue de Ségur, 75015 Paris',
    'office': '43 Quai du Président Roosevelt, 92130 Issy-les-Moulineaux',
    'charles_de_gaulle_airport': '95700 Roissy-en-France',
    'eiffel_tower': '5 Avenue Anatole France, 75007 Paris',
    'gare_du_nord': '18 Rue de Dunkerque, 75010 Paris',
    'la_defense': '2 Place de la Défense, 92800 Puteaux',
    'montparnasse_tower': '33 Avenue du Maine, 75015 Paris',
}
ADDRESS_LOCATION_DICT = {key: geolocator.geocode(value) for (key, value) in ADRESSES_DICT.items()}


def authenticate():
    credentials = import_oauth2_credentials()
    oauth2_credential = OAuth2Credential(**credentials)
    new_session = Session(oauth2credential=oauth2_credential)
    new_client = UberRidesClient(new_session)
    return new_client


def get_product_id(client):
    response = client.get_products(
        ADDRESS_LOCATION_DICT['home'].latitude,
        ADDRESS_LOCATION_DICT['home'].longitude
    )
    products = response.json.get('products')

    for product in products:
        if product['display_name'] == 'uberX':
            product_id = product['product_id']
            return product_id


def write_combinations_to_csv(client, product_id, address_combinations):
    with open('uber_monitoring.csv', 'a') as f:
        for combination in address_combinations:
            writer = csv.writer(f)

            from_place = combination[0]
            from_latitude = ADDRESS_LOCATION_DICT[from_place].latitude
            from_longitude = ADDRESS_LOCATION_DICT[from_place].longitude
            to_place = combination[1]
            to_latitude = ADDRESS_LOCATION_DICT[to_place].latitude
            to_longitude = ADDRESS_LOCATION_DICT[to_place].longitude

            now = TZ.localize(datetime.datetime.now())
            print("Gonna make call to Uber's api at {}.".format(now.isoformat()))
            estimated_ride = client.estimate_ride(
                product_id=product_id,
                start_latitude=from_latitude,
                start_longitude=from_longitude,
                end_latitude=to_latitude,
                end_longitude=to_longitude,
            ).json

            row = [
                now,
                from_place,
                from_latitude,
                from_longitude,
                to_place,
                to_latitude,
                to_longitude,
                estimated_ride['trip']['distance_estimate'] * CONVERSION_FACTOR if estimated_ride['trip']['distance_unit'] == 'mile' else estimated_ride['trip']['distance_estimate'],
                estimated_ride['trip']['duration_estimate'],
                estimated_ride['price']['surge_multiplier'],
                estimated_ride['price']['low_estimate'],
                estimated_ride['price']['high_estimate'],
            ]

            writer.writerow(row)
            print("Wrote line into csv successfully.")


def generate_filtered_csvs(address_combinations):
    df = pd.read_csv('uber_monitoring.csv')
    for combination in address_combinations:
        from_place = combination[0]
        to_place = combination[0]
        filtered_df = df[(df['from_place'] == from_place) & (df['to_place'] == to_place)]
        ax = filtered_df.plot(x='time', y=['low_price', 'high_price'], figsize=(20, 10), rot=90)
        ax.set_ylim(0, 30)


def main():
    client = authenticate()
    product_id = get_product_id(client)
    write_combinations_to_csv(client, product_id, ADDRESS_COMBINATIONS)


if __name__ == '__main__':
    main()
