import numpy
from jyotisha.panchaanga.temporal import zodiac, time
from jyotisha.panchaanga.temporal.time import Date
from jyotisha.panchaanga.temporal.zodiac import NakshatraDivision, Ayanamsha, AngaSpanFinder
from jyotisha.panchaanga.temporal.zodiac.angas import AngaType


def test_get_ayanaamsha():
  ayanaamsha = zodiac.Ayanamsha.singleton(ayanaamsha_id=zodiac.Ayanamsha.CHITRA_AT_180)
  assert ayanaamsha.get_offset(2458434.083333251) == 24.094859396693067


def disabled_test_swe_ayanaamsha_api():
  import swisseph as swe
  swe.set_sid_mode(swe.SIDM_LAHIRI)
  # city = City.from_address_and_timezone('Cupertino, CA', "America/Los_Angeles")
  # jd = city.local_time_to_julian_day(year=2018, month=11, day=11, hours=6, minutes=0, seconds=0)
  assert swe.get_ayanamsa_ut(2458434.083333251) == 24.120535828308334


def test_get_anga():

  nd = NakshatraDivision(jd=time.ist_timezone.local_time_to_julian_day(Date(2018, 7, 14)), ayanaamsha_id=Ayanamsha.CHITRA_AT_180)
  assert nd.get_anga(
    anga_type=AngaType.TITHI).index == 1

  nd = NakshatraDivision(jd=time.ist_timezone.local_time_to_julian_day(Date(2018, 7, 14, 6, 1)), ayanaamsha_id=Ayanamsha.CHITRA_AT_180)
  assert nd.get_anga(
    anga_type=AngaType.TITHI).index == 2

  nd = NakshatraDivision(jd=time.ist_timezone.local_time_to_julian_day(Date(2018, 7, 13)), ayanaamsha_id=Ayanamsha.CHITRA_AT_180)
  assert nd.get_anga(
    anga_type=AngaType.TITHI).index == 30
  assert nd.get_anga(
    anga_type=AngaType.SIDEREAL_MONTH).index == 3

  # Just before meSha sankrAnti
  assert NakshatraDivision(jd=time.ist_timezone.local_time_to_julian_day(Date(2018, 4, 13)), ayanaamsha_id=Ayanamsha.CHITRA_AT_180).get_anga(
    anga_type=AngaType.SIDEREAL_MONTH).index == 12


  # 5:6:0.00 UT on December 23, 1981
  nd = NakshatraDivision(2444961.7125, ayanaamsha_id=Ayanamsha.CHITRA_AT_180)
  assert nd.get_anga(AngaType.NAKSHATRA) == 16
  assert nd.get_anga(AngaType.TITHI) == 28
  assert nd.get_anga(AngaType.YOGA) == 8
  assert nd.get_anga(AngaType.KARANA) == 55
  assert nd.get_solar_raashi() == 9


def test_get_anga_span_solar_month():
  from jyotisha.panchaanga.temporal import time
  span_finder = AngaSpanFinder(default_anga_type=AngaType.SIDEREAL_MONTH, ayanaamsha_id=Ayanamsha.CHITRA_AT_180)

  assert span_finder.find(jd1=2458222.0333434483-32, jd2=2458222.0333434483 + 4, target_anga_in=12, ).to_tuple() == (2458192.24785228, 2458222.6026552585)

  jd2 = time.ist_timezone.local_time_to_julian_day(time.Date(2020, 4, 16))
  assert span_finder.find(jd1=jd2-32, jd2=jd2, target_anga_in=1).to_json_map(floating_point_precision=3) == {'anga': {'anga_type_id': 'SIDEREAL_MONTH', 'index': 1, 'jsonClass': 'Anga'},
 'default_to_none': True,
 'jd_start': 2458953.11,
 'jsonClass': 'AngaSpan'}

  assert span_finder.find(jd1=2458133.0189002366-32, jd2=2458133.0189002366, target_anga_in=10, ).to_json_map(floating_point_precision=3) == {'anga': {'anga_type_id': 'SIDEREAL_MONTH', 'index': 10, 'jsonClass': 'Anga'},
 'default_to_none': True,
 'jd_start': 2458132.829,
 'jsonClass': 'AngaSpan'}


def test_get_anga_span_tithi():
  span_finder = AngaSpanFinder(default_anga_type=AngaType.TITHI, ayanaamsha_id=Ayanamsha.CHITRA_AT_180)

  assert span_finder.find(jd1=2458102.5, jd2=2458108.5, target_anga_in=30).to_tuple() == (2458104.6663699686, 2458105.771125107)
  
  assert span_finder.find(jd1=2444959.54042, jd2=2444963.54076, target_anga_in=27).to_tuple() == (2444960.4924699212, 2444961.599213224)


def test_get_tithis_in_period():
  new_moon_jds = zodiac.get_tithis_in_period(jd_start=time.ist_timezone.local_time_to_julian_day(Date(year=2020, month=1, day=1)), jd_end=time.ist_timezone.local_time_to_julian_day(Date(year=2020, month=6, day=30)), tithi=30)
  numpy.testing.assert_array_almost_equal(new_moon_jds, [2458872.36655025,
                          2458902.0647052005,
                          2458931.792117506,
                          2458961.5055956016,
                          2458991.1712410315,
                          2459020.765607745], decimal=3)


def test_get_previous_solstice():
  solstice = zodiac.get_previous_solstice(jd=time.ist_timezone.local_time_to_julian_day(Date(2018, 1, 14)))
  expected_jd_start = time.ist_timezone.local_time_to_julian_day(date=Date(year=2017, month=12, day=21, hour=16, minute=28))
  numpy.testing.assert_approx_equal(solstice.jd_start, expected_jd_start, significant=4)

  solstice = zodiac.get_previous_solstice(jd=time.ist_timezone.local_time_to_julian_day(Date(2018, 3, 14)))
  expected_jd_start = time.ist_timezone.local_time_to_julian_day(date=Date(year=2017, month=12, day=21, hour=16, minute=28))
  numpy.testing.assert_approx_equal(solstice.jd_start, expected_jd_start, significant=4)

  solstice = zodiac.get_previous_solstice(jd=time.ist_timezone.local_time_to_julian_day(Date(2018, 7, 14)))
  expected_jd_start = time.ist_timezone.local_time_to_julian_day(date=Date(year=2018, month=6, day=20, hour=21, minute=44))
  numpy.testing.assert_approx_equal(solstice.jd_start, expected_jd_start, significant=4)


