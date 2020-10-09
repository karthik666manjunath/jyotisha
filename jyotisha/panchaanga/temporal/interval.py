import sys
from math import floor
from numbers import Number

from jyotisha.panchaanga.temporal.zodiac.angas import Anga
from sanskrit_data.schema import common


class BoundaryAngas(common.JsonObject):
  def __init__(self, start, end, interval=None):
    super(BoundaryAngas, self).__init__()
    self.start = start
    self.end = end
    self.interval = interval

  def to_tuple(self):
    return (None if self.start is None else self.start.index, None if self.end is None else self.end.index)


class Interval(common.JsonObject):
  def __init__(self, jd_start, jd_end, name=None):
    super(Interval, self).__init__()
    self.jd_start = jd_start
    self.jd_end = jd_end
    self.name = name

  def to_tuple(self):
    return (self.jd_start, self.jd_end)

  def __str__(self):
    from jyotisha.panchaanga.temporal import time
    return "%s: (%s, %s)" % ("" if self.name is None else self.name, time.ist_timezone.julian_day_to_local_time_str(jd=self.jd_start),
    time.ist_timezone.julian_day_to_local_time_str(jd=self.jd_end))

  def get_boundary_angas(self, anga_type, ayanaamsha_id):
    from jyotisha.panchaanga.temporal.zodiac import NakshatraDivision
    def f(x): 
      if x is None:
        return None
      else:
        return NakshatraDivision(x, ayanaamsha_id=ayanaamsha_id).get_anga(anga_type=anga_type)
    return BoundaryAngas(start=f(self.jd_start), end=f(self.jd_end), interval=self)


class AngaSpan(Interval):
  def __init__(self, jd_start, jd_end, anga):
    super(AngaSpan, self).__init__(jd_start=jd_start, jd_end=jd_end, name=None)
    self.anga = anga

  def __str__(self):
    return "%s - %s" % (str(self.anga),  super(AngaSpan, self).__str__())

class DayLengthBasedPeriods(common.JsonObject):
  def __init__(self, jd_previous_sunset, jd_sunrise, jd_sunset, jd_next_sunrise, weekday):
    # Compute the various day_length_based_periods
    # Sunrise/sunset and related stuff (like rahu, yama)
    if self.day_length_based_periods is not None:
      return self.day_length_based_periods

    YAMAGANDA_OCTETS = [4, 3, 2, 1, 0, 6, 5]
    RAHUKALA_OCTETS = [7, 1, 6, 4, 5, 3, 2]
    GULIKAKALA_OCTETS = [6, 5, 4, 3, 2, 1, 0]
    self.raahu = get_interval(jd_sunrise, jd_sunset,
                                       RAHUKALA_OCTETS[weekday], 8)
    self.yama = get_interval(jd_sunrise, jd_sunset,
                                      YAMAGANDA_OCTETS[weekday], 8)
    self.gulika = get_interval(jd_sunrise, jd_sunset,
                                        GULIKAKALA_OCTETS[weekday], 8)
    self.braahma = get_interval(jd_previous_sunset, jd_sunrise, 13, 15)
    self.praatas_sandhyaa = get_interval(jd_previous_sunset, jd_sunrise, 14, 15)
    self.praatas_sandhyaa_end = get_interval(jd_sunrise, jd_sunset, 4, 15)
    self.praatah = get_interval(jd_sunrise, jd_sunset, 0, 5)
    self.saangava = get_interval(jd_sunrise, jd_sunset, 1, 5)
    self.madhyaahna = get_interval(jd_sunrise, jd_sunset, 2, 5)
    self.maadhyaahnika_sandhyaa = get_interval(jd_sunrise, jd_sunset, 5, 15)
    self.maadhyaahnika_sandhyaa_end = get_interval(jd_sunrise, jd_sunset, 13, 15)
    self.aparaahna = get_interval(jd_sunrise, jd_sunset, 3, 5)
    self.saayaahna = get_interval(jd_sunrise, jd_sunset, 4, 5)
    self.saayam_sandhyaa = get_interval(jd_sunrise, jd_sunset, 14, 15)
    self.dinamaana = get_interval(jd_sunrise, jd_sunset, 1, 1)
    self.tb_muhuurtas = None

    self.raatrimaana = get_interval(jd_sunset, jd_next_sunrise, 1, 1)
    # pradOSo.astamayAdUrdhvaM ghaTikAdvayamiShyatE (tithyAdi tattvam, Vrat Parichay panchaanga. 25 Gita Press).
    self.pradosha = get_interval(jd_sunset, jd_next_sunrise, 1, 15)
    self.madhyaraatri = get_interval(jd_sunset, jd_next_sunrise, 2, 5)
    self.nishiitha = get_interval(jd_sunset, jd_next_sunrise, 7, 15)
    self.arunodaya = get_interval(jd_sunset, jd_next_sunrise, [13, 14], 15)
    self.raatri_yaama_1 = get_interval(jd_sunset, jd_next_sunrise, 1, 4)
    self.shayana = get_interval(jd_sunset, jd_next_sunrise, 3, 8)
    self.dinaanta = get_interval(jd_sunset, jd_next_sunrise, 5, 8)

    for attr_name, obj in self.__dict__.items():
      if isinstance(obj, Interval):
        obj.name = attr_name


class TbSayanaMuhuurta(Interval):
  """ A muhUrta as defined by SayaNa's commentary to TB 5.3
  
  Refer https://archive.org/stream/Anandashram_Samskrita_Granthavali_Anandashram_Sanskrit_Series/ASS_037_Taittiriya_Brahmanam_with_Sayanabhashya_Part_1_-_Narayanasastri_Godbole_1934#page/n239/mode/2up .
  """

  def __init__(self, jd_start, jd_end, muhuurta_id):
    super().__init__(jd_start=jd_start, jd_end=jd_end, name=muhuurta_id)
    self.muhuurta_id = muhuurta_id
    self.ahna = floor(self.muhuurta_id / 3)
    self.ahna_part = self.muhuurta_id % 3
    self.is_nirviirya = self.muhuurta_id in (2, 3, 5, 6, 8, 9, 11, 12)

  def to_localized_string(self, city):
    from jyotisha.panchaanga.temporal.time import Timezone
    return "muhUrta %d (nirvIrya: %s) starts from %s to %s" % (self.muhuurta_id, str(self.is_nirviirya),
                                                               Timezone(city.timezone).julian_day_to_local_time(
                                                                 julian_day=self.jd_start, round_seconds=True),
                                                               Timezone(city.timezone).julian_day_to_local_time(
                                                                 julian_day=self.jd_end, round_seconds=True))


def get_interval(start_jd, end_jd, part_index, num_parts, name=None):
  """Get start and end time of a given interval in a given span with specified fractions

  Args:
    :param start_jd float (jd)
    :param end_jd float (jd)
    :param part_index int, minimum/ start value 0. Or an array of those.
    :param num_parts

  Returns:
     tuple (start_time_jd, end_time_jd)

  Examples:

  """
  if isinstance(part_index, Number):
    part_index = [part_index]
  start_fraction = min(part_index) / float(num_parts)
  end_fraction = (max(part_index) + 1) / float(num_parts)

  start_time = start_jd + (end_jd - start_jd) * start_fraction
  end_time = start_jd + (end_jd - start_jd) * end_fraction

  return Interval(jd_start=start_time, jd_end=end_time, name=name)


# Essential for depickling to work.
common.update_json_class_index(sys.modules[__name__])
