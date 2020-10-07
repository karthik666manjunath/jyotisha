import sys
from datetime import datetime
from math import floor

from jyotisha.panchaanga.temporal.zodiac.angas import AngaType
from jyotisha import names
from jyotisha.panchaanga.temporal import time
from jyotisha.panchaanga.temporal import zodiac, tithi
from jyotisha.panchaanga.temporal.festival.applier import FestivalAssigner
from jyotisha.panchaanga.temporal.zodiac import NakshatraDivision
from pytz import timezone as tz

from sanskrit_data.schema import common


class SolarFestivalAssigner(FestivalAssigner):
  def assign_all(self, debug=False):
    # self.assign_gajachhaya_yoga()
    self.assign_mahodaya_ardhodaya()
    self.assign_month_day_festivals()
    self.assign_vishesha_vyatipata()

  def assign_month_day_festivals(self):
    for d in range(1, self.panchaanga.duration + 1):
      [y, m, dt, t] = time.jd_to_utc_gregorian(self.panchaanga.jd_start + d - 1).to_date_fractional_hour_tuple()
      ####################
      # Festival details #
      ####################

      # KARADAIYAN NOMBU
      if self.daily_panchaangas[d].solar_sidereal_date_sunset.month == 12 and self.daily_panchaangas[d].solar_sidereal_date_sunset.day == 1:
        festival_name = 'kAraDaiyAn2 nOn2bu'
        if NakshatraDivision(self.daily_panchaangas[d].jd_sunrise - (1 / 15.0) * (self.daily_panchaangas[d].jd_sunrise - self.daily_panchaangas[d - 1].jd_sunrise),
                             ayanaamsha_id=self.ayanaamsha_id).get_solar_raashi() == 12:
          # If kumbha prevails two ghatikAs before sunrise, nombu can be done in the early morning itself, else, previous night.
          self.panchaanga.festival_id_to_days[festival_name] =  [self.daily_panchaangas[d - 1].date]
        else:
          self.panchaanga.festival_id_to_days[festival_name] = [self.daily_panchaangas[d].date]

      # KUCHELA DINAM
      if self.daily_panchaangas[d].solar_sidereal_date_sunset.month == 9 and self.daily_panchaangas[d].solar_sidereal_date_sunset.day <= 7 and self.daily_panchaangas[d].date.get_weekday() == 3:
        self.panchaanga.festival_id_to_days['kucEla-dinam'] = [self.daily_panchaangas[d].date]

      # MESHA SANKRANTI
      if self.daily_panchaangas[d].solar_sidereal_date_sunset.month == 1 and self.daily_panchaangas[d - 1].solar_sidereal_date_sunset.month == 12:
        # distance from prabhava
        samvatsara_id = (y - 1568) % 60 + 1
        new_yr = 'mESa-saGkrAntiH' + '~(' + names.NAMES['SAMVATSARA_NAMES']['hk'][
          (samvatsara_id % 60) + 1] + \
                 '-' + 'saMvatsaraH' + ')'
        # self.panchaanga.festival_id_to_days[new_yr] = [d]
        self.add_festival(new_yr, d)
        self.add_festival('paJcAGga-paThanam', d)

  def assign_vishesha_vyatipata(self):
    vs_list = self.panchaanga.festival_id_to_days['vyatIpAta-zrAddham']
    for date in vs_list:
      d = int(date - self.daily_panchaangas[0].date)
      if self.daily_panchaangas[d].solar_sidereal_date_sunset.month == 9:
        self.panchaanga.festival_id_to_days['vyatIpAta-zrAddham'].remove(date)
        festival_name = 'mahAdhanurvyatIpAta-zrAddham'
        self.add_festival(festival_name, d)
      elif self.daily_panchaangas[d].solar_sidereal_date_sunset.month == 6:
        self.panchaanga.festival_id_to_days['vyatIpAta-zrAddham'].remove(date)
        festival_name = 'mahAvyatIpAta-zrAddham'
        self.add_festival(festival_name, d)

  def assign_gajachhaya_yoga(self):
    for d in range(1, self.panchaanga.duration + 1):
      [y, m, dt, t] = time.jd_to_utc_gregorian(self.panchaanga.jd_start + d - 1).to_date_fractional_hour_tuple()

      # checking @ 6am local - can we do any better?
      local_time = tz(self.panchaanga.city.timezone).localize(datetime(y, m, dt, 6, 0, 0))
      # compute offset from UTC in hours
      tz_off = (datetime.utcoffset(local_time).days * 86400 +
                datetime.utcoffset(local_time).seconds) / 3600.0
      # GAJACHHAYA YOGA
      if self.daily_panchaangas[d].solar_sidereal_date_sunset.month == 6 and self.daily_panchaangas[d].solar_sidereal_date_sunset.day == 1:
        moon_magha_jd_start = moon_magha_jd_start = t28_start = None
        moon_magha_jd_end = moon_magha_jd_end = t28_end = None
        moon_hasta_jd_start = moon_hasta_jd_start = t30_start = None
        moon_hasta_jd_end = moon_hasta_jd_end = t30_end = None

        anga_finder = zodiac.AngaSpanFinder(ayanaamsha_id=self.computation_system.ayanaamsha_id, default_anga_type=AngaType.SIDEREAL_MONTH)
        sun_hasta_jd_start, sun_hasta_jd_end = anga_finder.find(
          jd1=self.daily_panchaangas[d].jd_sunrise, jd2=self.daily_panchaangas[d].jd_sunrise + 30, target_anga_in=13).to_tuple()

        moon_magha_jd_start, moon_magha_jd_end = anga_finder.find(
          sun_hasta_jd_start - 2, sun_hasta_jd_end + 2, 10).to_tuple()
        if all([moon_magha_jd_start, moon_magha_jd_end]):
          anga_finder = zodiac.AngaSpanFinder(ayanaamsha_id=self.computation_system.ayanaamsha_id, default_anga_type=AngaType.TITHI)
          t28_start, t28_end = anga_finder.find(
            moon_magha_jd_start - 3, moon_magha_jd_end + 3, 28).to_tuple()

        anga_finder = zodiac.AngaSpanFinder(ayanaamsha_id=self.computation_system.ayanaamsha_id, default_anga_type=AngaType.NAKSHATRA)
        moon_hasta_jd_start, moon_hasta_jd_end = anga_finder.find(
          sun_hasta_jd_start - 1, sun_hasta_jd_end + 1, 13).to_tuple()
        if all([moon_hasta_jd_start, moon_hasta_jd_end]):
          anga_finder = zodiac.AngaSpanFinder(ayanaamsha_id=self.computation_system.ayanaamsha_id, default_anga_type=AngaType.TITHI)
          t30_start, t30_end = anga_finder.find(
            sun_hasta_jd_start - 1, sun_hasta_jd_end + 1, 30).to_tuple()

        gc_28 = gc_30 = False

        if all([sun_hasta_jd_start, moon_magha_jd_start, t28_start]):
          # We have a GC yoga
          gc_28_start = max(sun_hasta_jd_start, moon_magha_jd_start, t28_start)
          gc_28_end = min(sun_hasta_jd_end, moon_magha_jd_end, t28_end)

          if gc_28_start < gc_28_end:
            gc_28 = True

        if all([sun_hasta_jd_start, moon_hasta_jd_start, t30_start]):
          # We have a GC yoga
          gc_30_start = max(sun_hasta_jd_start, moon_hasta_jd_start, t30_start)
          gc_30_end = min(sun_hasta_jd_end, moon_hasta_jd_end, t30_end)

          if gc_30_start < gc_30_end:
            gc_30 = True

      if self.daily_panchaangas[d].solar_sidereal_date_sunset.month == 6 and (gc_28 or gc_30):
        if gc_28:
          gc_28_d = 1 + floor(gc_28_start - self.panchaanga.jd_start)
          # sys.stderr.write('gajacchhaya %d\n' % gc_28_d)
          # gajacchaayaa_fest = FestivalInstance(name='gajacchAyA-yOgaH', interval=Interval(jd_start=gc_28_start, jd_end=gc_28_end), days=[self.daily_panchaangas[gc_28_d].date])
          # self.panchaanga.festival_id_to_days[gajacchaayaa_fest.name] = gajacchaayaa_fest
          gc_28 = False
        if gc_30:
          # sys.stderr.write('30: (%f, %f)\n' % (gc_30_start, gc_30_end))
          gc_30_d = 1 + floor(gc_30_start - self.panchaanga.jd_start)
          # gajacchaayaa_fest = FestivalInstance(name='gajacchAyA-yOgaH', interval=Interval(jd_start=gc_30_start, jd_end=gc_30_end), days=[self.daily_panchaangas[gc_30_d].date])
          # self.panchaanga.festival_id_to_days[gajacchaayaa_fest.name] = gajacchaayaa_fest
          gc_30 = False

  def assign_mahodaya_ardhodaya(self):
    for d in range(1, self.panchaanga.duration + 1):
      [y, m, dt, t] = time.jd_to_utc_gregorian(self.panchaanga.jd_start + d - 1).to_date_fractional_hour_tuple()

      # MAHODAYAM
      # Can also refer youtube video https://youtu.be/0DBIwb7iaLE?list=PL_H2LUtMCKPjh63PRk5FA3zdoEhtBjhzj&t=6747
      # 4th pada of vyatipatam, 1st pada of Amavasya, 2nd pada of Shravana, Suryodaya, Bhanuvasara = Ardhodayam
      # 4th pada of vyatipatam, 1st pada of Amavasya, 2nd pada of Shravana, Suryodaya, Somavasara = Mahodayam
      sunrise_zodiac = NakshatraDivision(self.daily_panchaangas[d].jd_sunrise, ayanaamsha_id=self.ayanaamsha_id)
      sunset_zodiac = NakshatraDivision(self.daily_panchaangas[d].jd_sunset, ayanaamsha_id=self.ayanaamsha_id)
      if self.daily_panchaangas[d].lunar_month_sunrise in [10, 11] and self.daily_panchaangas[d].sunrise_day_angas.tithi_at_sunrise == 30 or tithi.get_tithi(self.daily_panchaangas[d].jd_sunrise) == 30:
        if sunrise_zodiac.get_anga(AngaType.NAKSHATRA) == 17 or \
            sunset_zodiac.get_anga(AngaType.NAKSHATRA) == 17 and \
            sunrise_zodiac.get_anga(AngaType.NAKSHATRA) == 22 or \
            sunset_zodiac.get_anga(AngaType.NAKSHATRA) == 22:
          if self.daily_panchaangas[d].date.get_weekday() == 1:
            festival_name = 'mahOdaya-puNyakAlaH'
            self.add_festival(festival_name, d)
            # logging.debug('* %d-%02d-%02d> %s!' % (y, m, dt, festival_name))
          elif self.daily_panchaangas[d].date.get_weekday() == 0:
            festival_name = 'ardhOdaya-puNyakAlaH'
            self.add_festival(festival_name, d)
            # logging.debug('* %d-%02d-%02d> %s!' % (y, m, dt, festival_name))


# Essential for depickling to work.
common.update_json_class_index(sys.modules[__name__])
