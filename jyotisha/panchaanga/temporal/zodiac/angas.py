from numbers import Number

import methodtools
from jyotisha import names

from sanskrit_data.schema import common

NAME_TO_TYPE = {}


class AngaType(common.JsonObject):
  # The below class variables are declared here, but instantiated later.
  TITHI = None
  TITHI_PADA = None
  NAKSHATRA = None
  NAKSHATRA_PADA = None
  RASHI = None
  YOGA = None
  KARANA = None
  SIDEREAL_MONTH = None
  TROPICAL_MONTH = None
  SOLAR_NAKSH = None
  SOLAR_NAKSH_PADA = None

  def __init__(self, name, num_angas, weight_moon, weight_sun, mean_period_days=None, names_dict=None):
    super(AngaType, self).__init__()
    self.name = name
    self.num_angas = num_angas
    self.arc_length = 360.0 / num_angas
    self.weight_moon = weight_moon
    self.weight_sun = weight_sun
    self.mean_period_days = mean_period_days
    if names_dict is None:
      key = name + "_NAMES"
      if name == 'SOLAR_NAKSH':
        key = 'NAKSHATRA'
      elif name == 'SIDEREAL_MONTH':
        key = 'CHANDRA_MASA_NAMES'
      if key in names.NAMES:
        self.names_dict = names.NAMES[key]
    NAME_TO_TYPE[self.name] = self

  def add(self, a, b):
    if b < 1:
      offset_index = (a + b) % self.num_angas
    else:
      offset_index = (a - 1 + b) % self.num_angas + 1
    return offset_index

  def __hash__(self):
    return hash(self.name)

  def __repr__(self):
    return self.name

  def __eq__(self, other):
    # Overriding for speed.
    return self.name == other.name


AngaType.TITHI = AngaType(name='TITHI', num_angas=30, weight_moon=1, weight_sun=-1, mean_period_days=29.530588)
AngaType.TITHI_PADA = AngaType(name='TITHI_PADA', num_angas=120, weight_moon=1, weight_sun=-1, mean_period_days=29.530588)
AngaType.NAKSHATRA = AngaType(name='NAKSHATRA', num_angas=27, weight_moon=1, weight_sun=0, mean_period_days=27.321661)
AngaType.NAKSHATRA_PADA = AngaType(name='NAKSHATRA_PADA', num_angas=108, weight_moon=1, weight_sun=0, mean_period_days=27.321661)
AngaType.RASHI = AngaType(name='RASHI', num_angas=12, weight_moon=1, weight_sun=0, mean_period_days=27.321661)
AngaType.YOGA = AngaType(name='YOGA', num_angas=27, weight_moon=1, weight_sun=1, mean_period_days=29.541)
AngaType.KARANA = AngaType(name='KARANA', num_angas=60, weight_moon=1, weight_sun=-1, mean_period_days=29.4)
AngaType.SIDEREAL_MONTH = AngaType(name='SIDEREAL_MONTH', num_angas=12, weight_moon=0, weight_sun=1, mean_period_days=365.242)
AngaType.TROPICAL_MONTH = AngaType(name='TROPICAL_MONTH', num_angas=12, weight_moon=0, weight_sun=1, mean_period_days=365.242)
AngaType.SOLAR_NAKSH = AngaType(name='SOLAR_NAKSH', num_angas=27, weight_moon=0, weight_sun=1, mean_period_days=365.242)
AngaType.SOLAR_NAKSH_PADA = AngaType(name='SOLAR_NAKSH_PADA', num_angas=108, weight_moon=0, weight_sun=1, mean_period_days=365.242)

class Anga(common.JsonObject):
  def __init__(self, index, anga_type_id):
    super(Anga, self).__init__()
    self.index = index
    self.anga_type_id = anga_type_id

  @methodtools.lru_cache()
  @classmethod
  def get_cached(self, index, anga_type_id):
    return Anga(index=index, anga_type_id=anga_type_id)

  def get_name(self, script="hk"):
    name_dict = NAME_TO_TYPE[self.anga_type_id].names_dict
    if self.anga_type_id == AngaType.SIDEREAL_MONTH.name:
      return names.get_chandra_masa(month=self.index, NAMES=names.NAMES, script=script)
    elif name_dict is not None:
      return name_dict[script][self.index]
    else:
      return None

  def get_type(self):
    return NAME_TO_TYPE[self.anga_type_id]

  def __repr__(self):
    return "%s: %02d" % (self.anga_type_id, self.index)

  def __sub__(self, other):
    """ 
    
    Consider the 27 nakshatras. 
    Expectations: 
      - nakshatra 1 - nakshatra 27 = 1 (not -26).
      - nakshatra 27 - nakshatra 1 = -1 (not 26).
    
    :return: 
    """
    if isinstance(other, Number):
      # We're offsetting angas.
      offset_index = (self.index - other - 1) % self.get_type().num_angas + 1
      return Anga.get_cached(index=offset_index, anga_type_id=self.anga_type_id)
    else:
      # In this case, we're measuring gap between angas.
      # Below is skipped for efficiency.
      # if self.anga_type_id != other.anga_type_id: raise ValueError("anga_type mismatch!", (self.anga_type_id, other.anga_type_id))
      num_angas = NAME_TO_TYPE[self.anga_type_id].num_angas
      gap = min((self.index - other.index) % num_angas, (other.index - self.index) % num_angas)
      if (self.index - 1 + gap) % num_angas == other.index - 1:
        return -gap
      else:
        return gap

  def __mod__(self, other):
    # We avoid if isinstance(other, Number) for efficiency.
    # We don't construct an anga object to avoid confusion between shukla and kRShNa paxa tithis. 
    return self.index % other

  def __add__(self, other):
    # Addition is only for offsetting an anga.
    # We avoid if isinstance(other, Number) for efficiency.
    if other < 1:
      offset_index = (self.index + other) % NAME_TO_TYPE[self.anga_type_id].num_angas
    else:
      offset_index = (self.index - 1 + other) % NAME_TO_TYPE[self.anga_type_id].num_angas + 1
    return Anga.get_cached(index=offset_index, anga_type_id=self.anga_type_id)

  def __lt__(self, other):
   return self - other < 0

  def __gt__(self, other):
    return self - other > 0

  def __ge__(self, other):
    return self > other or self == other

  def __le__(self, other):
    return self < other or self == other

  def __eq__(self, other):
    return self.index == other.index

  def __hash__(self):
    return super(Anga, self).__hash__()


class BoundaryAngas(common.JsonObject):
  def __init__(self, start, end, interval=None):
    super(BoundaryAngas, self).__init__()
    self.start = start
    self.end = end
    self.interval = interval

  def to_tuple(self):
    return (None if self.start is None else self.start.index, None if self.end is None else self.end.index)

  def __repr__(self):
    return "%s-%s %s" % (str(self.start), str(self.end), str(self.interval))