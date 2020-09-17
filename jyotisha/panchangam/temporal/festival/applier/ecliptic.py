from datetime import datetime
from math import floor

from pytz import timezone as tz

from jyotisha import names
from jyotisha.panchangam import temporal
from jyotisha.panchangam.temporal.body import Graha
from jyotisha.panchangam.temporal.festival.applier import FestivalAssigner
from jyotisha.panchangam.temporal.hour import Hour


class EclipticFestivalAssigner(FestivalAssigner):
  def assign_all(self, debug_festivals=False):
    self.computeTransits()
    self.compute_solar_eclipses()
    self.compute_lunar_eclipses()

  def compute_solar_eclipses(self):
    jd = self.panchaanga.jd_start_utc
    while 1:
      next_eclipse_sol = self.panchaanga.city.get_solar_eclipse_time(jd_start=jd)
      [y, m, dt, t] = temporal.jd_to_utc_gregorian(next_eclipse_sol[1][0])
      local_time = tz(self.panchaanga.city.timezone).localize(datetime(y, m, dt, 6, 0, 0))
      # checking @ 6am local - can we do any better?
      tz_off = (datetime.utcoffset(local_time).days * 86400 +
                datetime.utcoffset(local_time).seconds) / 3600.0
      # compute offset from UTC
      jd = next_eclipse_sol[1][0] + (tz_off / 24.0)
      jd_eclipse_solar_start = next_eclipse_sol[1][1] + (tz_off / 24.0)
      jd_eclipse_solar_end = next_eclipse_sol[1][4] + (tz_off / 24.0)
      # -1 is to not miss an eclipse that occurs after sunset on 31-Dec!
      if jd_eclipse_solar_start > self.panchaanga.jd_end_utc + 1:
        break
      else:
        fday = int(floor(jd) - floor(self.panchaanga.jd_start_utc) + 1)
        if (jd < (self.panchaanga.jd_sunrise[fday] + tz_off / 24.0)):
          fday -= 1
        eclipse_solar_start = temporal.jd_to_utc_gregorian(jd_eclipse_solar_start)[3]
        eclipse_solar_end = temporal.jd_to_utc_gregorian(jd_eclipse_solar_end)[3]
        if (jd_eclipse_solar_start - (tz_off / 24.0)) == 0.0 or \
            (jd_eclipse_solar_end - (tz_off / 24.0)) == 0.0:
          # Move towards the next eclipse... at least the next new
          # moon (>=25 days away)
          jd += temporal.MIN_DAYS_NEXT_ECLIPSE
          continue
        if eclipse_solar_end < eclipse_solar_start:
          eclipse_solar_end += 24
        sunrise_eclipse_day = temporal.jd_to_utc_gregorian(self.panchaanga.jd_sunrise[fday] + (tz_off / 24.0))[3]
        sunset_eclipse_day = temporal.jd_to_utc_gregorian(self.panchaanga.jd_sunset[fday] + (tz_off / 24.0))[3]
        if eclipse_solar_start < sunrise_eclipse_day:
          eclipse_solar_start = sunrise_eclipse_day
        if eclipse_solar_end > sunset_eclipse_day:
          eclipse_solar_end = sunset_eclipse_day
        solar_eclipse_str = 'sUrya-grahaNam' + \
                            '~\\textsf{' + Hour(eclipse_solar_start).toString(format=self.panchaanga.fmt) + \
                            '}{\\RIGHTarrow}\\textsf{' + Hour(eclipse_solar_end).toString(format=self.panchaanga.fmt) + '}'
        if self.panchaanga.weekday[fday] == 0:
          solar_eclipse_str = '★cUDAmaNi-' + solar_eclipse_str
        self.panchaanga.festivals[fday].append(solar_eclipse_str)
      jd = jd + temporal.MIN_DAYS_NEXT_ECLIPSE

  def compute_lunar_eclipses(self):
    # Set location
    jd = self.panchaanga.jd_start_utc
    while 1:
      next_eclipse_lun = self.panchaanga.city.get_lunar_eclipse_time(jd)
      [y, m, dt, t] = temporal.jd_to_utc_gregorian(next_eclipse_lun[1][0])
      local_time = tz(self.panchaanga.city.timezone).localize(datetime(y, m, dt, 6, 0, 0))
      # checking @ 6am local - can we do any better? This is crucial,
      # since DST changes before 6 am
      tz_off = (datetime.utcoffset(local_time).days * 86400 +
                datetime.utcoffset(local_time).seconds) / 3600.0
      # compute offset from UTC
      jd = next_eclipse_lun[1][0] + (tz_off / 24.0)
      jd_eclipse_lunar_start = next_eclipse_lun[1][2] + (tz_off / 24.0)
      jd_eclipse_lunar_end = next_eclipse_lun[1][3] + (tz_off / 24.0)
      # -1 is to not miss an eclipse that occurs after sunset on 31-Dec!
      if jd_eclipse_lunar_start > self.panchaanga.jd_end_utc:
        break
      else:
        eclipse_lunar_start = temporal.jd_to_utc_gregorian(jd_eclipse_lunar_start)[3]
        eclipse_lunar_end = temporal.jd_to_utc_gregorian(jd_eclipse_lunar_end)[3]
        if (jd_eclipse_lunar_start - (tz_off / 24.0)) == 0.0 or \
            (jd_eclipse_lunar_end - (tz_off / 24.0)) == 0.0:
          # Move towards the next eclipse... at least the next full
          # moon (>=25 days away)
          jd += temporal.MIN_DAYS_NEXT_ECLIPSE
          continue
        fday = int(floor(jd_eclipse_lunar_start) - floor(self.panchaanga.jd_start_utc) + 1)
        # print '%%', jd, fday, self.panchaanga.jd_sunrise[fday],
        # self.panchaanga.jd_sunrise[fday-1]
        if (jd < (self.panchaanga.jd_sunrise[fday] + tz_off / 24.0)):
          fday -= 1
        if eclipse_lunar_start < temporal.jd_to_utc_gregorian(self.panchaanga.jd_sunrise[fday + 1] + tz_off / 24.0)[3]:
          eclipse_lunar_start += 24
        # print '%%', jd, fday, self.panchaanga.jd_sunrise[fday],
        # self.panchaanga.jd_sunrise[fday-1], eclipse_lunar_start,
        # eclipse_lunar_end
        jd_moonrise_eclipse_day = self.panchaanga.city.get_rising_time(julian_day_start=self.panchaanga.jd_sunrise[fday],
                                                            body=Graha.MOON) + (tz_off / 24.0)

        jd_moonset_eclipse_day = self.panchaanga.city.get_rising_time(julian_day_start=jd_moonrise_eclipse_day,
                                                           body=Graha.MOON) + (tz_off / 24.0)

        if eclipse_lunar_end < eclipse_lunar_start:
          eclipse_lunar_end += 24

        if jd_eclipse_lunar_end < jd_moonrise_eclipse_day or \
            jd_eclipse_lunar_start > jd_moonset_eclipse_day:
          # Move towards the next eclipse... at least the next full
          # moon (>=25 days away)
          jd += temporal.MIN_DAYS_NEXT_ECLIPSE
          continue

        moonrise_eclipse_day = temporal.jd_to_utc_gregorian(jd_moonrise_eclipse_day)[3]
        moonset_eclipse_day = temporal.jd_to_utc_gregorian(jd_moonset_eclipse_day)[3]

        if jd_eclipse_lunar_start < jd_moonrise_eclipse_day:
          eclipse_lunar_start = moonrise_eclipse_day
        if jd_eclipse_lunar_end > jd_moonset_eclipse_day:
          eclipse_lunar_end = moonset_eclipse_day

        if Graha(Graha.MOON).get_longitude(jd_eclipse_lunar_end) < Graha(Graha.SUN).get_longitude(
            jd_eclipse_lunar_end):
          grasta = 'rAhugrasta'
        else:
          grasta = 'kEtugrasta'

        lunar_eclipse_str = 'candra-grahaNam~(' + grasta + ')' + \
                            '~\\textsf{' + Hour(eclipse_lunar_start).toString(format=self.panchaanga.fmt) + \
                            '}{\\RIGHTarrow}\\textsf{' + Hour(eclipse_lunar_end).toString(format=self.panchaanga.fmt) + '}'
        if self.panchaanga.weekday[fday] == 1:
          lunar_eclipse_str = '★cUDAmaNi-' + lunar_eclipse_str

        self.panchaanga.festivals[fday].append(lunar_eclipse_str)
      jd += temporal.MIN_DAYS_NEXT_ECLIPSE

  def computeTransits(self):
    jd_end = self.panchaanga.jd_start_utc + self.panchaanga.duration
    check_window = 400  # Max t between two Jupiter transits is ~396 (checked across 180y)
    # Let's check for transitions in a relatively large window
    # to finalise what is the FINAL transition post retrograde movements
    transits = Graha(Graha.JUPITER).get_next_raashi_transit(self.panchaanga.jd_start_utc, jd_end + check_window,
                                                            ayanamsha_id=self.panchaanga.ayanamsha_id)
    if len(transits) > 0:
      for i, (jd_transit, rashi1, rashi2) in enumerate(transits):
        if self.panchaanga.jd_start_utc < jd_transit < jd_end:
          fday = int(floor(jd_transit) - floor(self.panchaanga.jd_start_utc) + 1)
          self.panchaanga.festivals[fday].append('guru-saGkrAntiH~(%s##\\To{}##%s)' %
                                      (names.NAMES['RASHI_NAMES']['hk'][rashi1],
                                       names.NAMES['RASHI_NAMES']['hk'][rashi2]))
          if rashi1 < rashi2 and transits[i + 1][1] < transits[i + 1][2]:
            # Considering only non-retrograde transits for pushkara computations
            # logging.debug('Non-retrograde transit; we have a pushkaram!')
            (madhyanha_start, madhyaahna_end) = temporal.get_interval(self.panchaanga.jd_sunrise[fday],
                                                                      self.panchaanga.jd_sunset[fday], 2, 5).to_tuple()
            if jd_transit < madhyaahna_end:
              fday_pushkara = fday
            else:
              fday_pushkara = fday + 1
            self.add_festival(
              '%s-Adi-puSkara-ArambhaH' % names.NAMES['PUSHKARA_NAMES']['hk'][rashi2],
              fday_pushkara, debug=False)
            self.add_festival(
              '%s-Adi-puSkara-samApanam' % names.NAMES['PUSHKARA_NAMES']['hk'][rashi2],
              fday_pushkara + 11, debug=False)
            self.add_festival(
              '%s-antya-puSkara-samApanam' % names.NAMES['PUSHKARA_NAMES']['hk'][rashi1],
              fday_pushkara - 1, debug=False)
            self.add_festival(
              '%s-antya-puSkara-ArambhaH' % names.NAMES['PUSHKARA_NAMES']['hk'][rashi1],
              fday_pushkara - 12, debug=False)