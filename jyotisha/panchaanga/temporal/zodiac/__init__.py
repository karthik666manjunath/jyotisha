import logging
import sys
from math import floor
from numbers import Number

import methodtools
import numpy
import swisseph as swe
from jyotisha.panchaanga.temporal.body import Graha
from jyotisha.panchaanga.temporal.interval import Interval, AngaSpan
from jyotisha.panchaanga.temporal.zodiac.angas import AngaType, Anga
from sanskrit_data.schema import common
from sanskrit_data.schema.common import JsonObject
from scipy.optimize import brentq

# noinspection SpellCheckingInspection
logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)


class Ayanamsha(common.JsonObject):
  VERNAL_EQUINOX_AT_0 = "VERNAL_EQUINOX_AT_0"
  CHITRA_AT_180 = "CHITRA_AT_180"
  ASHVINI_STARTING_0 = "ASHVINI_STARTING_0"
  RASHTRIYA_PANCHANGA_NAKSHATRA_TRACKING = "RASHTRIYA_PANCHANGA_NAKSHATRA_TRACKING"

  @methodtools.lru_cache(maxsize=None)
  @classmethod
  def singleton(cls, ayanaamsha_id):
    return cls(ayanaamsha_id=ayanaamsha_id)

  def __init__(self, ayanaamsha_id):
    super().__init__()
    self.ayanaamsha_id = ayanaamsha_id

  def get_offset(self, jd):
    if self.ayanaamsha_id == Ayanamsha.VERNAL_EQUINOX_AT_0:
      return 0
    elif self.ayanaamsha_id == Ayanamsha.CHITRA_AT_180:
      # TODO: The below fails due to https://github.com/astrorigin/pyswisseph/issues/35
      from jyotisha.panchaanga.temporal import body
      return body.get_star_longitude(star="Spica", jd=jd) - 180
    elif self.ayanaamsha_id == Ayanamsha.ASHVINI_STARTING_0:
      return 0
    elif self.ayanaamsha_id == Ayanamsha.RASHTRIYA_PANCHANGA_NAKSHATRA_TRACKING:
      swe.set_sid_mode(swe.SIDM_LAHIRI)
      return swe.get_ayanamsa_ut(jd)
    raise Exception("Bad ayamasha_id")


