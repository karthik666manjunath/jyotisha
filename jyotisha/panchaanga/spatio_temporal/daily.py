#!/usr/bin/python3
#  -*- coding: utf-8 -*-
import logging
import sys
from math import floor, modf

from jyotisha.panchaanga.temporal.festival import rules, FestivalInstance
from jyotisha.panchaanga.temporal.zodiac import angas, AngaSpanFinder
from scipy.optimize import brentq

from jyotisha.panchaanga.spatio_temporal import City
from jyotisha.panchaanga.temporal import interval, time, ComputationSystem, set_constants
from jyotisha.panchaanga.temporal import zodiac
from jyotisha.panchaanga.temporal.body import Graha
from jyotisha.panchaanga.temporal.interval import Interval, DayLengthBasedPeriods, AngaSpan
from jyotisha.panchaanga.temporal.month import LunarMonthAssigner
from jyotisha.panchaanga.temporal.time import Timezone, Hour, Date
from jyotisha.panchaanga.temporal.zodiac import Ayanamsha, NakshatraDivision
from jyotisha.panchaanga.temporal.zodiac.angas import AngaType
from jyotisha.util import zero_if_none, default_if_none
from sanskrit_data.schema import common

logging.basicConfig(level=logging.DEBUG,
                    format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s ")


set_constants()



class DayAngas(common.JsonObject):
  def __init__(self):
    self.tithis_with_ends = None
    self.tithi_at_sunrise = None
    self.nakshatras_with_ends = None
    self.nakshatra_at_sunrise = None
    self.yogas_with_ends = None
    self.yoga_at_sunrise = None
    self.karanas_with_ends = None
    self.raashis_with_ends = None

  def get_angas_with_ends(self, anga_type):
    anga_spans = []
    if anga_type == AngaType.NAKSHATRA:
      anga_spans = self.nakshatras_with_ends
    elif anga_type == AngaType.TITHI:
      anga_spans = self.tithis_with_ends
    elif anga_type == AngaType.YOGA:
      anga_spans = self.yogas_with_ends
    elif anga_type == AngaType.RASHI:
      anga_spans = self.rashis_with_ends
    elif anga_type == AngaType.KARANA:
      anga_spans = self.karanas_with_ends
    return anga_spans

  def find_anga(self, anga_type, anga_id):
    for anga_span in self.get_angas_with_ends(anga_type=anga_type):
      if anga_span.anga == anga_id:
        return anga_span.anga
    return None


# This class is not named Panchangam in order to be able to disambiguate from annual.Panchangam in serialized objects.
class DailyPanchaanga(common.JsonObject):
  """This class enables the construction of a panchaanga
    """

  @classmethod
  def from_city_and_julian_day(cls, city, julian_day, computation_system: ComputationSystem = ComputationSystem.MULTI_NEW_MOON_SOLAR_MONTH_ADHIKA__CHITRA_180):
    date = Timezone(city.timezone).julian_day_to_local_time(julian_day)
    return DailyPanchaanga(city=city, date=date, computation_system=computation_system)

  def __init__(self, city: City, date: Date, computation_system = ComputationSystem.MULTI_NEW_MOON_SOLAR_MONTH_ADHIKA__CHITRA_180,
               previous_day_panchaanga=None) -> None:
    """Constructor for the panchaanga.
    """
    super(DailyPanchaanga, self).__init__()
    self.city = city
    self.date = date
    date.set_time_to_day_start()
    self.julian_day_start = Timezone(self.city.timezone).local_time_to_julian_day(date=self.date)
    self.computation_system = computation_system

    self.jd_sunrise = None
    self.jd_sunset = None
    self.jd_previous_sunset = None
    self.jd_next_sunrise = None
    self.jd_moonrise = None
    self.jd_moonset = None

    self.lagna_data = None
    self.sunrise_day_angas = None

    self.solar_sidereal_date_sunset = None

    self.tropical_date_sunset = None

    self.lunar_month_sunrise = None

    
    self.shraaddha_tithi = []
    self.festival_id_to_instance = {}

    self.compute_sun_moon_transitions(previous_day_panchaanga=previous_day_panchaanga)
    self.compute_solar_day_sunset(previous_day_panchaanga=previous_day_panchaanga)
    self.set_tropical_date_sunset(previous_day_panchaanga=previous_day_panchaanga)
    self.day_length_based_periods = DayLengthBasedPeriods(jd_previous_sunset=self.jd_previous_sunset, jd_sunrise=self.jd_sunrise, jd_sunset=self.jd_sunset, jd_next_sunrise=self.jd_next_sunrise, weekday=self.date.get_weekday())

    if computation_system.lunar_month_assigner_type is not None:
      lunar_month_assigner = LunarMonthAssigner.get_assigner(computation_system=computation_system)
      self.set_lunar_month_sunrise(month_assigner=lunar_month_assigner, previous_day_panchaanga=previous_day_panchaanga)


  def __lt__(self, other):
    return self.date.get_date_str() < self.date.get_date_str()

  def compute_sun_moon_transitions(self, previous_day_panchaanga=None, force_recomputation=False):
    """

    :param previous_day_panchaanga: Panchangam for previous day, to avoid unnecessary calculations. (rise_trans calculations can be time consuming.)
    :param force_recomputation: Boolean indicating if the transitions should be recomputed. (rise_trans calculations can be time consuming.)
    :return:
    """
    if force_recomputation or self.jd_sunrise is None:
      if previous_day_panchaanga is not None and previous_day_panchaanga.jd_next_sunrise is not None:
        self.jd_sunrise = previous_day_panchaanga.jd_next_sunrise
      else:
        self.jd_sunrise = self.city.get_rising_time(julian_day_start=self.julian_day_start, body=Graha.SUN)
    if force_recomputation or self.jd_sunset is None:
      self.jd_sunset = self.city.get_setting_time(julian_day_start=self.jd_sunrise, body=Graha.SUN)
    if force_recomputation or self.jd_previous_sunset is None:
      if previous_day_panchaanga is not None and previous_day_panchaanga.jd_sunset is not None:
        self.jd_previous_sunset = previous_day_panchaanga.jd_sunset
      else:
        self.jd_previous_sunset = self.city.get_setting_time(julian_day_start=self.jd_sunrise - 1,
                                                             body=Graha.SUN)
    if force_recomputation or self.jd_next_sunrise is None:
      self.jd_next_sunrise = self.city.get_rising_time(julian_day_start=self.jd_sunset, body=Graha.SUN)
    if self.jd_sunset == 0.0:
      logging.error('No sunset was computed!')
      raise (ValueError(
        'No sunset was computed. Perhaps the co-ordinates are beyond the polar circle (most likely a LAT-LONG swap! Please check your inputs.'))

    if force_recomputation or self.jd_moonrise is None:
      self.jd_moonrise = self.city.get_rising_time(julian_day_start=self.jd_sunrise, body=Graha.MOON)
    if force_recomputation or self.jd_moonset is None:
      self.jd_moonset = self.city.get_setting_time(julian_day_start=self.jd_sunrise, body=Graha.MOON)

    if force_recomputation or self.sunrise_day_angas is None:
      self.sunrise_day_angas = DayAngas()
      # Deliberately passing ASHVINI_STARTING_0 below since it is cheapest. Tithi is independent of ayanAmsha. 
      self.sunrise_day_angas.tithis_with_ends = AngaSpanFinder.get_cached(ayanaamsha_id=Ayanamsha.ASHVINI_STARTING_0, anga_type=zodiac.AngaType.TITHI).get_all_angas_in_period(jd1=self.jd_sunrise, jd2=self.jd_next_sunrise)
      self.sunrise_day_angas.tithi_at_sunrise = self.sunrise_day_angas.tithis_with_ends[0].anga
      
      self.sunrise_day_angas.nakshatras_with_ends = AngaSpanFinder.get_cached(ayanaamsha_id=self.computation_system.ayanaamsha_id, anga_type=zodiac.AngaType.NAKSHATRA).get_all_angas_in_period(jd1=self.jd_sunrise, jd2=self.jd_next_sunrise)
      self.sunrise_day_angas.nakshatra_at_sunrise = self.sunrise_day_angas.nakshatras_with_ends[0].anga
      
      self.sunrise_day_angas.yogas_with_ends = AngaSpanFinder.get_cached(ayanaamsha_id=self.computation_system.ayanaamsha_id, anga_type=zodiac.AngaType.YOGA).get_all_angas_in_period(jd1=self.jd_sunrise, jd2=self.jd_next_sunrise)
      self.sunrise_day_angas.yoga_at_sunrise = self.sunrise_day_angas.yogas_with_ends[0].anga
      
      self.sunrise_day_angas.karanas_with_ends = AngaSpanFinder.get_cached(ayanaamsha_id=self.computation_system.ayanaamsha_id, anga_type=zodiac.AngaType.KARANA).get_all_angas_in_period(jd1=self.jd_sunrise, jd2=self.jd_next_sunrise)
      
      self.sunrise_day_angas.raashis_with_ends = AngaSpanFinder.get_cached(ayanaamsha_id=self.computation_system.ayanaamsha_id, anga_type=zodiac.AngaType.RASHI).get_all_angas_in_period(jd1=self.jd_sunrise, jd2=self.jd_next_sunrise)

  def compute_tb_muhuurtas(self):
    """ Computes muhuurta-s according to taittiriiya brAhmaNa.
    """
    if getattr(self, "jd_sunrise", None) is None:
      self.compute_sun_moon_transitions()
    tb_muhuurtas = []
    for muhuurta_id in range(0, 15):
      (jd_start, jd_end) = interval.get_interval(start_jd=self.jd_sunrise, end_jd=self.jd_sunset,
                                                                              part_index=muhuurta_id, num_parts=15).to_tuple()
      from jyotisha.panchaanga.temporal.interval import TbSayanaMuhuurta
      tb_muhuurtas.append(TbSayanaMuhuurta(
        jd_start=jd_start, jd_end=jd_end,
        muhuurta_id=muhuurta_id))
    self.day_length_based_periods.tb_muhuurtas = tb_muhuurtas

  def compute_solar_day_sunset(self, previous_day_panchaanga=None):
    """Compute the solar month and day for a given Julian day at sunset.
    """
    # If solar transition happens before the current sunset but after the previous sunset, then that is taken to be solar day 1.
    self.compute_sun_moon_transitions(previous_day_panchaanga=previous_day_panchaanga)
    solar_month_sunset = NakshatraDivision(jd=self.jd_sunset, ayanaamsha_id=self.computation_system.ayanaamsha_id).get_anga(
      anga_type=AngaType.SIDEREAL_MONTH)

    solar_sidereal_month_end_jd = None
    if previous_day_panchaanga is None or previous_day_panchaanga.solar_sidereal_date_sunset.day > 28 :
      anga_finder = zodiac.AngaSpanFinder(ayanaamsha_id=self.computation_system.ayanaamsha_id)
      solar_month_sunset_span = anga_finder.find(jd1=self.jd_sunset - 32, jd2=self.jd_sunset + 5, target_anga_in=solar_month_sunset)
      solar_sidereal_month_day_sunset = len(self.city.get_sunsets_in_period(jd_start=solar_month_sunset_span.jd_start, jd_end=self.jd_sunset + 1/48.0))
      if solar_sidereal_month_day_sunset == 1 and solar_month_sunset_span.jd_start > self.jd_sunrise:
        solar_sidereal_month_end_jd = solar_month_sunset_span.jd_start
      elif solar_sidereal_month_day_sunset == 30 and solar_month_sunset_span.jd_end < self.jd_next_sunrise:
        solar_sidereal_month_end_jd = solar_month_sunset_span.jd_end
    else:
      solar_sidereal_month_day_sunset = previous_day_panchaanga.solar_sidereal_date_sunset.day + 1
    from jyotisha.panchaanga.temporal import time
    self.solar_sidereal_date_sunset = time.BasicDateWithTransitions(month=solar_month_sunset.index, day=solar_sidereal_month_day_sunset, month_transition=solar_sidereal_month_end_jd)

  def set_tropical_date_sunset(self, previous_day_panchaanga=None):
    month_transition_jd = None
    if previous_day_panchaanga is not None:
      tropical_date_sunset_day = previous_day_panchaanga.tropical_date_sunset.day + 1
      tropical_date_sunset_month = previous_day_panchaanga.tropical_date_sunset.month
    
    if previous_day_panchaanga is None or previous_day_panchaanga.tropical_date_sunset.day > 28 :
      nd = zodiac.NakshatraDivision(jd=self.jd_sunset, ayanaamsha_id=Ayanamsha.ASHVINI_STARTING_0)
      fractional_month = nd.get_fractional_division_for_body(body=Graha.singleton(Graha.SUN), anga_type=AngaType.RASHI)
      (month_fraction, _) = modf(fractional_month)
      approx_day = month_fraction*30
      month_transitions = Graha.singleton(Graha.SUN).get_transits(jd_start=self.jd_sunset-approx_day-5, jd_end=self.jd_sunset + 4, anga_type=AngaType.RASHI, ayanaamsha_id=Ayanamsha.ASHVINI_STARTING_0)
      if month_transitions[-1].jd > self.jd_previous_sunset and month_transitions[-1].jd <= self.jd_sunset:
        tropical_date_sunset_day = 1
        tropical_date_sunset_month = month_transitions[-1].value_2
      else:
        tropical_date_sunset_day = len(self.city.get_sunsets_in_period(jd_start=month_transitions[0].jd, jd_end=self.jd_sunset + 1/48.0))
        tropical_date_sunset_month = month_transitions[0].value_2
    self.tropical_date_sunset = time.BasicDateWithTransitions(month=tropical_date_sunset_month, day=tropical_date_sunset_day, month_transition=month_transition_jd)

  def set_lunar_month_sunrise(self, month_assigner, previous_day_panchaanga=None):
    if previous_day_panchaanga is not None:
      tithi_1 = previous_day_panchaanga.sunrise_day_angas.find_anga(anga_type=AngaType.TITHI, anga_id=1)
      if tithi_1 is not None or self.sunrise_day_angas.tithi_at_sunrise == 1:
        self.lunar_month_sunrise = month_assigner.get_month_sunrise(daily_panchaanga=self)
      else:
        self.lunar_month_sunrise = previous_day_panchaanga.lunar_month_sunrise
    else:
      if  month_assigner is not None:
        self.lunar_month_sunrise = month_assigner.get_month_sunrise(daily_panchaanga=self)
    

  def get_lagna_data(self, ayanaamsha_id=zodiac.Ayanamsha.CHITRA_AT_180, debug=False):
    """Returns the lagna data

        Args:
          debug

        Returns:
          tuples detailing the end time of each lagna, beginning with the one
          prevailing at sunrise
        """
    if self.lagna_data is not None:
      return self.lagna_data

    self.lagna_data = []
    if getattr(self, "jd_sunrise", None) is None or self.jd_sunrise is None:
      self.compute_sun_moon_transitions()
    lagna_sunrise = 1 + floor(self.city.get_lagna_float(self.jd_sunrise, ayanaamsha_id=ayanaamsha_id))

    lagna_list = [(x + lagna_sunrise - 1) % 12 + 1 for x in range(13)]

    lbrack = self.jd_sunrise - 3 / 24
    rbrack = self.jd_sunrise + 3 / 24

    for lagna in lagna_list:
      # print('---\n', lagna)
      if (debug):
        logging.debug(('lagna sunrise', self.city.get_lagna_float(self.jd_sunrise, ayanaamsha_id=ayanaamsha_id)))
        logging.debug(('lbrack', self.city.get_lagna_float(lbrack, int(-lagna), ayanaamsha_id=ayanaamsha_id)))
        logging.debug(('rbrack', self.city.get_lagna_float(rbrack, int(-lagna), ayanaamsha_id=ayanaamsha_id)))

      lagna_end_time = brentq(self.city.get_lagna_float, lbrack, rbrack,
                              args=(-lagna, ayanaamsha_id, debug))
      lbrack = lagna_end_time + 1 / 24
      rbrack = lagna_end_time + 3 / 24
      if lagna_end_time < self.jd_next_sunrise:
        self.lagna_data.append((lagna, lagna_end_time))
    return self.lagna_data

  def assign_festivals(self, previous_day_panchaanga, no_next_day_lookup=True):
    return # Disable for now.
    if previous_day_panchaanga is None:
      return
    rule_set = rules.RulesCollection.get_cached(repos=tuple(self.computation_system.options.fest_repos))
    
    # Assign sunrise solar sidereal day fests. Current day's sunset solar month and day will generally hold at sunrise.
    fest_dict = rule_set.get_month_anga_fests(month=self.solar_sidereal_date_sunset.month, anga=self.solar_sidereal_date_sunset.day, month_type=rules.RulesRepo.SIDEREAL_SOLAR_MONTH_DIR, anga_type_id=rules.RulesRepo.DAY_DIR)
    for fest_id, fest in fest_dict.items():
      kaala = fest.timing.get_kaala()
      if kaala == "sunrise":
        self.festival_id_to_instance[fest_id] = FestivalInstance(name=fest.id)
      elif kaala == "arunodaya":
        pass # Handled separately
      else:
        raise ValueError("%s %s " % (fest_id, kaala))

    # Assign aruNodaya solar sidereal day fests. Previous day's sunset solar month and day will generally hold.
    fest_dict = rule_set.get_month_anga_fests(month=previous_day_panchaanga.solar_sidereal_date_sunset.month, anga=previous_day_panchaanga.solar_sidereal_date_sunset.day, month_type=rules.RulesRepo.SIDEREAL_SOLAR_MONTH_DIR, anga_type_id=rules.RulesRepo.DAY_DIR)
    for fest_id, fest in fest_dict.items():
      kaala = fest.timing.get_kaala()
      if kaala == "sunrise":
        pass # Handled separately
      elif kaala == "arunodaya":
        self.festival_id_to_instance[fest_id] = FestivalInstance(name=fest.id)
      else:
        raise ValueError("Unhandled - %s %s " % (fest_id, kaala))

    return
    fest_dict = rule_set.get_month_anga_fests(month=self.solar_sidereal_date_sunset.month, anga=self.sunrise_day_angas.tithi_at_sunrise.index, month_type=rules.RulesRepo.SIDEREAL_SOLAR_MONTH_DIR, anga_type_id=rules.RulesRepo.TITHI_DIR)
    for fest_id, fest in fest_dict.items():
      if fest.timing.get_kaala() == "sunrise" and fest.timing.get_priority() == "puurvaviddha" and fest_id not in previous_day_panchaanga.festival_id_to_instance:
        self.festival_id_to_instance[fest_id] = FestivalInstance(name=fest.id)

    non_sunrise_tithis = [x.anga for x in self.sunrise_day_angas.tithis_with_ends if zero_if_none(x.jd_start) > self.jd_sunrise and default_if_none(x.jd_end, self.jd_next_sunrise) < self.jd_next_sunrise]
    for non_sunrise_tithi in non_sunrise_tithis:
      fest_dict = rule_set.get_month_anga_fests(month=self.solar_sidereal_date_sunset.month, anga=non_sunrise_tithi.index, month_type=rules.RulesRepo.SIDEREAL_SOLAR_MONTH_DIR, anga_type_id=rules.RulesRepo.TITHI_DIR)
      for fest_id, fest in fest_dict.items():
        if fest.timing.get_kaala() == "sunrise" and fest.timing.get_priority() == "puurvaviddha":
          self.festival_id_to_instance[fest_id] = FestivalInstance(name=fest.id)
    return


  # Essential for depickling to work.
common.update_json_class_index(sys.modules[__name__])
# logging.debug(common.json_class_index)


if __name__ == '__main__':
  panchaanga = DailyPanchaanga.from_city_and_julian_day(city=City('Chennai', '13:05:24', '80:16:12', 'Asia/Calcutta'),
                                                        julian_day=2457023.27)
  panchaanga.compute_tb_muhuurtas()
  logging.debug(str(panchaanga))
