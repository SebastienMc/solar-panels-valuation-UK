import datetime
import math
import numpy as np
import pandas as pd
import pickle as pk
import sys

# Want an accurate NPV valutation for your solar panels? Visit:

# www.greenassist.co.uk

# User command line inputs:
# sys.argv[0] - "solar_npv_estimator.py"
# sys.argv[1] - date in format "YYYY-MM-DD" - representative of commissioning date.
# sys.argv[2] - integer in the range 0 to 1 - representative of capacity input type:
#       0 - Actual capacity in kWp; and
#       1 - Number of panels (assumption per panel = 250Wp).
# sys.argv[3] - float - representative of capacity.
# sys.argv[4] - integer in the range 0 to 12 (inclusive) - representative of location:
#       0 - East of England;
#       1 - East Midlands;
#       2 - Greater London;
#       3 - North East;
#       4 - North West;
#       5 - Northern Ireland;
#       6 - Scottish Highlands and Isles;
#       7 - Scotland excl. Highlands and Isles;
#       8 - South East;
#       9 - South West;
#       10 - Wales;
#       11 - West Midlands; and
#       12 - Yorkshire and the Humber.
# sys.argv[5] - integer in the range 0 to 1 - representative of ownership structure:
#       0 - Self owned; and
#       1 - Investor owned.
# Script outputs:
# NPV to the homeowner | full NPV if investor owned - output formatted as a string of length 11. examples below:
#           args: 2018-06-09 0 3 1 0        out:    08000|00000
#           args: 2018-06-09 0 3 1 1        out:    05000|08000


def identify_fit(com_date, size):
    """Identifies FIT rate from adjoined tables."""
    if com_date >= datetime.date(2012, 4, 1):
        rates = pk.load(open('fits_recent', 'rb'))['Higher']
    else:
        rates = pk.load(open('fits_retrofit', 'rb'))
    column_number = sum([x < size for x in rates.columns])
    if com_date >= datetime.date(2012, 4, 1):
        fit = float(rates[datetime.datetime.strftime(com_date, '%Y-%m')][rates.columns[column_number]])
    else:
        row_number = sum([x <= pd.to_datetime(com_date) for x in rates.index]) - 1
        fit = float(rates.iloc[row_number, column_number])
    return fit / 100


def identify_profile(integer):
    """Returns array of monthly generation figures. Integer represents region, see comments above."""
    pvgis = {0: [28.0, 43.6, 81.5, 106.0, 117.0, 114.0, 118.0, 105.0, 84.5, 56.8, 33.3, 28.4],
             1: [28.9, 45.5, 81.4, 105.0, 118.0, 115.0, 117.0, 106.0, 85.5, 57.8, 35.7, 29.4],
             2: [31.5, 45.8, 86.1, 115.0, 123.0, 124.0, 129.0, 109.0, 89.7, 60.6, 35.3, 28.0],
             3: [25.0, 43.5, 80.3, 108.0, 125.0, 113.0, 113.0, 98.8, 82.3, 55.8, 28.7, 19.6],
             4: [24.9, 42.2, 80.7, 111.0, 126.0, 126.0, 121.0, 107.0, 80.8, 51.5, 29.9, 22.4],
             5: [24.8, 39.8, 74.4, 107.0, 121.0, 114.0, 107.0, 93.7, 75.1, 49.3, 30.1, 20.9],
             6: [13.2, 35.5, 71.8, 103.0, 121.0, 107.0, 103.0, 88.6, 74.6, 48.1, 17.0, 8.76],
             7: [24.4, 43.2, 79.0, 106.0, 126.0, 112.0, 113.0, 100.0, 82.3, 54.3, 28.9, 17.1],
             8: [29.1, 42.2, 84.4, 113.0, 120.0, 121.0, 125.0, 105.0, 87.7, 59.0, 33.6, 26.2],
             9: [32.4, 48.2, 89.2, 116.0, 123.0, 125.0, 119.0, 107.0, 93.4, 60.9, 37.3, 29.2],
             10: [27.3, 40.2, 76.1, 100.0, 109.0, 110.0, 106.0, 91.3, 76.3, 49.9, 29.8, 22.0],
             11: [31.8, 44.8, 86.1, 112.0, 122.0, 124.0, 125.0, 107.0, 87.4, 58.5, 33.5, 27.7],
             12: [31.8, 48.4, 88.5, 115.0, 130.0, 126.0, 129.0, 115.0, 93.3, 64.2, 38.0, 31.8]}
    return np.array(pvgis[integer])


def round_down(number):
    """Rounds number to nearest thousand."""
    return int(math.floor(number/1000) * 1000)


if __name__ == "__main__":
    # Identifies remaining system life
    date_string = sys.argv[1]
    commissioning_date = datetime.date(int(date_string[:4]), int(date_string[5:7]), int(date_string[8:10]))
    years_commissioned = (datetime.date.today() - commissioning_date).days / 365.25
    life_remaining = 25 - years_commissioned
    life_end_date = datetime.date.today() + datetime.timedelta(days=life_remaining * 365.25)

    # Identifies system capacity, and likely FiT rate
    if int(sys.argv[2]) == 0:
        system_size = int(sys.argv[3])
    else:
        system_size = int(sys.argv[3]) * 0.25
    fit_rate = identify_fit(commissioning_date, system_size)

    # Identifies generation profile
    pvgis_profile = identify_profile(int(sys.argv[4]))
    generation_profile = pvgis_profile * system_size

    # Establishes ownership structure, and other price assumptions
    if int(sys.argv[5]) == 0:
        ownership = 'Self'
    else:
        ownership = 'Investor'
    electricity_price = 0.10
    export_rate = 0.054
    ratio_exported = 0.5
    annual_discount_rate = 0

    # Prepare df
    months = pd.period_range(start=datetime.date.today(), end=life_end_date, freq='M')
    df = pd.DataFrame(months, columns=['Months'])
    df['Generation'] = df['Months'].apply(lambda x: generation_profile[x.month - 1])

    # Calculate cashflows
    df['FiT revenue'] = df['Generation'] * fit_rate
    df['Electricity savings'] = df['Generation'] * (1 - ratio_exported) * electricity_price
    df['Export revenue'] = df['Generation'] * ratio_exported * export_rate

    # Calculate NPVs
    fit_npv = np.npv((1 + annual_discount_rate)**(1/12) - 1, df['FiT revenue'])
    savings_npv = np.npv((1 + annual_discount_rate)**(1/12) - 1, df['Electricity savings'])
    export_npv = np.npv((1 + annual_discount_rate)**(1/12) - 1, df['Export revenue'])
    if ownership == 'Self':
        total_npv = round_down(fit_npv + savings_npv + export_npv)
        output = str(total_npv).rjust(5, '0') + '|' + '0'.rjust(5, '0')
    else:
        total_npv = round_down(savings_npv + export_npv)
        potential_npv = round_down(fit_npv + savings_npv + export_npv)
        output = str(total_npv).rjust(5, '0') + '|' + str(potential_npv).rjust(5, '0')
    print(output)