class NakshatraDivision(common.JsonObject):
  """Nakshatra division at a certain time, according to a certain ayanaamsha."""

  def __init__(self, jd, ayanaamsha_id):
    super().__init__()
    self.ayanaamsha_id = ayanaamsha_id
    self.julday = jd

  def get_fractional_division_for_body(self, body: Graha, anga_type: AngaType) -> float:
    """
    
    :param body: graha ID.
    :return: 0.x for AshvinI and so on.
    """
    longitude = body.get_longitude(self.julday, ayanaamsha_id=self.ayanaamsha_id)
    return self.longitude_to_fractional_division(longitude=longitude, anga_type=anga_type)

  def get_equatorial_boundary_coordinates(self):
    """Get equatorial coordinates for the points where the ecliptic nakShatra boundary longitude intersects the ecliptic."""
    nakShatra_ends = ((numpy.arange(27) + 1) * (360.0 / 27.0) + Ayanamsha.singleton(
      self.ayanaamsha_id).get_offset(
      self.julday)) % 360
    equatorial_boundary_coordinates = [ecliptic_to_equatorial(longitude=longitude, latitude=0) for longitude in nakShatra_ends]
    return equatorial_boundary_coordinates

  def get_stellarium_nakshatra_boundaries(self):
    equatorial_boundary_coordinates_with_ra = self.get_equatorial_boundary_coordinates()
    ecliptic_north_pole_with_ra = ecliptic_to_equatorial(longitude=20, latitude=90)
    # logging.debug(ecliptic_north_pole_with_ra)
    ecliptic_south_pole_with_ra = ecliptic_to_equatorial(longitude=20, latitude=-90)
    # logging.debug(ecliptic_south_pole_with_ra)
    for index, (boundary_ra, boundary_declination) in enumerate(equatorial_boundary_coordinates_with_ra):
      print(
        '3 %(north_pole_ra)f %(north_pole_dec)f %(boundary_ra)f %(boundary_declination)f %(south_pole_ra)f %(south_pole_dec)f 2 N%(sector_id_1)02d N%(sector_id_2)02d' % dict(
          north_pole_ra=ecliptic_north_pole_with_ra[0],
          north_pole_dec=ecliptic_north_pole_with_ra[1],
          boundary_ra=boundary_ra,
          boundary_declination=boundary_declination,
          south_pole_ra=ecliptic_south_pole_with_ra[0],
          south_pole_dec=ecliptic_south_pole_with_ra[1],
          sector_id_1=(index % 27 + 1),
          sector_id_2=((index + 1) % 27 + 1)
        ))

  def longitude_to_fractional_division(self, longitude, anga_type):
    return (longitude % 360) / anga_type.arc_length

  def get_anga_float(self, anga_type):
    """Returns the anga/ temporal property. Computed based on lunar and solar longitudes, division of a circle into a certain number of degrees (arc_len).

      Args:
        :param anga_type: One of the pre-defined tuple-valued constants in the panchaanga
        class, such as TITHI, nakshatra, YOGA, KARANA or SOLAR_MONTH

      Returns:
        float anga
    """
    if anga_type == AngaType.TITHI:
      # For efficiency - avoid lookups.
      ayanaamsha_id = Ayanamsha.VERNAL_EQUINOX_AT_0
    else:
      ayanaamsha_id = self.ayanaamsha_id

    w_moon = anga_type.weight_moon
    w_sun = anga_type.weight_sun
    arc_len = anga_type.arc_length

    lcalc = 0  # computing offset longitudes

    #  Get the lunar longitude, starting at the ayanaamsha point in the ecliptic.
    if w_moon != 0:
      lmoon = Graha.singleton(Graha.MOON).get_longitude(self.julday, ayanaamsha_id=ayanaamsha_id)
      lcalc += w_moon * lmoon

    #  Get the solar longitude, starting at the ayanaamsha point in the ecliptic.
    if w_sun != 0:
      lsun = Graha.singleton(Graha.SUN).get_longitude(self.julday, ayanaamsha_id=ayanaamsha_id)
      lcalc += w_sun * lsun

    return self.longitude_to_fractional_division(longitude=lcalc, anga_type=anga_type)

  def get_anga(self, anga_type):
    """Returns the anga prevailing at a particular time. Computed based on lunar and solar longitudes, division of a circle into a certain number of degrees (arc_len).

      Args:
        float arc_len: The arc_len for the corresponding anga

      Returns:
        int anga
    """

    return Anga(index=int(1 + floor(self.get_anga_float(anga_type))), anga_type_id=anga_type.name)

  def get_all_angas(self):
    """Compute various properties of the time based on lunar and solar longitudes, division of a circle into a certain number of degrees (arc_len).
    """
    anga_objects = [AngaType.TITHI, AngaType.TITHI_PADA, AngaType.NAKSHATRA, AngaType.NAKSHATRA_PADA, AngaType.RASHI,
                    AngaType.SOLAR_MONTH, AngaType.SOLAR_NAKSH, AngaType.YOGA, AngaType.KARANA]
    angas = list(map(lambda anga_object: self.get_anga(anga_type=anga_object), anga_objects))
    anga_ids = list(map(lambda anga_obj: anga_obj.index, anga_objects))
    return dict(list(zip(anga_ids, angas)))

  def get_nakshatra(self):
    """Returns the nakshatra prevailing at a given moment

    Nakshatra is computed based on the longitude of the Moon; in
    addition, to obtain the absolute value of the longitude, the
    ayanamsa is required to be subtracted.

    Returns:
      int nakShatram, where 1 stands for Ashwini, ..., 14 stands
      for Chitra, ..., 27 stands for Revati

    """

    return self.get_anga(AngaType.NAKSHATRA)

  def get_yoga(self):
    """Returns the yoha prevailing at a given moment

    Yoga is computed based on the longitude of the Moon and longitude of
    the Sun; in addition, to obtain the absolute value of the longitude, the
    ayanamsa is required to be subtracted (for each).

    Returns:
      int yoga, where 1 stands for Vishkambha and 27 stands for Vaidhrti
    """

    return self.get_anga(AngaType.YOGA)

  def get_solar_raashi(self):
    """Returns the solar rashi prevailing at a given moment

    Solar month is computed based on the longitude of the sun; in
    addition, to obtain the absolute value of the longitude, the
    ayanamsa is required to be subtracted.

    Returns:
      int rashi, where 1 stands for mESa, ..., 12 stands for mIna
    """

    return self.get_anga(AngaType.SOLAR_MONTH)


def longitude_to_right_ascension(longitude):
  return (360 - longitude) / 360 * 24


def ecliptic_to_equatorial(longitude, latitude):
  coordinates = swe.cotrans(lon=longitude, lat=latitude, dist=9999999, obliquity=23.437404)
  # swe.cotrans returns the right ascension longitude in degrees, rather than hours.
  return (
    longitude_to_right_ascension(coordinates[0]), coordinates[1])


