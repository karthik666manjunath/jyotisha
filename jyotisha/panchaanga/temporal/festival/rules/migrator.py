import logging
import os

from indic_transliteration import xsanscript as sanscript
from jyotisha import custom_transliteration
from jyotisha.names import get_chandra_masa, NAMES
# from jyotisha.panchaanga.temporal import festival
from jyotisha.panchaanga.temporal.festival import rules
from jyotisha.util import default_if_none
from sanskrit_data.schema.common import JsonObject

logging.basicConfig(
  level=logging.DEBUG,
  format="%(levelname)s: %(asctime)s {%(filename)s:%(lineno)d}: %(message)s "
)


def migrate_db(dir_path):
  festival_rules_dict = rules.get_festival_rules_map(dir_path)
  output_dir = os.path.join(os.path.dirname(__file__), 'data')
  # import shutil
  # shutil.rmtree(output_dir)
  for event in festival_rules_dict.values():
    logging.info("Migrating %s", event.id)
    event.names = default_if_none(x=event.names, default={})
    sa_names = event.names.get("sa", [])
    ta_names = event.names.get("ta", [])
    if "Mahapurusha" not in ",".join(event.tags):
      event_file_name = event.get_storage_file_name(base_dir=os.path.join(output_dir, "migrated/general"))
    elif "Mahapurusha" in ",".join(event.tags):
      event_file_name = event.get_storage_file_name(base_dir=os.path.join(output_dir, "Mahapurusha/general"))
    logging.debug(event_file_name)
    event.dump_to_file(filename=event_file_name)
    # append_to_event_group_README(event, event_file_name)


def clear_output_dirs():
  import shutil
  for dir in ["lunar_month", "other", "relative_event", "sidereal_solar_month"]:
    shutil.rmtree(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', dir), ignore_errors=True)


if __name__ == '__main__':
  clear_output_dirs()
  migrate_db(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data/general'))
  # migrate_db(os.path.join(os.path.dirname(__file__), 'data/tamil'))
  pass
