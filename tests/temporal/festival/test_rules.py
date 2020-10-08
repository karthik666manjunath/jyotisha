from pprint import pprint

from jyotisha.panchaanga.temporal.festival import rules


def test_rules_dicts():
  rule_set = rules.RulesCollection()
  pprint(rule_set)
  assert 'pUrNimA~vratam' in rule_set.tree[rules.RulesRepo.LUNAR_MONTH_DIR][rules.RulesRepo.TITHI_DIR]["00"]["15"]
  assert list(rule_set.get_month_anga_fests(month=2, anga_id=1, month_type=rules.RulesRepo.SIDEREAL_SOLAR_MONTH_DIR, anga_type_id=rules.RulesRepo.DAY_DIR).keys()) == ["viSNupadI-vRSabharaviH"]
  assert list(rule_set.get_month_anga_fests(month=1, anga_id=31, month_type=rules.RulesRepo.SIDEREAL_SOLAR_MONTH_DIR, anga_type_id=rules.RulesRepo.DAY_DIR).keys()) == []
