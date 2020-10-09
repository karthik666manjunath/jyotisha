import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path

import methodtools
from sanskrit_data.schema import common


class HinduCalendarEventTiming(common.JsonObject):
  schema = common.recursively_merge_json_schemas(common.JsonObject.schema, ({
    "type": "object",
    "properties": {
      common.TYPE_FIELD: {
        "enum": ["HinduCalendarEventTiming"]
      },
      "month_type": {
        "type": "string",
        "enum": ["lunar_month", "sidereal_solar_month", "tropical_month"],
        "description": "",
      },
      "month_number": {
        "type": "integer",
        "description": "",
      },
      "anga_type": {
        "type": "string",
        "enum": ["tithi", "nakshatra", "yoga", "day"],
        "description": "",
      },
      "anga_number": {
        "type": "integer",
        "description": "",
      },
      "kaala": {
        "type": "string",
        "description": "",
      },
      "priority": {
        "type": "string",
        "description": "",
      },
      "year_start": {
        "type": "integer",
        "description": "",
      },
      "anchor_festival_id": {
        "type": "string",
        "description": "A festival may be (say) 8 days before some other event xyz. The xyz is stored here.",
      },
      "offset": {
        "type": "integer",
        "description": "A festival may be 8 days before some other event xyz. The 8 is stored here.",
      },
    }
  }))

  @classmethod
  def from_details(cls, month_type, month_number, anga_type, anga_number, kaala, year_start):
    timing = HinduCalendarEventTiming()
    timing.month_type = month_type
    timing.month_number = month_number
    timing.anga_type = anga_type
    timing.anga_number = anga_number
    timing.kaala = kaala
    timing.year_start = year_start
    timing.validate_schema()
    return timing


# noinspection PyUnresolvedReferences
class HinduCalendarEvent(common.JsonObject):
  schema = common.recursively_merge_json_schemas(common.JsonObject.schema, ({
    "type": "object",
    "properties": {
      common.TYPE_FIELD: {
        "enum": ["HinduCalendarEvent"]
      },
      "timing": HinduCalendarEventTiming.schema,
      "tags": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "description": "",
      },
      "comments": {
        "type": "string",
        "description": "",
      },
      "image": {
        "type": "string",
        "description": "",
      },
      "description": {
        "type": "object",
        "description": "Language code to text mapping.",
      },
      "names": {
        "type": "object",
        "description": "Language code to text array mapping.",
      },
      "shlokas": {
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "references_primary": {
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "references_secondary": {
        "type": "array",
        "items": {
          "type": "string"
        }
      },
    }
  }))

  def get_storage_file_name(self, base_dir):
    if self.timing.anchor_festival_id is not None:
      return "%(base_dir)s/relative_event/%(anchor_festival_id)s/offset__%(offset)02d/%(id)s__info.toml" % dict(
        base_dir=base_dir,
        anchor_festival_id=self.timing.anchor_festival_id.replace('/','__'),
        offset=self.timing.offset,
        id=self.id.replace('/','__').strip('{}')
      )
    else:
      if self.timing is None or self.timing.month_number is None:
        tag_list = '/'.join(self.tags)
        return "%(base_dir)s/description_only/%(tags)s/%(id)s__info.toml" % dict(
          base_dir=base_dir,
          tags=tag_list,
          id=self.id.replace('/','__').strip('{}')
        )
      else:
        try:
          return "%(base_dir)s/%(month_type)s/%(anga_type)s/%(month_number)02d/%(anga_number)02d/%(id)s__info.toml" % dict(
            base_dir=base_dir,
            month_type=self.timing.month_type,
            anga_type=self.timing.anga_type,
            month_number=self.timing.month_number,
            anga_number=self.timing.anga_number,
            id=self.id.replace('/','__').strip('{}')
          )
        except Exception:
          logging.error(str(self))
          raise 

  def get_url(self):
    from urllib.parse import quote
    return quote(self.get_storage_file_name(base_dir=self.repo.base_url))

  def get_description_string(self, script, include_url=False, include_images=False, use_markup=False,
                             include_shlokas=False, is_brief=False, truncate=False):
    from jyotisha.panchaanga.temporal.festival.rules import summary
    final_description_string = summary.describe_fest(self, include_images, include_shlokas, include_url, is_brief, script,
                                                  truncate, use_markup)

    return final_description_string

def get_festival_rules_map(dir_path, repo=None):
  toml_file_paths = sorted(Path(dir_path).glob("**/*.toml"))
  festival_rules = {}
  if len(toml_file_paths) == 0:
    logging.warning("No festival rule found at %s", dir_path)
    return festival_rules
  for file_path in toml_file_paths:
    event = HinduCalendarEvent.read_from_file(filename=str(file_path))
    event.repo = repo
    festival_rules[event.id] = event
  return festival_rules


def read_old_festival_rules_dict(file_name):
  with open(file_name, encoding="utf-8") as festivals_data:
    festival_rules_dict = json.load(festivals_data)
    for festival_rule in festival_rules_dict:
      festival_rules = {}
      festival_rules[festival_rule.id] = festival_rule
    return festival_rules


DATA_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


class RulesRepo(common.JsonObject):
  LUNAR_MONTH_DIR = "lunar_month"
  SIDEREAL_SOLAR_MONTH_DIR = "sidereal_solar_month"
  RELATIVE_EVENT_DIR = "relative_event"
  DAY_DIR = "day"
  TITHI_DIR = "tithi"
  NAKSHATRA_DIR = "nakshatra"
  YOGA_DIR = "yoga"

  def __init__(self, name, path=None, base_url='https://github.com/sanskrit-coders/adyatithi/tree/master'):
    self.name = name
    self.path = path
    self.base_url = os.path.join(base_url, name)

  def get_path(self):
    #  We don't set the path in __init__ so as to avoid storing machine-specific paths for canonical repos.
    return self.path if self.path is not None else os.path.join(DATA_ROOT, self.name)


rule_repos = [RulesRepo(name="general"), RulesRepo(name="gRhya/general"), RulesRepo(name="tamil"), RulesRepo(name="mahApuruSha/general"), RulesRepo(name="mahApuruSha/kAnchI-maTha"), RulesRepo(name="mahApuruSha/ALvAr"), RulesRepo(name="mahApuruSha/nAyanAr"), RulesRepo(name="temples/venkaTAchala"), RulesRepo(name="temples/Andhra"), RulesRepo(name="temples/Tamil"), RulesRepo(name="temples/Kerala"), RulesRepo(name="temples/Odisha"), RulesRepo(name="temples/North")]


class RulesCollection(common.JsonObject):
  def __init__(self, repos=rule_repos):
    self.repos = repos
    self.relative = {}
    self.name_to_rule = {}
    self.tree = None
    self.set_rule_dicts()

  @methodtools.lru_cache()  # the order is important!
  @classmethod
  def get_cached(cls, repos):
    return RulesCollection(repos=repos)

  def set_rule_dicts(self):
    for repo in self.repos:
      self.name_to_rule.update(get_festival_rules_map(
        os.path.join(DATA_ROOT, repo.get_path()), repo=repo))
    from sanskrit_data import collection_helper
    self.tree = collection_helper.tree_maker(leaves=self.name_to_rule.values(), path_fn=lambda x: x.get_storage_file_name(base_dir="").replace("__info.toml", ""))
    # for fest_name, fest in self.name_to_rule.items():
    #   date = BasicDate(month=fest.timing.month, day=month.timing.month_number)


# Essential for depickling to work.
common.update_json_class_index(sys.modules[__name__])
# logging.debug(common.json_class_index)


