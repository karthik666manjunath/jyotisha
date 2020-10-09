import sys

from jyotisha.panchaanga.temporal import time
from jyotisha.panchaanga.temporal.festival.applier import FestivalAssigner
from jyotisha.panchaanga.temporal.zodiac import NakshatraDivision
from jyotisha.panchaanga.temporal.zodiac.angas import AngaType
from sanskrit_data.schema import common


class VaraFestivalAssigner(FestivalAssigner):
  def assign_all(self, debug=False):
    self.assign_bhriguvara_subrahmanya_vratam(debug_festivals=debug)
    self.assign_masa_vara_yoga_vratam(debug_festivals=debug)
    self.assign_nakshatra_vara_yoga_vratam(debug_festivals=debug)
    self.assign_ayushman_bava_saumya_yoga(debug_festivals=debug)
    self.assign_tithi_vara_yoga(debug_festivals=debug)


  def assign_bhriguvara_subrahmanya_vratam(self, debug_festivals=False):
    for d in range(1, self.panchaanga.duration + 1):
      [y, m, dt, t] = time.jd_to_utc_gregorian(self.panchaanga.jd_start + d - 1).to_date_fractional_hour_tuple()

      # BHRGUVARA SUBRAHMANYA VRATAM
      if self.daily_panchaangas[d].solar_sidereal_date_sunset.month == 7 and self.daily_panchaangas[d].date.get_weekday() == 5:
        festival_name = 'bhRguvAra-subrahmaNya-vratam'
        if festival_name not in self.panchaanga.festival_id_to_days:
          # only the first bhRguvAra of tulA mAsa is considered (skAnda purANam)
          # https://youtu.be/rgXwyo0L3i8?t=222
          self.add_festival(festival_name, d)

  def assign_masa_vara_yoga_vratam(self, debug_festivals=False):
    for d in range(1, self.panchaanga.duration + 1):

      # KRTTIKA SOMAVASARA
      if self.daily_panchaangas[d].lunar_month_sunrise == 8 and self.daily_panchaangas[d].date.get_weekday() == 1:
        self.add_festival('kRttikA~sOmavAsaraH', d)

      # SOLAR MONTH-WEEKDAY FESTIVALS
      for (mwd_fest_m, mwd_fest_wd, mwd_fest_name) in ((5, 0, 'AvaNi~JAyir2r2ukkizhamai'),
                                                       (6, 6, 'puraTTAci~can2ikkizhamai'),
                                                       (8, 0, 'kArttigai~JAyir2r2ukkizhamai'),
                                                       (4, 5, 'ADi~veLLikkizhamai'),
                                                       (10, 5, 'tai~veLLikkizhamai'),
                                                       (11, 2, 'mAci~cevvAy')):
        if self.daily_panchaangas[d].solar_sidereal_date_sunset.month == mwd_fest_m and self.daily_panchaangas[d].date.get_weekday() == mwd_fest_wd:
          self.add_festival(mwd_fest_name, d)

  def assign_tithi_vara_yoga(self, debug_festivals=False):
    for d in range(1, self.panchaanga.duration + 1):
      [y, m, dt, t] = time.jd_to_utc_gregorian(self.panchaanga.jd_start + d - 1).to_date_fractional_hour_tuple()

      # MANGALA-CHATURTHI
      if self.daily_panchaangas[d].date.get_weekday() == 2 and (self.daily_panchaangas[d].sunrise_day_angas.tithi_at_sunrise % 15) == 4:
        festival_name = 'aGgAraka-caturthI'
        if self.daily_panchaangas[d].sunrise_day_angas.tithi_at_sunrise == 4:
          festival_name = 'sukhA' + '~' + festival_name
        self.add_festival(festival_name, d)

      # KRISHNA ANGARAKA CHATURDASHI
      if self.daily_panchaangas[d].date.get_weekday() == 2 and self.daily_panchaangas[d].sunrise_day_angas.tithi_at_sunrise == 29:
        # Double-check rule. When should the vyApti be?
        self.add_festival('kRSNAGgAraka-caturdazI-puNyakAlaH/yamatarpaNam', d)

      # BUDHASHTAMI
      if self.daily_panchaangas[d].date.get_weekday() == 3 and (self.daily_panchaangas[d].sunrise_day_angas.tithi_at_sunrise % 15) == 8:
        self.add_festival('budhASTamI', d)


  def assign_nakshatra_vara_yoga_vratam(self, debug_festivals=False):
    for d in range(1, self.panchaanga.duration + 1):
      [y, m, dt, t] = time.jd_to_utc_gregorian(self.panchaanga.jd_start + d - 1).to_date_fractional_hour_tuple()

      # NAKSHATRA-WEEKDAY FESTIVALS
      for (nwd_fest_n, nwd_fest_wd, nwd_fest_name) in ((13, 0, 'Adityahasta-puNyakAlaH'),
                                                       (8, 0, 'ravipuSyayOga-puNyakAlaH'),
                                                       (22, 1, 'sOmazrAvaNI-puNyakAlaH'),
                                                       (5, 1, 'sOmamRgazIrSa-puNyakAlaH'),
                                                       (1, 2, 'bhaumAzvinI-puNyakAlaH'),
                                                       (6, 2, 'bhaumArdrA-puNyakAlaH'),
                                                       (17, 3, 'budhAnurAdhA-puNyakAlaH'),
                                                       (8, 4, 'gurupuSya-puNyakAlaH'),
                                                       (27, 5, 'bhRgurEvatI-puNyakAlaH'),
                                                       (4, 6, 'zanirOhiNI-puNyakAlaH'),
                                                       ):
        n_prev = ((nwd_fest_n - 2) % 27) + 1
        if (self.daily_panchaangas[d].sunrise_day_angas.nakshatra_at_sunrise == nwd_fest_n or self.daily_panchaangas[d].sunrise_day_angas.nakshatra_at_sunrise == n_prev) and self.daily_panchaangas[
          d].date.get_weekday() == nwd_fest_wd:
          # Is it necessarily only at sunrise?
          angas = self.panchaanga.get_2_day_interval_boundaries_angas(d, lambda x: NakshatraDivision(x,
                                                                                                     ayanaamsha_id=self.ayanaamsha_id).get_nakshatra(),
                                              'dinamaana')
          if any(x == nwd_fest_n for x in [self.daily_panchaangas[d].sunrise_day_angas.nakshatra_at_sunrise, angas[0], angas[1]]):
            self.add_festival(nwd_fest_name, d)


  def assign_ayushman_bava_saumya_yoga(self, debug_festivals=False):
    for d in range(1, self.panchaanga.duration + 1):
      [y, m, dt, t] = time.jd_to_utc_gregorian(self.panchaanga.jd_start + d - 1).to_date_fractional_hour_tuple()

      # AYUSHMAN BHAVA SAUMYA
      if self.daily_panchaangas[d].date.get_weekday() == 3 and NakshatraDivision(self.daily_panchaangas[d].jd_sunrise, ayanaamsha_id=self.ayanaamsha_id).get_anga(
          AngaType.NAKSHATRA) == 3:
        if NakshatraDivision(self.daily_panchaangas[d].jd_sunrise, ayanaamsha_id=self.ayanaamsha_id).get_anga(
            AngaType.KARANA) in list(range(2, 52, 7)):
          self.add_festival('AyuSmad-bava-saumya-saMyogaH', d)
      if self.daily_panchaangas[d].date.get_weekday() == 3 and NakshatraDivision(self.daily_panchaangas[d].jd_sunset, ayanaamsha_id=self.ayanaamsha_id).get_anga(
          AngaType.NAKSHATRA) == 3:
        if NakshatraDivision(self.daily_panchaangas[d].jd_sunset, ayanaamsha_id=self.ayanaamsha_id).get_anga(
            AngaType.KARANA) in list(range(2, 52, 7)):
          self.add_festival('AyuSmad-bava-saumya-saMyogaH', d)


# Essential for depickling to work.
common.update_json_class_index(sys.modules[__name__])
