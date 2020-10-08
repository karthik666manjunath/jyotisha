import logging

import numpy.testing
import tests.spatio_temporal
from jyotisha.panchaanga.spatio_temporal import City
from jyotisha.panchaanga.spatio_temporal import daily
from jyotisha.panchaanga.temporal import time
from jyotisha.panchaanga.temporal.interval import Interval, AngaSpan
from jyotisha.panchaanga.temporal.time import Date
from jyotisha.panchaanga.temporal.zodiac import AngaType, Anga

logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)


def test_solar_day():

  panchaanga = daily.DailyPanchaanga(
    city=tests.spatio_temporal.chennai, date=Date(2018, 1, 14))
  assert panchaanga.solar_sidereal_date_sunset.day == 1
  assert panchaanga.solar_sidereal_date_sunset.month == 10
  assert panchaanga.solar_sidereal_date_sunset.month_transition == 2458132.8291680976

  panchaanga = daily.DailyPanchaanga(
    city=tests.spatio_temporal.chennai, date=Date(2018, 2, 12))
  numpy.testing.assert_approx_equal(panchaanga.solar_sidereal_date_sunset.month_transition, 2458162.3747)

  panchaanga = daily.DailyPanchaanga(
    city=tests.spatio_temporal.chennai, date=Date(2018, 7, 13))
  assert panchaanga.solar_sidereal_date_sunset.month_transition is None
  assert panchaanga.solar_sidereal_date_sunset.day == 29
  assert panchaanga.solar_sidereal_date_sunset.month == 3

  panchaanga = daily.DailyPanchaanga(
    city=tests.spatio_temporal.chennai, date=Date(2018, 12, 31))
  assert panchaanga.solar_sidereal_date_sunset.month_transition is None

  panchaanga = daily.DailyPanchaanga(
    city=tests.spatio_temporal.chennai, date=Date(2017, 12, 16))
  assert panchaanga.solar_sidereal_date_sunset.day == 1
  assert panchaanga.solar_sidereal_date_sunset.month == 9

  panchaanga = daily.DailyPanchaanga.from_city_and_julian_day(
    city=tests.spatio_temporal.chennai, julian_day=2457023.27)
  logging.debug(str(panchaanga))
  assert panchaanga.solar_sidereal_date_sunset.day == 16
  assert panchaanga.solar_sidereal_date_sunset.month == 9

  panchaanga = daily.DailyPanchaanga(
    city=tests.spatio_temporal.chennai, date=Date(2017, 12, 31))
  assert panchaanga.solar_sidereal_date_sunset.day == 16
  assert panchaanga.solar_sidereal_date_sunset.month == 9


def test_sunrise_mtv():
  city = City.get_city_from_db('Cupertino')
  panchaanga = daily.DailyPanchaanga(city=city, date=Date(year=2018, month=11, day=11))
  panchaanga.compute_sun_moon_transitions()
  numpy.testing.assert_approx_equal(panchaanga.jd_sunrise, 2458434.11)


def test_tb_muhuurta_blr():
  city = City.get_city_from_db('Bangalore')
  panchaanga = daily.DailyPanchaanga(city=city, date=Date(year=2019, month=9, day=10))
  panchaanga.compute_tb_muhuurtas()
  assert len(panchaanga.day_length_based_periods.tb_muhuurtas) == 15
  assert panchaanga.day_length_based_periods.tb_muhuurtas[0].jd_start == panchaanga.jd_sunrise
  for muhurta in panchaanga.day_length_based_periods.tb_muhuurtas:
    logging.info(muhurta.to_localized_string(city=city))


def test_jd_start_DST_orinda_ca():
  #  8:0:0.00 UT on March 9, 2019
  city = City.get_city_from_db('Orinda')
  assert daily.DailyPanchaanga.from_city_and_julian_day(city=city,
                                                        julian_day=2458551.8333333335).julian_day_start == 2458551.8333333335
  assert daily.DailyPanchaanga.from_city_and_julian_day(city=city,
                                                        julian_day=2458552.8333333335).julian_day_start == 2458552.8333333335

