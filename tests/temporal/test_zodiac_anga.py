from jyotisha.panchaanga.temporal.zodiac import angas


def test_minus():
  a1 = angas.Anga(index=27, anga_type_id=angas.AngaType.NAKSHATRA.name)
  a2 = angas.Anga(index=1, anga_type_id=angas.AngaType.NAKSHATRA.name)
  assert a1 - a2 == -1
  assert a2 - a1 == 1
  assert a1 - 1 == angas.Anga(index=26, anga_type_id=angas.AngaType.NAKSHATRA.name)
  assert a2 - 1 == a1
  assert a1 + 1 == a2
  assert str(a1 + .5) == str(angas.Anga(index=0.5, anga_type_id=angas.AngaType.NAKSHATRA.name))


def test_comparison():
  a1 = angas.Anga(index=27, anga_type_id=angas.AngaType.NAKSHATRA.name)
  a3 = angas.Anga(index=27, anga_type_id=angas.AngaType.NAKSHATRA.name)
  a2 = angas.Anga(index=1, anga_type_id=angas.AngaType.NAKSHATRA.name)
  assert a1 < a2
  assert a1 == a3


def test_hashability():
  a1 = angas.Anga(index=27, anga_type_id=angas.AngaType.NAKSHATRA.name)
  a3 = angas.Anga(index=27, anga_type_id=angas.AngaType.NAKSHATRA.name)
  a2 = angas.Anga(index=1, anga_type_id=angas.AngaType.NAKSHATRA.name)
  set([a1, a2, a3])
  


def test_get_name():
  a1 = angas.Anga(index=27, anga_type_id=angas.AngaType.NAKSHATRA.name)
  a2 = angas.Anga(index=1, anga_type_id=angas.AngaType.NAKSHATRA.name)
  assert a1.get_name() == "rEvatI"
  assert a2.get_name() == "azvinI"
