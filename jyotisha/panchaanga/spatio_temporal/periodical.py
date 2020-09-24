import logging
import os
import sys
import traceback
from typing import List

from indic_transliteration import xsanscript as sanscript

from jyotisha.panchaanga import spatio_temporal
from jyotisha.panchaanga.spatio_temporal import daily
from jyotisha.panchaanga.temporal import zodiac, time
from jyotisha.panchaanga.temporal.body import Graha
from jyotisha.panchaanga.temporal.month import LunarMonthAssigner
from jyotisha.panchaanga.temporal.tithi import TithiAssigner
from jyotisha.panchaanga.temporal.zodiac import NakshatraDivision
from sanskrit_data.schema import common
from sanskrit_data.schema.common import JsonObject


class Panchaanga(common.JsonObject):
  """This class enables the construction of a panchaanga for arbitrary periods, with festivals.
    """
  LATEST_VERSION = "0.0.3"

  def __init__(self, city, start_date, end_date, lunar_month_assigner_type=LunarMonthAssigner.SIDERIAL_SOLAR_BASED,
               script=sanscript.DEVANAGARI, fmt='hh:mm',
               ayanamsha_id=zodiac.Ayanamsha.CHITRA_AT_180,
               compute_lagnas=False):
    """Constructor for the panchaanga.
        """
    super(Panchaanga, self).__init__()
    self.version = Panchaanga.LATEST_VERSION
    self.city = city
    self.start_date = tuple([int(x) for x in start_date.split('-')])  # (tuple of (yyyy, mm, dd))
    self.end_date = tuple([int(x) for x in end_date.split('-')])  # (tuple of (yyyy, mm, dd))
    self.script = script
    self.fmt = fmt

    self.jd_start = time.utc_gregorian_to_jd(self.start_date[0], self.start_date[1], self.start_date[2], 0)
    self.jd_end = time.utc_gregorian_to_jd(self.end_date[0], self.end_date[1], self.end_date[2], 0)

    self.duration = int(self.jd_end - self.jd_start) + 1

    # some buffer, for various look-ahead calculations
    # Pushkaram starting on 31 Jan might not get over till 12 days later
    self.duration_to_calculate = int(self.duration + 16)  

    self.weekday_start = time.get_weekday(self.jd_start)
    self.ayanamsha_id = ayanamsha_id

    self.compute_angas(compute_lagnas=compute_lagnas)
    lunar_month_assigner = LunarMonthAssigner.get_assigner(assigner_id=lunar_month_assigner_type, panchaanga=self)
    lunar_month_assigner.assign()

  def compute_angas(self, compute_lagnas=True):
    """Compute the entire panchaanga
    """

    nDays = self.duration_to_calculate

    # INITIALISE VARIABLES
    self.solar_month_end_time = [None] * nDays
    self.solar_month_day = [None] * nDays
    self.tropical_month = [None] * nDays
    self.tropical_month_end_time = [None] * nDays

    self.lunar_month = [None] * nDays

    self.daily_panchaangas: List[daily.DailyPanchanga] = [None] * nDays

    # Computing solar month details for Dec 31
    # rather than Jan 1, since we have an always increment
    # solar_month_day at the start of the loop across every day in
    # year
    [prev_day_yy, prev_day_mm, prev_day_dd] = time.jd_to_utc_gregorian(self.jd_start - 1).to_date_fractional_hour_tuple()[:3]
    daily_panchaanga_start = daily.DailyPanchanga(city=self.city, date=time.Date(year=prev_day_yy, month=prev_day_mm,
                                                                       day=prev_day_dd), ayanamsha_id=self.ayanamsha_id)
    daily_panchaanga_start.compute_solar_day()
    solar_month_day = daily_panchaanga_start.solar_month_day

    solar_month_today_sunset = NakshatraDivision(daily_panchaanga_start.jd_sunset,
                                                 ayanamsha_id=self.ayanamsha_id).get_anga(
      zodiac.AngaType.SOLAR_MONTH)
    solar_month_tmrw_sunrise = NakshatraDivision(daily_panchaanga_start.jd_sunrise + 1,
                                                 ayanamsha_id=self.ayanamsha_id).get_anga(
      zodiac.AngaType.SOLAR_MONTH)
    month_start_after_sunset = solar_month_today_sunset != solar_month_tmrw_sunrise

    #############################################################
    # Compute all parameters -- sun/moon latitude/longitude etc #
    #############################################################

    for d in range(-1, nDays - 1):
      # TODO: Eventually, we are shifting to an array of daily panchangas. Reason: Better modularity.
      # The below block is temporary code to make the transition seamless.
      (year_d, month_d, day_d, _) = time.jd_to_utc_gregorian(self.jd_start + d).to_date_fractional_hour_tuple()
      self.daily_panchaangas[d + 1] = daily.DailyPanchanga(city=self.city, date=time.Date(year=year_d, month=month_d, day=day_d),
                                                           ayanamsha_id=self.ayanamsha_id,
                                                           previous_day_panchaanga=self.daily_panchaangas[d])
      self.daily_panchaangas[d + 1].compute_sun_moon_transitions(previous_day_panchaanga=self.daily_panchaangas[d])
      self.daily_panchaangas[d + 1].compute_solar_month()

      if (d <= 0):
        continue
        # This is just to initialise, since for a lot of calculations,
        # we require comparing with tomorrow's data. This computes the
        # data for day 0, -1.

      # Solar month calculations
      if month_start_after_sunset is True:
        solar_month_day = 0
        month_start_after_sunset = False

      solar_month_end_jd = None
      if self.daily_panchaangas[d].solar_month_sunset != self.daily_panchaangas[d + 1].solar_month_sunset:
        solar_month_day = solar_month_day + 1
        if self.daily_panchaangas[d].solar_month_sunset != self.daily_panchaangas[d + 1].solar_month_sunrise:
          month_start_after_sunset = True
          [_m, solar_month_end_jd] = zodiac.get_angam_data(
            self.daily_panchaangas[d].jd_sunrise, self.daily_panchaangas[d + 1].jd_sunrise, zodiac.AngaType.SOLAR_MONTH,
            ayanamsha_id=self.ayanamsha_id)[
            0]
      elif self.daily_panchaangas[d].solar_month_sunrise != self.daily_panchaangas[d].solar_month_sunset:
        # sankrAnti!
        # sun moves into next rAshi before sunset
        solar_month_day = 1
        [_m, solar_month_end_jd] = zodiac.get_angam_data(
          self.daily_panchaangas[d].jd_sunrise, self.daily_panchaangas[d + 1].jd_sunrise, zodiac.AngaType.SOLAR_MONTH,
          ayanamsha_id=self.ayanamsha_id)[0]
      else:
        solar_month_day = solar_month_day + 1
        solar_month_end_jd = None

      self.solar_month_end_time[d] = solar_month_end_jd

      self.solar_month_day[d] = solar_month_day

      # Compute all the anga datas
      self.daily_panchaangas[d].get_kaalas()
      if compute_lagnas:
        self.daily_panchaangas[d].get_lagna_data()

  def get_angas_for_interval_boundaries(self, d, get_anga_func, interval_type):
    jd_sunrise = self.daily_panchaangas[d].jd_sunrise
    jd_sunrise_tmrw = self.daily_panchaangas[d + 1].jd_sunrise
    jd_sunrise_datmrw = self.daily_panchaangas[d + 2].jd_sunrise
    jd_sunset = self.daily_panchaangas[d].jd_sunset
    jd_sunset_tmrw = self.daily_panchaangas[d + 1].jd_sunset
    jd_moonrise = self.daily_panchaangas[d].jd_moonrise
    jd_moonrise_tmrw = self.daily_panchaangas[d + 1].jd_moonrise
    if interval_type == 'sunrise':
      angas = [get_anga_func(jd_sunrise),
               get_anga_func(jd_sunrise),
               get_anga_func(jd_sunrise_tmrw),
               get_anga_func(jd_sunrise_tmrw)]
    elif interval_type == 'sunset':
      angas = [get_anga_func(jd_sunset),
               get_anga_func(jd_sunset),
               get_anga_func(jd_sunset_tmrw),
               get_anga_func(jd_sunset_tmrw)]
    elif interval_type == 'praatah':
      angas = [get_anga_func(jd_sunrise),  # praatah1 start
               # praatah1 end
               get_anga_func(jd_sunrise + (jd_sunset - jd_sunrise) * (1.0 / 5.0)),
               get_anga_func(jd_sunrise_tmrw),  # praatah2 start
               # praatah2 end
               get_anga_func(jd_sunrise_tmrw + \
                             (jd_sunset_tmrw - jd_sunrise_tmrw) * (1.0 / 5.0))]
    elif interval_type == 'sangava':
      angas = [
        get_anga_func(jd_sunrise + (jd_sunset - jd_sunrise) * (1.0 / 5.0)),
        get_anga_func(jd_sunrise + (jd_sunset - jd_sunrise) * (2.0 / 5.0)),
        get_anga_func(jd_sunrise_tmrw +
                      (jd_sunset_tmrw - jd_sunrise_tmrw) * (1.0 / 5.0)),
        get_anga_func(jd_sunrise_tmrw +
                      (jd_sunset_tmrw - jd_sunrise_tmrw) * (2.0 / 5.0))]
    elif interval_type == 'madhyaahna':
      angas = [
        get_anga_func(jd_sunrise + (jd_sunset - jd_sunrise) * (2.0 / 5.0)),
        get_anga_func(jd_sunrise + (jd_sunset - jd_sunrise) * (3.0 / 5.0)),
        get_anga_func(jd_sunrise_tmrw +
                      (jd_sunset_tmrw - jd_sunrise_tmrw) * (2.0 / 5.0)),
        get_anga_func(jd_sunrise_tmrw + (jd_sunset_tmrw -
                                         jd_sunrise_tmrw) * (3.0 / 5.0))]
    elif interval_type == 'aparaahna':
      angas = [
        get_anga_func(jd_sunrise + (jd_sunset - jd_sunrise) * (3.0 / 5.0)),
        get_anga_func(jd_sunrise + (jd_sunset - jd_sunrise) * (4.0 / 5.0)),
        get_anga_func(jd_sunrise_tmrw +
                      (jd_sunset_tmrw - jd_sunrise_tmrw) * (3.0 / 5.0)),
        get_anga_func(jd_sunrise_tmrw +
                      (jd_sunset_tmrw - jd_sunrise_tmrw) * (4.0 / 5.0))]
    elif interval_type == 'saayaahna':
      angas = [
        get_anga_func(jd_sunrise + (jd_sunset - jd_sunrise) * (4.0 / 5.0)),
        get_anga_func(jd_sunrise + (jd_sunset - jd_sunrise) * (5.0 / 5.0)),
        get_anga_func(jd_sunrise_tmrw +
                      (jd_sunset_tmrw - jd_sunrise_tmrw) * (4.0 / 5.0)),
        get_anga_func(jd_sunrise_tmrw +
                      (jd_sunset_tmrw - jd_sunrise_tmrw) * (5.0 / 5.0))]
    elif interval_type == 'madhyaraatri':
      angas = [
        get_anga_func(jd_sunset + (jd_sunrise_tmrw - jd_sunset) * (2.0 / 5.0)),
        get_anga_func(jd_sunset + (jd_sunrise_tmrw - jd_sunset) * (3.0 / 5.0)),
        get_anga_func(jd_sunset_tmrw +
                      (jd_sunrise_datmrw - jd_sunset_tmrw) * (2.0 / 5.0)),
        get_anga_func(jd_sunset_tmrw +
                      (jd_sunrise_datmrw - jd_sunset_tmrw) * (3.0 / 5.0))]
    elif interval_type == 'pradosha':
      # pradOSo.astamayAdUrdhvaM ghaTikAdvayamiShyatE (tithyAdi tattvam, Vrat Parichay p. 25 Gita Press)
      angas = [get_anga_func(jd_sunset),
               get_anga_func(jd_sunset + (jd_sunrise_tmrw - jd_sunset) * (1.0 / 15.0)),
               get_anga_func(jd_sunset_tmrw),
               get_anga_func(jd_sunset_tmrw +
                             (jd_sunrise_datmrw - jd_sunset_tmrw) * (1.0 / 15.0))]
    elif interval_type == 'nishita':
      angas = [
        get_anga_func(jd_sunset + (jd_sunrise_tmrw - jd_sunset) * (7.0 / 15.0)),
        get_anga_func(jd_sunset + (jd_sunrise_tmrw - jd_sunset) * (8.0 / 15.0)),
        get_anga_func(jd_sunset_tmrw +
                      (jd_sunrise_datmrw - jd_sunset_tmrw) * (7.0 / 15.0)),
        get_anga_func(jd_sunset_tmrw +
                      (jd_sunrise_datmrw - jd_sunset_tmrw) * (8.0 / 15.0))]
    elif interval_type == 'dinamaana':
      angas = [
        get_anga_func(jd_sunrise + (jd_sunset - jd_sunrise) * (0.0 / 5.0)),
        get_anga_func(jd_sunrise + (jd_sunset - jd_sunrise) * (5.0 / 5.0)),
        get_anga_func(jd_sunrise_tmrw +
                      (jd_sunset_tmrw - jd_sunrise_tmrw) * (0.0 / 5.0)),
        get_anga_func(jd_sunrise_tmrw + (jd_sunset_tmrw -
                                         jd_sunrise_tmrw) * (5.0 / 5.0))]
    elif interval_type == 'raatrimaana':
      angas = [
        get_anga_func(jd_sunset + (jd_sunrise_tmrw - jd_sunset) * (0.0 / 15.0)),
        get_anga_func(jd_sunset + (jd_sunrise_tmrw - jd_sunset) * (15.0 / 15.0)),
        get_anga_func(jd_sunset_tmrw +
                      (jd_sunrise_datmrw - jd_sunset_tmrw) * (0.0 / 15.0)),
        get_anga_func(jd_sunset_tmrw +
                      (jd_sunrise_datmrw - jd_sunset_tmrw) * (15.0 / 15.0))]
    elif interval_type == 'arunodaya':
      # deliberately not simplifying expressions involving 15/15
      angas = [
        get_anga_func(jd_sunset + (jd_sunrise_tmrw - jd_sunset) * (13.0 / 15.0)),
        get_anga_func(jd_sunset + (jd_sunrise_tmrw - jd_sunset) * (15.0 / 15.0)),
        get_anga_func(jd_sunset_tmrw +
                      (jd_sunrise_datmrw - jd_sunset_tmrw) * (13.0 / 15.0)),
        get_anga_func(jd_sunset_tmrw +
                      (jd_sunrise_datmrw - jd_sunset_tmrw) * (15.0 / 15.0))]
    elif interval_type == 'moonrise':
      angas = [get_anga_func(jd_moonrise),
               get_anga_func(jd_moonrise),
               get_anga_func(jd_moonrise_tmrw),
               get_anga_func(jd_moonrise_tmrw)]
    else:
      # Error!
      raise ValueError('Unkown kaala "%s" input!' % interval_type)
    return angas

  def write_debug_log(self):
    log_file = open('cal-%4d-%s-log.txt' % (self.year, self.city.name), 'w')
    for d in range(1, self.duration_to_calculate - 1):
      jd = self.jd_start - 1 + d
      [y, m, dt, t] = time.jd_to_utc_gregorian(jd).to_date_fractional_hour_tuple()
      longitude_sun_sunset = Graha.singleton(Graha.SUN).get_longitude(
        self.daily_panchaangas[d].jd_sunset) - zodiac.Ayanamsha.singleton(
        self.ayanamsha_id).get_offset(self.daily_panchaangas[d].jd_sunset)
      log_data = '%02d-%02d-%4d\t[%3d]\tsun_rashi=%8.3f\ttithi=%8.3f\tsolar_month\
        =%2d\tlunar_month=%4.1f\n' % (dt, m, y, d, (longitude_sun_sunset % 360) / 30.0,
                                      NakshatraDivision(self.daily_panchaangas[d].jd_sunrise,
                                                        ayanamsha_id=self.ayanamsha_id).get_anga_float(
                                        zodiac.AngaType.TITHI),
                                      self.daily_panchaangas[d].solar_month_sunset, self.lunar_month[d])
      log_file.write(log_data)

  def update_festival_details(self, debug=False):
    """

    Festival data may be updated more frequently and a precomputed panchaanga may go out of sync. Hence we keep this method separate.
    :return:
    """
    self._reset_festivals()
    TithiAssigner(self).assign_shraaddha_tithi()
    from jyotisha.panchaanga.temporal.festival import applier
    from jyotisha.panchaanga.temporal.festival.applier import tithi_festival, ecliptic, solar, vaara
    applier.MiscFestivalAssigner(panchaanga=self).assign_all(debug=debug)
    ecliptic.EclipticFestivalAssigner(panchaanga=self).assign_all(debug=debug)
    tithi_festival.TithiFestivalAssigner(panchaanga=self).assign_all(debug=debug)
    solar.SolarFestivalAssigner(panchaanga=self).assign_all(debug=debug)
    vaara.VaraFestivalAssigner(panchaanga=self).assign_all(debug=debug)
    applier.MiscFestivalAssigner(panchaanga=self).cleanup_festivals(debug=debug)
    applier.MiscFestivalAssigner(panchaanga=self).assign_relative_festivals()

  def _reset_festivals(self, compute_lagnams=False):
    self.fest_days = {}
    for daily_panchaanga in self.daily_panchaangas:
      daily_panchaanga.festivals = []


