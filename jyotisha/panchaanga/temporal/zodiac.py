import logging
from math import floor

import methodtools
import numpy
import swisseph as swe
from scipy.optimize import brentq

from jyotisha.panchaanga.temporal.body import Graha
from jyotisha.panchaanga.temporal.interval import Interval
from sanskrit_data.schema import common
from sanskrit_data.schema.common import JsonObject

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
  def singleton(cls, ayanamsha_id):
    return cls(ayanamsha_id=ayanamsha_id)

  def __init__(self, ayanamsha_id):
    super().__init__()
    self.ayanamsha_id = ayanamsha_id

  def get_offset(self, jd):
    if self.ayanamsha_id == Ayanamsha.VERNAL_EQUINOX_AT_0:
      return 0
    elif self.ayanamsha_id == Ayanamsha.CHITRA_AT_180:
      # TODO: The below fails due to https://github.com/astrorigin/pyswisseph/issues/35
      from jyotisha.panchaanga.temporal import body
      return body.get_star_longitude(star="Spica", jd=jd) - 180
    elif self.ayanamsha_id == Ayanamsha.ASHVINI_STARTING_0:
      return 0
    elif self.ayanamsha_id == Ayanamsha.RASHTRIYA_PANCHANGA_NAKSHATRA_TRACKING:
      swe.set_sid_mode(swe.SIDM_LAHIRI)
      return swe.get_ayanamsa_ut(jd)
    raise Exception("Bad ayamasha_id")


