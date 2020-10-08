from numbers import Number

from jyotisha import names
from jyotisha.names import NAMES
from sanskrit_data.schema import common
from sanskrit_data.schema.common import JsonObject

NAME_TO_TYPE = {}


class AngaType(JsonObject):
  # The below class variables are declared here, but instantiated later.
  TITHI = None
  TITHI_PADA = None
  NAKSHATRA = None
  NAKSHATRA_PADA = None
  RASHI = None
  YOGA = None
  KARANA = None
  SIDEREAL_MONTH = None
  SOLAR_NAKSH = None
  SOLAR_NAKSH_PADA = None

  def __init__(self, name, num_angas, weight_moon, weight_sun, names_dict=None):
    super(AngaType, self).__init__()
    self.name = name
    self.num_angas = num_angas
    self.arc_length = 360.0 / num_angas
    self.weight_moon = weight_moon
    self.weight_sun = weight_sun
    self.names_dict = names_dict
    if names_dict is None:
      key = name + "_NAMES"
      if name == 'SOLAR_NAKSH':
        key = 'NAKSHATRA'
      elif name == 'SIDEREAL_MONTH':
        key = 'CHANDRA_MASA_NAMES'
      if key in NAMES:
        self.names_dict = NAMES[key]
    global NAME_TO_TYPE
    NAME_TO_TYPE[self.name] = self


AngaType.TITHI = AngaType(name='TITHI', num_angas=30, weight_moon=1, weight_sun=-1)
AngaType.TITHI_PADA = AngaType(name='TITHI_PADA', num_angas=120, weight_moon=1, weight_sun=-1)
AngaType.NAKSHATRA = AngaType(name='NAKSHATRA', num_angas=27, weight_moon=1, weight_sun=0)
AngaType.NAKSHATRA_PADA = AngaType(name='NAKSHATRA_PADA', num_angas=108, weight_moon=1, weight_sun=0)
AngaType.RASHI = AngaType(name='RASHI', num_angas=12, weight_moon=1, weight_sun=0)
AngaType.YOGA = AngaType(name='YOGA', num_angas=27, weight_moon=1, weight_sun=1)
AngaType.KARANA = AngaType(name='KARANA', num_angas=60, weight_moon=1, weight_sun=-1)
AngaType.SIDEREAL_MONTH = AngaType(name='SIDEREAL_MONTH', num_angas=12, weight_moon=0, weight_sun=1)
AngaType.SOLAR_NAKSH = AngaType(name='SOLAR_NAKSH', num_angas=27, weight_moon=0, weight_sun=1)
AngaType.SOLAR_NAKSH_PADA = AngaType(name='SOLAR_NAKSH_PADA', num_angas=108, weight_moon=0, weight_sun=1)


class Anga(common.JsonObject):
  def __init__(self, index, anga_type_id):
    self.index = index
    self.anga_type_id = anga_type_id

  def get_name(self, script="hk"):
    name_dict = NAME_TO_TYPE[self.anga_type_id].names_dict
    if self.anga_type_id == AngaType.SIDEREAL_MONTH.name:
      return names.get_chandra_masa(month=self.index, NAMES=NAMES, script=script)
    elif name_dict is not None:
      return name_dict[script][self.index]
    else:
      return None

  def get_type(self):
    return NAME_TO_TYPE[self.anga_type_id]

  def __str__(self):
    return "%s: %02d" % (self.anga_type_id, self.index)

  def __sub__(self, other):
    """ 
    
    Consider the 27 nakshatras. 
    Expectations: 
      - nakshatra 1 - nakshatra 27 = 1 (not -26).
      - nakshatra 27 - nakshatra 1 = -1 (not 26).
    
    :param x: 
    :param y: 
    :return: 
    """
    if isinstance(other, Number):
      offset_index = (self.index - other - 1) % self.get_type().num_angas + 1
      return Anga(index=offset_index, anga_type_id=self.anga_type_id)
    if self.anga_type_id != other.anga_type_id: raise ValueError("anga_type mismatch!", (self.anga_type_id, other.anga_type_id))
    num_angas = NAME_TO_TYPE[self.anga_type_id].num_angas
    gap = min((self.index - other.index) % num_angas, (other.index - self.index) % num_angas)
    if (self.index - 1 + gap) % 27 == other.index - 1:
      return -gap
    else:
      return gap

  def __mod__(self, other):
    if isinstance(other, Number):
      # We don't construct an anga object to avoid confusion between shukla and kRShNa paxa tithis. 
      return self.index % other
    else:
      raise ValueError((self, other))
  
  def __add__(self, other):
    if isinstance(other, Number):
      if other < 1:
        offset_index = (self.index + other) % self.get_type().num_angas
      else:
        offset_index = (self.index - 1 + other) % self.get_type().num_angas + 1
      return Anga(index=offset_index, anga_type_id=self.anga_type_id)
    else:
      raise ValueError(other)

  def __lt__(self, other):
    if isinstance(other, Number):
      return self.index < other
    elif isinstance(other, Anga):
      return self - other < 0
    else:
      raise ValueError(other)

  def __gt__(self, other):
    if isinstance(other, Number):
      return self.index > other
    elif isinstance(other, Anga):
      return self - other > 0
    else:
      raise ValueError(other)

  def __ge__(self, other):
    return self > other or self == other

  def __le__(self, other):
    return self < other or self == other

  def __eq__(self, other):
    if isinstance(other, Number):
      return self.index == other
    else:
      return super(Anga, self).__eq__(other=other)

  def __hash__(self):
    return super(Anga, self).__hash__()