# Essential for depickling to work.
common.update_json_class_index(sys.modules[__name__])


# logging.debug(common.json_class_index)


def get_panchaanga(city, start_date, end_date, script, fmt='hh:mm', compute_lagnams=False,
                   precomputed_json_dir="~/Documents", ayanamsha_id=zodiac.Ayanamsha.CHITRA_AT_180):
  fname_det = os.path.expanduser(
    '%s/%s-%s-%s-detailed.json' % (precomputed_json_dir, city.name, start_date, end_date))
  fname = os.path.expanduser('%s/%s-%s-%s.json' % (precomputed_json_dir, city.name, start_date, end_date))

  if os.path.isfile(fname) and not compute_lagnams:
    sys.stderr.write('Loaded pre-computed panchaanga from %s.\n' % fname)
    p = JsonObject.read_from_file(filename=fname)
    p.script = script  # Need to force script, in case saved file script is different
    return p
  elif os.path.isfile(fname_det):
    # Load pickle, do not compute!
    sys.stderr.write('Loaded pre-computed panchaanga from %s.\n' % fname)
    p = JsonObject.read_from_file(filename=fname_det)
    p.script = script  # Need to force script, in case saved file script is different
    return p
  else:
    sys.stderr.write('No precomputed data available. Computing panchaanga...\n')
    panchaanga = Panchaanga(city=city, start_date=start_date, end_date=end_date, script=script, fmt=fmt,
                            compute_lagnas=compute_lagnams, ayanamsha_id=ayanamsha_id)
    sys.stderr.write('Writing computed panchaanga to %s...\n' % fname)

    try:
      if compute_lagnams:
        panchaanga.dump_to_file(filename=fname_det)
      else:
        panchaanga.dump_to_file(filename=fname)
    except EnvironmentError:
      logging.warning("Not able to save.")
      logging.error(traceback.format_exc())
    # Save without festival details
    # Festival data may be updated more frequently and a precomputed panchaanga may go out of sync. Hence we keep this method separate.
    panchaanga.update_festival_details()
    return panchaanga


if __name__ == '__main__':
  city = spatio_temporal.City('Chennai', "13:05:24", "80:16:12", "Asia/Calcutta")
  panchaanga = Panchaanga(city=city, start_date='2019-04-14', end_date='2020-04-13', script=sanscript.DEVANAGARI,
                          ayanamsha_id=zodiac.Ayanamsha.CHITRA_AT_180, fmt='hh:mm', compute_lagnas=False)