def test_get_lagna_float():
  city = City.get_city_from_db('Chennai')
  numpy.testing.assert_allclose(
    city.get_lagna_float(
      2444961.7125), 10.353595502472984, rtol=1e-4)


def test_find_anga():
  city = City.get_city_from_db('Bangalore')
  panchaanga = daily.DailyPanchaanga(city=city, date=Date(year=2018, month=7, day=13))
  assert panchaanga.sunrise_day_angas.find_anga(anga_id=1, anga_type=AngaType.TITHI) is not None
  

def test_tithi():
  city = City.get_city_from_db('Bangalore')
  panchaanga = daily.DailyPanchaanga(city=city, date=Date(year=2018, month=7, day=14))
  assert panchaanga.sunrise_day_angas.tithi_at_sunrise.index == 2


def test_get_anga_data_1981_12_23():
  # 0:58:12.29 UT on December 23, 1981
  panchaanga = daily.DailyPanchaanga.from_city_and_julian_day(
    city=tests.spatio_temporal.chennai, julian_day=2444961.54042)
  assert panchaanga.sunrise_day_angas.tithis_with_ends[0].to_string(floating_point_precision=3) == [
    AngaSpan(anga=Anga(index=27, anga_type_id=AngaType.TITHI.name), jd_end=2444961.5992132244, jd_start=None)][0].to_string(floating_point_precision=3)
  
  # 5:55:34.39 UT on December 23, 1981
  assert panchaanga.sunrise_day_angas.nakshatras_with_ends[0].to_string(floating_point_precision=3) == [AngaSpan(anga=Anga(index=16, anga_type_id=AngaType.NAKSHATRA.name), jd_end=2444961.746925843, jd_start=2444960.622,)][0].to_string(floating_point_precision=3)
  
  # 16:23:10.51 UT on December 23, 1981
  assert panchaanga.sunrise_day_angas.yogas_with_ends[0].to_string(floating_point_precision=3)[0] == [
    AngaSpan(anga=Anga(index=8, anga_type_id=AngaType.YOGA.name), jd_end=2444962.18276057, jd_start=2444961.045)][0].to_string(floating_point_precision=3)[0]

  # 15:42:24.09 UT on December 23, 1981
  assert panchaanga.sunrise_day_angas.karanas_with_ends[0].to_string(floating_point_precision=3) == [
    AngaSpan(anga=Anga(index=54, anga_type_id=AngaType.KARANA.name), jd_end=2444961.5992132244, jd_start=2444961.045), Interval(name=55, jd_end=2444962.1544454526, jd_start=2444961.045)][0].to_string(floating_point_precision=3)


# def test_festivals():
#   city = City.get_city_from_db('Bangalore')
#   panchaanga0 = daily.DailyPanchaanga(city=city, date=Date(year=2018, month=4, day=14))
#   panchaanga = daily.DailyPanchaanga(city=city, date=Date(year=2018, month=4, day=15))
#   panchaanga.assign_festivals(previous_day_panchaanga=panchaanga0, no_next_day_lookup=True)
# 
#   assert "viSukkan2i" in panchaanga.festival_id_to_instance


def test_get_lagna_data():
  city = City('X', 13.08784, 80.27847, 'Asia/Calcutta')
  from jyotisha.panchaanga.temporal import zodiac
  actual = daily.DailyPanchaanga.from_city_and_julian_day(city=city, julian_day=2458222.5208333335).get_lagna_data(
    ayanaamsha_id=zodiac.Ayanamsha.CHITRA_AT_180)
  expected = [(12, 2458222.5214310056), (1, 2458222.596420153),
              (2, 2458222.6812926503), (3, 2458222.772619788),
              (4, 2458222.8624254186), (5, 2458222.9478168003),
              (6, 2458223.0322211445), (7, 2458223.1202004547),
              (8, 2458223.211770839), (9, 2458223.3000455885),
              (10, 2458223.3787625884), (11, 2458223.4494649624),
              (12, 2458223.518700759)]
  numpy.testing.assert_allclose(actual, expected, rtol=1e-4) 
