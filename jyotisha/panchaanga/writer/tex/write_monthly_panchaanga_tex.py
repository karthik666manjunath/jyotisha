#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import os
import os.path
import sys
from datetime import datetime

from indic_transliteration import xsanscript as sanscript
from panchaanga.temporal.time import Timezone
from pytz import timezone as tz

import jyotisha
import jyotisha.custom_transliteration
import jyotisha.names
from jyotisha.panchaanga.spatio_temporal import City, annual
from jyotisha.panchaanga.temporal import time
from jyotisha.panchaanga.temporal.festival import rules

logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)

CODE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def write_monthly_tex(panchaanga, template_file, scripts=[sanscript.DEVANAGARI], temporal=None):
  """Write out the panchaanga TeX using a specified template
  """
  day_colours = {0: 'blue', 1: 'blue', 2: 'blue',
                 3: 'blue', 4: 'blue', 5: 'blue', 6: 'blue'}
  month = {1: 'JANUARY', 2: 'FEBRUARY', 3: 'MARCH', 4: 'APRIL',
           5: 'MAY', 6: 'JUNE', 7: 'JULY', 8: 'AUGUST', 9: 'SEPTEMBER',
           10: 'OCTOBER', 11: 'NOVEMBER', 12: 'DECEMBER'}
  MON = {1: 'January', 2: 'February', 3: 'March', 4: 'April',
         5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September',
         10: 'October', 11: 'November', 12: 'December'}
  WDAY = {0: 'Sun', 1: 'Mon', 2: 'Tue',
          3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat'}

  monthly_template_file = open(os.path.join(os.path.dirname(__file__), 'templates/monthly_cal_template.tex'))

  template_lines = template_file.readlines()
  for i in range(0, len(template_lines) - 3):
    print(template_lines[i][:-1])

  samvatsara_id = (panchaanga.year - 1568) % 60 + 1  # distance from prabhava
  samvatsara_names = '%s–%s' % (jyotisha.names.NAMES['SAMVATSARA_NAMES'][scripts[0]][samvatsara_id],
                                jyotisha.names.NAMES['SAMVATSARA_NAMES'][scripts[0]][(samvatsara_id % 60) + 1])

  print('\\mbox{}')
  print('{\\sffamily\\fontsize{60}{25}\\selectfont %d\\\\[0.5cm]}' % panchaanga.year)
  print('\\mbox{\\font\\x="Siddhanta:script=deva" at 48 pt\\x %s}\\\\[0.5cm]' %
        samvatsara_names)
  print('\\mbox{\\font\\x="Siddhanta:script=deva" at 32 pt\\x %s } %%'
        % jyotisha.custom_transliteration.tr('kali', scripts[0]))
  print('{\\sffamily\\fontsize{32}{25}\\selectfont %d–%d\\\\[0.5cm]}'
        % (panchaanga.year + 3100, panchaanga.year + 3101))
  print('{\\sffamily\\fontsize{48}{25}\\selectfont \\uppercase{%s}\\\\[0.2cm]}' %
        panchaanga.city.name)
  print('{\\sffamily\\fontsize{16}{25}\\selectfont {%s}\\\\[0.5cm]}' %
        jyotisha.custom_transliteration.print_lat_lon(panchaanga.city.latitude, panchaanga.city.longitude))
  print('\\hrule')

  print('\\newpage')
  print('\\centering')
  print('\\centerline{\\LARGE {{%s}}}' % jyotisha.custom_transliteration.tr('mAsAntara-vizESAH', scripts[0]))
  print('\\begin{multicols*}{3}')
  print('\\TrickSupertabularIntoMulticols')
  print('\\begin{supertabular}' +
        '{>{\\sffamily}r>{\\sffamily}r>{\\sffamily}c>{\\hangindent=2ex}panchaanga{8cm}}')

  mlast = 1
  daily_panchaangas = panchaanga.daily_panchaangas_sorted()
  for d in range(1, jyotisha.panchaanga.temporal.MAX_SZ - 1):
    [y, m, dt, t] = time.jd_to_utc_gregorian(panchaanga.jd_start + d - 1).to_date_fractional_hour_tuple()
    daily_panchaanga = daily_panchaangas[d]

    rules_collection = rules.RulesCollection.get_cached(repos=tuple(panchaanga.computation_system.options.fest_repos))
    fest_details_dict = rules_collection.name_to_rule

    if len(daily_panchaanga.festival_id_to_instance) != 0:
      if m != mlast:
        mlast = m
        print('\\\\')

      print('%s & %s & %s & {\\raggedright %s} \\\\' %
            (MON[m], dt, WDAY[daily_panchaanga.date.get_weekday()],
             '\\\\'.join([f.tex_code(scripts=scripts, timezone=panchaanga.city.timezone, fest_details_dict=fest_details_dict)
                          for f in sorted(daily_panchaanga.festival_id_to_instance.values())])))

    if m == 12 and dt == 31:
      break

  print('\\end{supertabular}')
  print('\\end{multicols*}')
  print('\\renewcommand{\\tamil}[1]{%')
  print('{\\fontspec[Scale=0.9,FakeStretch=0.9]{Noto Sans Tamil}\\fontsize{7}{12}\\selectfont #1}}')

  # print('\\clearpage')

  month_text = ''
  W6D1 = W6D2 = ''
  for d in range(1, jyotisha.panchaanga.temporal.MAX_SZ - 1):
    [y, m, dt, t] = time.jd_to_utc_gregorian(panchaanga.jd_start + d - 1).to_date_fractional_hour_tuple()

    # checking @ 6am local - can we do any better?
    local_time = tz(panchaanga.city.timezone).localize(datetime(y, m, dt, 6, 0, 0))
    # compute offset from UTC in hours
    tz_off = (datetime.utcoffset(local_time).days * 86400 +
              datetime.utcoffset(local_time).seconds) / 3600.0

    # What is the jd at 00:00 local time today?
    jd = daily_panchaanga.julian_day_start

    if dt == 1:
      currWeek = 1
      if m > 1:
        month_text = month_text.replace('W6D1', W6D1)
        month_text = month_text.replace('W6D2', W6D2)
        print(month_text)
        month_text = W6D1 = W6D2 = ''
        if currWeek < 6:
          if daily_panchaanga.date.get_weekday() != 0:  # Space till Sunday
            for i in range(daily_panchaanga.date.get_weekday(), 6):
              print("\\mbox{}  & %% %d" % currWeek)
            print("\\\\ \\hline")
        print('\\end{tabular}')
        print('\n\n')

      # Begin tabular
      print('\\begin{tabular}{|c|c|c|c|c|c|c|}')
      print('\\multicolumn{7}{c}{\\Large \\bfseries \\sffamily %s %s}\\\\[3mm]' % (
        month[m], y))
      print('\\hline')
      WDAY_NAMES = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
      print(' & '.join(['\\textbf{\\textsf{%s}}' %
                        _day for _day in WDAY_NAMES]) + ' \\\\ \\hline')

      # Blanks for previous weekdays
      for i in range(0, daily_panchaanga.date.get_weekday()):
        if i == 0:
          month_text += '\n' + ("{W6D1}  &")
        elif i == 1:
          month_text += '\n' + ("{W6D2}  &")
        else:
          month_text += '\n' + ("{}  &")

    tithi_data_str = ''
    for tithi_span in daily_panchaanga.sunrise_day_angas.tithis_with_ends:
      (tithi_ID, tithi_end_jd) = (tithi_span.anga.index, tithi_span.jd_end)
      # if tithi_data_str != '':
      #     tithi_data_str += '\\hspace{2ex}'
      tithi = '\\moon[scale=0.6]{%d}\\hspace{2pt}' % (tithi_ID) + \
              jyotisha.names.NAMES['TITHI_NAMES'][scripts[0]][tithi_ID]
      if tithi_end_jd is None:
        tithi_data_str = '%s\\mbox{%s\\To{}%s}' % \
                         (tithi_data_str, tithi, jyotisha.custom_transliteration.tr('ahOrAtram', scripts[0]))
      else:
        tithi_data_str = '%s\\mbox{%s\\To{}\\textsf{%s%s}}' % \
                         (tithi_data_str, tithi,
                          jyotisha.panchaanga.temporal.hour.Hour(24 * (tithi_end_jd - jd)).toString(
                            format=panchaanga.fmt),
                          '\\hspace{2ex}')

    nakshatra_data_str = ''
    for nakshatra_span in daily_panchaanga.sunrise_day_angas.nakshatras_with_ends:
      (nakshatra_ID, nakshatra_end_jd) = (nakshatra_span.anga.index, nakshatra_span.jd_end)
      # if nakshatra_data_str != '':
      #     nakshatra_data_str += '\\hspace{2ex}'
      nakshatra = jyotisha.names.NAMES['NAKSHATRA_NAMES'][scripts[0]][nakshatra_ID]
      if nakshatra_end_jd is None:
        nakshatra_data_str = '%s\\mbox{%s\\To{}%s}' % \
                              (nakshatra_data_str, nakshatra,
                               jyotisha.custom_transliteration.tr('ahOrAtram', scripts[0]))
      else:
        nakshatra_data_str = '%s\\mbox{%s\\To{}\\textsf{%s%s}}' % \
                              (nakshatra_data_str, nakshatra,
                               jyotisha.panchaanga.temporal.hour.Hour(24 * (nakshatra_end_jd -
                                                                            jd)).toString(format=panchaanga.fmt),
                               '\\hspace{2ex}')

    yoga_data_str = ''
    for yoga_span in daily_panchaanga.sunrise_day_angas.yogas_with_ends:
      (yoga_ID, yoga_end_jd) = (yoga_span.anga.index, yoga_span.jd_end)
      # if yoga_data_str != '':
      #     yoga_data_str += '\\hspace{2ex}'
      yoga = jyotisha.names.NAMES['YOGA_NAMES'][scripts[0]][yoga_ID]
      if yoga_end_jd is None:
        yoga_data_str = '%s\\mbox{%s\\To{}%s}' % \
                        (yoga_data_str, yoga, jyotisha.custom_transliteration.tr('ahOrAtram', scripts[0]))
      else:
        yoga_data_str = '%s\\mbox{%s\\To{}\\textsf{%s%s}}' % \
                        (yoga_data_str, yoga,
                         jyotisha.panchaanga.temporal.hour.Hour(24 * (yoga_end_jd - jd)).toString(
                           format=panchaanga.fmt),
                         '\\hspace{2ex}')

    karana_data_str = ''
    for numKaranam, karaNa_span in enumerate(daily_panchaanga.sunrise_day_angas.karanas_with_ends):
      (karana_ID, karana_end_jd) = (karaNa_span.anga.index, karaNa_span.jd_end)
      # if numKaranam == 1:
      #     karana_data_str += '\\hspace{2ex}'
      if numKaranam == 2:
        karana_data_str = karana_data_str + '\\\\'
      karana = jyotisha.names.NAMES['KARANA_NAMES'][scripts[0]][karana_ID]
      if karana_end_jd is None:
        karana_data_str = '%s\\mbox{%s\\To{}%s}' % \
                           (karana_data_str, karana,
                            jyotisha.custom_transliteration.tr('ahOrAtram', scripts[0]))
      else:
        karana_data_str = '%s\\mbox{%s\\To{}\\textsf{%s%s}}' % \
                           (karana_data_str, karana,
                            jyotisha.panchaanga.temporal.hour.Hour(24 * (karana_end_jd -
                                                                         jd)).toString(format=panchaanga.fmt),
                            '\\hspace{2ex}')

    sunrise = jyotisha.panchaanga.temporal.hour.Hour(24 * (daily_panchaanga.jd_sunrise - jd)).toString(
      format=panchaanga.fmt)
    sunset = jyotisha.panchaanga.temporal.hour.Hour(24 * (daily_panchaanga.jd_sunset - jd)).toString(format=panchaanga.fmt)
    saangava = jyotisha.panchaanga.temporal.hour.Hour(24 * (daily_panchaanga.day_length_based_periods.saangava.jd_start - jd)).toString(
      format=panchaanga.fmt)
    rahu = '%s--%s' % (
      jyotisha.panchaanga.temporal.hour.Hour(24 * (daily_panchaanga.day_length_based_periods.raahu.jd_start - jd)).toString(
        format=panchaanga.fmt),
      jyotisha.panchaanga.temporal.hour.Hour(24 * (daily_panchaanga.day_length_based_periods.raahu.jd_end - jd)).toString(
        format=panchaanga.fmt))
    yama = '%s--%s' % (
      jyotisha.panchaanga.temporal.hour.Hour(24 * (daily_panchaanga.day_length_based_periods.yama.jd_start - jd)).toString(
        format=panchaanga.fmt),
      jyotisha.panchaanga.temporal.hour.Hour(24 * (daily_panchaanga.day_length_based_periods.yama.jd_end - jd)).toString(
        format=panchaanga.fmt))

    if daily_panchaanga.solar_sidereal_date_sunset.month_transition is None:
      month_end_str = ''
    else:
      _m = daily_panchaangas[d - 1].solar_sidereal_date_sunset.month
      if daily_panchaanga.solar_sidereal_date_sunset.month_transition >= daily_panchaangas[d + 1].jd_sunrise:
        month_end_str = '\\mbox{%s{\\tiny\\RIGHTarrow}\\textsf{%s}}' % (
          jyotisha.names.NAMES['RASHI_NAMES'][scripts[0]][_m], jyotisha.panchaanga.temporal.hour.Hour(
            24 * (daily_panchaanga.solar_sidereal_date_sunset.month_transition - daily_panchaangas[d + 1].julian_day_start)).toString(format=panchaanga.fmt))
      else:
        month_end_str = '\\mbox{%s{\\tiny\\RIGHTarrow}\\textsf{%s}}' % (
          jyotisha.names.NAMES['RASHI_NAMES'][scripts[0]][_m], jyotisha.panchaanga.temporal.hour.Hour(
            24 * (daily_panchaanga.solar_sidereal_date_sunset.month_transition - daily_panchaanga.julian_day_start)).toString(format=panchaanga.fmt))

    month_data = '\\sunmonth{%s}{%d}{%s}' % (
      jyotisha.names.NAMES['RASHI_NAMES'][scripts[0]][daily_panchaanga.solar_sidereal_date_sunset.month], daily_panchaanga.solar_sidereal_date_sunset.day,
      month_end_str)

    if currWeek < 6:
      month_text += '\n' + ('\\caldata{\\textcolor{%s}{%s}}{%s{%s}}%%' %
                            (day_colours[daily_panchaanga.date.get_weekday()], dt, month_data,
                             jyotisha.names.get_chandra_masa(daily_panchaanga.lunar_month_sunrise,
                                                             jyotisha.names.NAMES, scripts[0])))
      month_text += '\n' + ('{\\sundata{%s}{%s}{%s}}%%' % (sunrise, sunset, saangava))
      month_text += '\n' + ('{\\tnyk{%s}%%\n{%s}%%\n{%s}%%\n{%s}}%%' % (tithi_data_str, nakshatra_data_str,
                                                                        yoga_data_str, karana_data_str))
      month_text += '\n' + ('{\\rahuyama{%s}{%s}}%%' % (rahu, yama))

      # Using set as an ugly workaround since we may have sometimes assigned the same
      # festival to the same day again!
      month_text += '\n' + ('{%s}' % '\\eventsep '.join(
        [f.tex_code(scripts=scripts, timezone=panchaanga.city.timezone, fest_details_dict=fest_details_dict) for f in
         sorted(daily_panchaanga.festival_id_to_instance.values())]))
    else:
      if daily_panchaanga.date.get_weekday() == 0:
        W6D1 = '\n' + ('\\caldata{\\textcolor{%s}{%s}}{%s{%s}}%%' %
                       (day_colours[daily_panchaanga.date.get_weekday()], dt, month_data,
                        jyotisha.names.get_chandra_masa(daily_panchaanga.lunar_month_sunrise,
                                                        jyotisha.names.NAMES, scripts[0])))
        W6D1 += '\n' + ('{\\sundata{%s}{%s}{%s}}%%' % (sunrise, sunset, saangava))
        W6D1 += '\n' + ('{\\tnyk{%s}%%\n{%s}%%\n{%s}%%\n{%s}}%%' % (tithi_data_str, nakshatra_data_str,
                                                                    yoga_data_str, karana_data_str))
        W6D1 += '\n' + ('{\\rahuyama{%s}{%s}}%%' % (rahu, yama))

        # Using set as an ugly workaround since we may have sometimes assigned the same
        # festival to the same day again!
        W6D1 += '\n' + ('{%s}' % '\\eventsep '.join(
          [f.tex_code(scripts=scripts, timezone=Timezone(panchaanga.city.timezone), fest_details_dict=fest_details_dict) for f in sorted(daily_panchaanga.festival_id_to_instance.values())]))
      elif daily_panchaanga.date.get_weekday() == 1:
        W6D2 = '\n' + ('\\caldata{\\textcolor{%s}{%s}}{%s{%s}}%%' %
                       (day_colours[daily_panchaanga.date.get_weekday()], dt, month_data,
                        jyotisha.names.get_chandra_masa(daily_panchaanga.lunar_month_sunrise,
                                                        jyotisha.names.NAMES, scripts[0])))
        W6D2 += '\n' + ('{\\sundata{%s}{%s}{%s}}%%' % (sunrise, sunset, saangava))
        W6D2 += '\n' + ('{\\tnyk{%s}%%\n{%s}%%\n{%s}%%\n{%s}}%%' % (tithi_data_str, nakshatra_data_str,
                                                                    yoga_data_str, karana_data_str))
        W6D2 += '\n' + ('{\\rahuyama{%s}{%s}}%%' % (rahu, yama))

        # Using set as an ugly workaround since we may have sometimes assigned the same
        # festival to the same day again!
        W6D2 += '\n' + ('{%s}' % '\\eventsep '.join(
          [f.tex_code(scripts=scripts, timezone=panchaanga.city.timezone, fest_details_dict=fest_details_dict) for f in sorted(daily_panchaanga.festival_id_to_instance.values())]))
      else:
        # Cannot be here, since we cannot have more than 2 days in week 6 of any month!
        pass

    if daily_panchaanga.date.get_weekday() == 6:
      month_text += '\n' + ("\\\\ \\hline %%END OF WEEK %d" % (currWeek))
      currWeek += 1
    else:
      if currWeek < 6:
        month_text += '\n' + ("&")

    if m == 12 and dt == 31:
      break

  month_text = month_text.replace('W6D1', W6D1)
  month_text = month_text.replace('W6D2', W6D2)
  print(month_text)

  if currWeek < 6:
    for i in range(daily_panchaanga.date.get_weekday() + 1, 6):
      print("{}  &")
    if daily_panchaanga.date.get_weekday() != 6:
      print("\\\\ \\hline")
  print('\\end{tabular}')
  print('\n\n')

  print(template_lines[-2][:-1])
  print(template_lines[-1][:-1])


def main():
  [city_name, latitude, longitude, tz] = sys.argv[1:5]
  year = int(sys.argv[5])

  scripts = [sanscript.DEVANAGARI]  # Default script is devanagari

  if len(sys.argv) == 7:
    scripts = sys.argv[6].split(",")

  # logging.debug(script)

  city = City(city_name, latitude, longitude, tz)
  panchaanga = annual.get_panchaanga_for_civil_year(city=city, year=year, scripts=scripts)

  panchaanga.update_festival_details()

  write_monthly_tex(panchaanga)
  # panchaanga.writeDebugLog()


if __name__ == '__main__':
  main()