class NakshatraDivision(common.JsonObject):
  """Nakshatra division at a certain time, according to a certain ayanaamsha."""

  def __init__(self, julday, ayanamsha_id):
    super().__init__()
    self.ayanamsha_id = ayanamsha_id

    self.set_time(julday=julday)

  # noinspection PyAttributeOutsideInit
  def set_time(self, julday):
    self.julday = julday
    self.right_boundaries = ((numpy.arange(27) + 1) * (360.0 / 27.0) + Ayanamsha.singleton(
      self.ayanamsha_id).get_offset(
      julday)) % 360

  def get_nakshatra_for_body(self, body):
    """
    
    :param body: graha ID.
    :return: 1.x for AshvinI and so on.
    """
    if self.julday is not None:
      self.set_time(julday=self.julday)
    logging.debug(Ayanamsha.singleton(self.ayanamsha_id).get_offset(self.julday))
    return Graha.singleton(body).get_longitude_offset(self.julday, ayanamsha_id=self.ayanamsha_id) / (360.0 / 27.0) + 1

  def get_equatorial_boundary_coordinates(self):
    """Get equatorial coordinates for the points where the ecliptic nakShatra boundary longitude intersects the ecliptic."""
    equatorial_boundary_coordinates = [ecliptic_to_equatorial(longitude=longitude, latitude=0) for longitude in
                                       self.right_boundaries]
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

  def get_anga_float(self, anga_type, offset_angas=0, debug=False):
    """Returns the angam/ temporal property. Computed based on lunar and solar longitudes, division of a circle into a certain number of degrees (arc_len).

      Args:
        :param anga_type: One of the pre-defined tuple-valued constants in the panchaanga
        class, such as TITHI, NAKSHATRAM, YOGA, KARANAM or SOLAR_MONTH
        :param offset_angas: 
        :param debug: Unused

      Returns:
        float angam
    """
    if anga_type == AngaType.TITHI:
      # For efficiency - avoid lookups.
      ayanamsha_id = Ayanamsha.VERNAL_EQUINOX_AT_0
    else:
      ayanamsha_id = self.ayanamsha_id

    w_moon = anga_type.weight_moon
    w_sun = anga_type.weight_sun
    arc_len = anga_type.arc_length

    lcalc = 0  # computing offset longitudes

    #  Get the lunar longitude, starting at the ayanaamsha point in the ecliptic.
    if w_moon != 0:
      lmoon = Graha.singleton(Graha.MOON).get_longitude_offset(self.julday, offset=0, ayanamsha_id=ayanamsha_id)
      lcalc += w_moon * lmoon

    #  Get the solar longitude, starting at the ayanaamsha point in the ecliptic.
    if w_sun != 0:
      lsun = Graha.singleton(Graha.SUN).get_longitude_offset(self.julday, offset=0, ayanamsha_id=ayanamsha_id)
      lcalc += w_sun * lsun

    lcalc = lcalc % 360

    if offset_angas + int(360.0 / arc_len) == 0 and lcalc < arc_len:
      # Angam 1 -- needs different treatment, because of 'discontinuity'
      return lcalc / arc_len
    else:
      return (lcalc / arc_len) + offset_angas

  def get_anga(self, angam_type):
    """Returns the angam prevailing at a particular time. Computed based on lunar and solar longitudes, division of a circle into a certain number of degrees (arc_len).

      Args:
        float arc_len: The arc_len for the corresponding angam

      Returns:
        int angam
    """

    return int(1 + floor(self.get_anga_float(angam_type)))

  def get_all_angas(self):
    """Compute various properties of the time based on lunar and solar longitudes, division of a circle into a certain number of degrees (arc_len).
    """
    anga_objects = [AngaType.TITHI, AngaType.TITHI_PADA, AngaType.NAKSHATRA, AngaType.NAKSHATRA_PADA, AngaType.RASHI,
                    AngaType.SOLAR_MONTH, AngaType.SOLAR_NAKSH, AngaType.YOGA, AngaType.KARANA]
    angas = list(map(lambda anga_object: self.get_anga(angam_type=anga_object), anga_objects))
    anga_ids = list(map(lambda anga_obj: anga_obj.name, anga_objects))
    return dict(list(zip(anga_ids, angas)))

  def get_nakshatra(self):
    """Returns the nakshatram prevailing at a given moment

    Nakshatram is computed based on the longitude of the Moon; in
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


class AngaType(JsonObject):
  # The below class variables are declared here, but instantiated later.
  TITHI = None
  TITHI_PADA = None
  NAKSHATRA = None
  NAKSHATRA_PADA = None
  RASHI = None
  YOGA = None
  KARANA = None
  SOLAR_MONTH = None
  SOLAR_NAKSH = None
  SOLAR_NAKSH_PADA = None

  def __init__(self, name, arc_length, weight_moon, weight_sun):
    super(AngaType, self).__init__()
    self.name = name
    self.arc_length = arc_length
    self.weight_moon = weight_moon
    self.weight_sun = weight_sun


AngaType.TITHI = AngaType(name='TITHI', arc_length=360.0 / 30.0, weight_moon=1, weight_sun=-1)
AngaType.TITHI_PADA = AngaType(name='TITHI_PADA', arc_length=360.0 / 120.0, weight_moon=1, weight_sun=-1)
AngaType.NAKSHATRA = AngaType(name='NAKSHATRAM', arc_length=360.0 / 27.0, weight_moon=1, weight_sun=0)
AngaType.NAKSHATRA_PADA = AngaType(name='NAKSHATRA_PADA', arc_length=360.0 / 108.0, weight_moon=1, weight_sun=0)
AngaType.RASHI = AngaType(name='RASHI', arc_length=360.0 / 12.0, weight_moon=1, weight_sun=0)
AngaType.YOGA = AngaType(name='YOGA', arc_length=360.0 / 27.0, weight_moon=1, weight_sun=1)
AngaType.KARANA = AngaType(name='KARANAM', arc_length=360.0 / 60.0, weight_moon=1, weight_sun=-1)
AngaType.SOLAR_MONTH = AngaType(name='SOLAR_MONTH', arc_length=360.0 / 12.0, weight_moon=0, weight_sun=1)
AngaType.SOLAR_NAKSH = AngaType(name='SOLAR_NAKSH', arc_length=360.0 / 27.0, weight_moon=0, weight_sun=1)
AngaType.SOLAR_NAKSH_PADA = AngaType(name='SOLAR_NAKSH_PADA', arc_length=360.0 / 108.0, weight_moon=0, weight_sun=1)


def get_angam_data(jd_sunrise, jd_sunrise_tmrw, anga_type, ayanamsha_id):
  """Computes angam data for angams such as tithi, nakshatram, yoga
  and karanam.

  Args:
      :param jd_sunrise:
      :param jd_sunrise_tmrw:
      :param anga_type: TITHI, NAKSHATRAM, YOGA, KARANAM, SOLAR_MONTH, SOLAR_NAKSH
      :param ayanamsha_id:

  Returns:
    tuple: A tuple comprising
      angam_sunrise: The angam that prevails as sunrise
      angam_data: a list of (int, float) tuples detailing the angams
      for the day and their end-times (Julian day)
  """
  w_moon = anga_type.weight_moon
  w_sun = anga_type.weight_sun
  arc_len = anga_type.arc_length

  num_angas = int(360.0 / arc_len)

  # Compute angam details
  angam_now = NakshatraDivision(jd_sunrise, ayanamsha_id=ayanamsha_id).get_anga(anga_type)
  angam_tmrw = NakshatraDivision(jd_sunrise_tmrw, ayanamsha_id=ayanamsha_id).get_anga(anga_type)

  angams_list = []

  num_angas_today = (angam_tmrw - angam_now) % num_angas

  if num_angas_today == 0:
    # The angam does not change until sunrise tomorrow
    return [(angam_now, None)]
  else:
    lmoon = Graha.singleton(Graha.MOON).get_longitude_offset(jd_sunrise, offset=0, ayanamsha_id=ayanamsha_id)

    lsun = Graha.singleton(Graha.SUN).get_longitude_offset(jd_sunrise, offset=0, ayanamsha_id=ayanamsha_id)

    lmoon_tmrw = Graha.singleton(Graha.MOON).get_longitude_offset(jd_sunrise_tmrw, offset=0, ayanamsha_id=ayanamsha_id)

    lsun_tmrw = Graha.singleton(Graha.SUN).get_longitude_offset(jd_sunrise_tmrw, offset=0, ayanamsha_id=ayanamsha_id)

    for i in range(num_angas_today):
      angam_remaining = arc_len * (i + 1) - (((lmoon * w_moon +
                                               lsun * w_sun) % 360) % arc_len)

      # First compute approximate end time by essentially assuming
      # the speed of the moon and the sun to be constant
      # throughout the day. Therefore, angam_remaining is computed
      # just based on the difference in longitudes for sun and
      # moon today and tomorrow.
      approx_end = jd_sunrise + angam_remaining / (((lmoon_tmrw - lmoon) % 360) * w_moon +
                                                   ((lsun_tmrw - lsun) % 360) * w_sun)

      # Initial guess value for the exact end time of the angam
      x0 = approx_end

      # What is the target (next) angam? It is needed to be passed
      # to get_angam_float for zero-finding. If the target angam
      # is say, 12, then we need to subtract 12 from the value
      # returned by get_angam_float, so that this function can be
      # passed as is to a zero-finding method like brentq or
      # newton. Since we have a good x0 guess, it is easy to
      # bracket the function in an interval where the function
      # changes sign. Therefore, brenth can be used, as suggested
      # in the scipy documentation.
      target = (angam_now + i - 1) % num_angas + 1

      # Approximate error in calculation of end time -- arbitrary
      # used to bracket the root, for brenth
      TDELTA = 0.05
      try:
        def f(x):
          return NakshatraDivision(x, ayanamsha_id=ayanamsha_id).get_anga_float(anga_type=anga_type,
                                                                                offset_angas=-target, debug=False)

        # noinspection PyTypeChecker
        t_act = brentq(f, x0 - TDELTA, x0 + TDELTA)
      except ValueError:
        logging.warning('Unable to bracket! Using approximate t_end itself.')
        logging.warning(locals())
        t_act = approx_end
      angams_list.extend([((angam_now + i - 1) % num_angas + 1, t_act)])
  return angams_list


class AngaSpan(Interval):
  @classmethod
  def _find_anga_start_between(cls, jd1, jd2, angam_type, target_anga_id, ayanamsha_id):
    jd_start = None
    num_angas = int(360.0 / angam_type.arc_length)
    min_step = 0.5  # Min Step for moving
    jd_bracket_L = jd1
    jd_now = jd1
    while jd_now < jd2 and jd_start is None:
      angam_now = NakshatraDivision(jd_now, ayanamsha_id=ayanamsha_id).get_anga(angam_type)

      if angam_now < target_anga_id or (target_anga_id == 1 and angam_now == num_angas):
        # So, jd_now will be lower than jd_start
        jd_bracket_L = jd_now
      if angam_now == target_anga_id:
        # In this branch, angam_now will have overshot the jd_start of the required interval.
        try:
          def f(x):
            return NakshatraDivision(x, ayanamsha_id=ayanamsha_id).get_anga_float(anga_type=angam_type,
                                                                                  offset_angas=-target_anga_id + 1,
                                                                                  debug=False)

          # noinspection PyTypeChecker
          jd_start = brentq(f, jd_bracket_L, jd_now)
          return jd_start
        except ValueError:
          logging.error('Unable to bracket %s->%f between jd = (%f, %f), starting with (%f, %f)' % (
            str(angam_type), -target_anga_id + 1, jd_bracket_L, jd_now, jd1, jd2))
          jd_start = None
      jd_now += min_step
    return jd_start

  @classmethod
  def _find_anga_end(cls, jd_start, jd2, angam_type, target_anga_id, ayanamsha_id):
    jd_end = None
    num_angas = int(360.0 / angam_type.arc_length)

    jd_bracket_R = jd2

    min_step = 0.5  # Min Step for moving
    jd_now = jd_start

    while jd_now < jd2 and jd_end is None:
      angam_now = NakshatraDivision(jd_now, ayanamsha_id=ayanamsha_id).get_anga(angam_type)

      if target_anga_id == num_angas:
        # Wait till we land at the next anga!
        if angam_now == 1:
          jd_bracket_R = jd_now
          break
      else:
        if angam_now > target_anga_id:
          jd_bracket_R = jd_now
          break
      jd_now += min_step

    try:
      def f(x):
        return NakshatraDivision(x, ayanamsha_id=ayanamsha_id).get_anga_float(anga_type=angam_type,
                                                                              offset_angas=-target_anga_id,
                                                                              debug=False)

      # noinspection PyTypeChecker
      jd_end = brentq(f, jd_start, jd_bracket_R)
    except ValueError:
      logging.error('Unable to compute anga_interval.jd_end (%s->%d); possibly could not bracket correctly!\n' % (
        str(angam_type), target_anga_id))
    return jd_end

  @classmethod
  def find(cls, jd1, jd2, angam_type, target_anga_id, ayanamsha_id, debug=False):
    """Computes angam spans for angams such as tithi, nakshatram, yoga
        and karanam.

        Args:
          :param jd1: return the first span that starts after this date
          :param jd2: return the first span that ends before this date
          :param angam_type: TITHI, NAKSHATRAM, YOGA, KARANAM, SOLAR_MONTH, SOLAR_NAKSH
          :param ayanamsha_id
          :param debug

        Returns:
          tuple: A tuple of start and end times that lies within jd1 and jd2
    """

    anga_interval = AngaSpan(None, None)

    anga_interval.jd_start = cls._find_anga_start_between(jd1=jd1, jd2=jd2, target_anga_id=target_anga_id,
                                                          angam_type=angam_type, ayanamsha_id=ayanamsha_id)

    if anga_interval.jd_start is None:
      return AngaSpan(None, None)  # If it doesn't start, we don't care if it ends!

    anga_interval.jd_end = cls._find_anga_end(jd_start=anga_interval.jd_start, jd2=jd2, target_anga_id=target_anga_id,
                                              angam_type=angam_type, ayanamsha_id=ayanamsha_id)

    if debug:
      logging.debug(('anga_interval.jd_end', anga_interval.jd_end))

    return anga_interval


if __name__ == '__main__':
  # lahiri_nakshatra_division = NakshatraDivision(julday=temporal.utc_to_jd(year=2017, month=8, day=19, hour=11, minutes=10, seconds=0, flag=1)[0])
  pass