class AngaSpanFinder(JsonObject):
  def __init__(self, ayanaamsha_id, default_anga_type=None):
    self.ayanaamsha_id = ayanaamsha_id
    self.default_anga_type = default_anga_type

  def _get_anga(self, jd, anga_type):
    return NakshatraDivision(jd, ayanaamsha_id=self.ayanaamsha_id).get_anga( anga_type=anga_type)

  def _get_anga_float_offset(self, jd, target_anga):
    anga_float = NakshatraDivision(jd, ayanaamsha_id=self.ayanaamsha_id).get_anga_float(anga_type=target_anga.get_type())
    num_angas = int(360.0 / target_anga.get_type().arc_length)
    if anga_float > target_anga.index:
      return anga_float - num_angas # A negative number
    else:
      return anga_float - (target_anga.index - 1)

  def _interpolate_for_start(self, jd1, jd2, target_anga):
    try:
      # noinspection PyTypeChecker
      return brentq(lambda x: self._get_anga_float_offset(jd=x, target_anga=target_anga), jd1, jd2)
    except ValueError:
      return None

  def find_anga_start_between(self, jd1, jd2, target_anga):
    jd_start = None
    num_angas = int(360.0 / target_anga.get_type().arc_length)
    min_step = 0.5  # Min Step for moving
    jd_bracket_L = jd1
    jd_now = jd1
    while jd_now <= jd2 and jd_start is None:
      anga_now = self._get_anga(jd=jd_now, anga_type=target_anga.get_type())

      if anga_now < target_anga or (target_anga == 1 and anga_now == num_angas):
        # So, jd_now will be lower than jd_start
        jd_bracket_L = jd_now
      if anga_now == target_anga:
        # In this branch, anga_now will have overshot the jd_start of the required interval.
        jd_start = self._interpolate_for_start(jd1=jd_bracket_L, jd2=jd_now, target_anga=target_anga)
      if jd_now == jd2:
        # Prevent infinite loop
        break
      jd_now = min(jd_now + min_step, jd2)
    return jd_start

  def find(self, jd1: float, jd2: float, target_anga_in) -> Interval:
    """Computes anga spans for sunrise_day_angas such as tithi, nakshatra, yoga
        and karana.

        Args:
          :param target_anga_in: 
          :param jd1: return the first span that starts after this date
          :param jd2: return the first span that ends before this date
          :param ayanaamsha_id
          :param debug

        Returns:
          AngaSpan
    """
    if isinstance(target_anga_in, Number):
      # TODO: Remove this backward compatibility fix
      target_anga = Anga(index=target_anga_in, anga_type_id=self.default_anga_type.name)
    else:
      target_anga = target_anga_in
    num_angas = int(360.0 / target_anga.get_type().arc_length)
    if target_anga > num_angas or target_anga < 1:
      raise ValueError

    anga_interval = AngaSpan(jd_start=None, jd_end=None, anga=target_anga)

    anga_interval.jd_start = self.find_anga_start_between(jd1=jd1, jd2=jd2, target_anga=target_anga)

    if anga_interval.jd_start is None:
      return AngaSpan(jd_start=None, jd_end=None, anga=target_anga)  # If it doesn't start, we don't care if it ends!

    next_anga = target_anga + 1
    anga_interval.jd_end = self.find_anga_start_between(jd1=anga_interval.jd_start, jd2=jd2, target_anga=next_anga)
    return anga_interval


# Essential for depickling to work.
common.update_json_class_index(sys.modules[__name__])


def get_tithis_in_period(jd_start, jd_end, tithi):
  if jd_start > jd_end:
    raise ValueError((jd_start, jd_end))
  jd = jd_start
  anga_finder = AngaSpanFinder(ayanaamsha_id=Ayanamsha.ASHVINI_STARTING_0, default_anga_type=AngaType.TITHI)
  new_moon_jds = []
  while jd < jd_end:
    new_moon = anga_finder.find(
      jd1=jd, jd2=jd + 30,
      target_anga_in=tithi)
    if new_moon is None:
      raise Exception("Could not find a new moon between %f and %f" % (jd, jd+30))
    if new_moon.jd_start < jd_end:
      new_moon_jds.append(new_moon.jd_start)
    jd = new_moon.jd_start + 28
  return new_moon_jds


def get_tropical_month(jd):
  nd = NakshatraDivision(jd=jd, ayanaamsha_id=Ayanamsha.ASHVINI_STARTING_0)
  return nd.get_anga(anga_type=AngaType.SOLAR_MONTH)


def get_previous_solstice(jd):
  tropical_month = get_tropical_month(jd=jd)
  if tropical_month >= 4 and tropical_month < 10:
    target_month = 4
  else:
    target_month = 10
  months_past_solstice = (tropical_month - target_month) % 12
  jd1 = jd - (months_past_solstice * 30 + months_past_solstice + 30)
  jd2 = jd - (months_past_solstice * 30 + months_past_solstice) + 30
  anga_span_finder = AngaSpanFinder(ayanaamsha_id=Ayanamsha.ASHVINI_STARTING_0, default_anga_type=AngaType.SOLAR_MONTH)
  return anga_span_finder.find(jd1=jd1, jd2=jd2, target_anga_in=target_month)




if __name__ == '__main__':
  # lahiri_nakshatra_division = NakshatraDivision(julday=temporal.utc_to_jd(year=2017, month=8, day=19, hour=11, minutes=10, seconds=0, flag=1)[0])
  pass
