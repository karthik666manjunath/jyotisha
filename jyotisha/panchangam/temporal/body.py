import logging
import math

import swisseph as swe
from scipy.optimize import brentq


class Graha(object):
    SUN = "sun"
    MOON = "moon"
    JUPITER = "jupiter"
    VENUS = "venus"
    MERCURY = "mercury"
    MARS = "mars"
    SATURN = "saturn"

    def __init__(self, body_name):
        self.body_name = body_name

    def _get_swisseph_id(self):
        body_id = -1
        if self.body_name == Graha.SUN:
            body_id = swe.SUN
        elif self.body_name == Graha.MOON:
            body_id = swe.MOON
        elif self.body_name == Graha.JUPITER:
            body_id = swe.JUPITER
        elif self.body_name == Graha.VENUS:
            body_id = swe.VENUS
        elif self.body_name == Graha.MERCURY:
            body_id = swe.MERCURY
        elif self.body_name == Graha.MARS:
            body_id = swe.MARS
        elif self.body_name == Graha.SATURN:
            body_id = swe.SATURN
        return body_id

    def get_longitude(self, jd):
        return swe.calc_ut(jd, self._get_swisseph_id())[0][0]

    def get_longitude_offset(self, jd, offset, ayanamsha_id):
        from jyotisha.panchangam.temporal import Ayanamsha
        return self.get_longitude(jd=jd) - Ayanamsha(ayanamsha_id).get_offset(jd) + offset

    def get_next_raashi_transit(self, jd_start, jd_end, ayanamsha_id):
        """Returns the next transit of the given planet e.g. jupiter
  
      Args:
        float jd_start, jd_end: The Julian Days between which transits must be computed
        int planet  - e.g. sun, jupiter, ...
  
      Returns:
        List of tuples [(float jd_transit, int old_rashi, int new_rashi)]
  
      
    """

        transits = []
        MIN_JUMP = 15  # Random check for a transit every 15 days!
        # Could be tweaked based on planet using a dict?

        curr_L_bracket = jd_start
        curr_R_bracket = jd_start + MIN_JUMP

        while curr_R_bracket <= jd_end:
            L_rashi = math.floor(self.get_longitude_offset(curr_L_bracket, offset=0,
                                                           ayanamsha_id=ayanamsha_id) / 30) + 1
            R_rashi = math.floor(self.get_longitude_offset(curr_R_bracket, offset=0,
                                                           ayanamsha_id=ayanamsha_id) / 30) + 1

            if L_rashi == R_rashi:
                curr_R_bracket += MIN_JUMP
                continue
            else:
                # We have bracketed a transit!
                if L_rashi < R_rashi:
                    target = R_rashi
                else:
                    # retrograde transit
                    target = L_rashi
                try:
                    jd_transit = \
                        brentq(self.get_longitude_offset, curr_L_bracket, curr_R_bracket,
                                        args=((-target + 1) * 30, ayanamsha_id))
                    transits += [(jd_transit, L_rashi, R_rashi)]
                    curr_R_bracket += MIN_JUMP
                    curr_L_bracket = jd_transit + MIN_JUMP
                except ValueError:
                    logging.error('Unable to compute transit of planet;\
                                   possibly could not bracket correctly!\n')
                    return (None, None, None)

        return transits


def get_star_longitude(star, jd):
    from jyotisha.panchangam import data
    import os
    swe.set_ephe_path(os.path.dirname(data.__file__))
    (long, lat, _, _, _, _) = swe.fixstar_ut(star, jd)[0]
    return long