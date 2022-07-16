import json
import os
from datetime import datetime, timezone
from json.decoder import JSONDecodeError
from os import path, remove
from shutil import rmtree, move
from tempfile import mkdtemp

from retriever import reload_scripts, dataset_names
from retriever import download
from retriever.lib.engine_tools import getmd5
from retriever.lib.defaults import HOME_DIR

import sys
import csv
try:
    from .status_dashboard_tools import get_dataset_md5
    from .status_dashboard_tools import diff_generator, diff_generator_spatial, data_shift
    from .status_dashboard_tools import create_dirs
    from .status_dashboard_tools import dataset_type, join_path
    from .status_dashboard_tools import install_postgres
except ImportError as error:
    try:
        from retrieverdash.dashboard_script.status_dashboard_tools import get_dataset_md5
        from retrieverdash.dashboard_script.status_dashboard_tools import diff_generator, diff_generator_spatial, data_shift
        from retrieverdash.dashboard_script.status_dashboard_tools import create_dirs
        from retrieverdash.dashboard_script.status_dashboard_tools import dataset_type,join_path
        from retrieverdash.dashboard_script.status_dashboard_tools import install_postgres
    except ImportError as error:
        pass
# To set location of the path
file_location = os.path.normpath(os.path.dirname(os.path.realpath(__file__)))

# To prevent field size errors when converting to csv
maxInt = sys.maxsize
decrement = True
while decrement:
    try:
        csv.field_size_limit(maxInt)
        decrement = False
    except OverflowError:
        maxInt = int(maxInt / 10)


# The DEV_LIST, useful for testing on less strong machines.
DEV_LIST = ['iris', 'abalone-age', ] #'harvard-forest', 'titanic']
IGNORE = ['activity-timberharvest']


DASH_DETAILS = os.path.join(file_location, "dataset_details.json")
CURRENT_PATH = os.path.join(file_location, 'current')
DATASET_DATA_FOLDER = os.path.join(file_location, 'current', '{dataset_name}')


def check_dataset(dataset):
    md5 = None
    status = None
    reason = None
    diff = None
    dataset_detail = None
    dataset_detail_json = join_path([file_location, "dataset_details.json"])
    try:
        try:
            with open(dataset_detail_json, 'r') as json_file:
                dataset_detail = json.load(json_file)
        except (OSError, JSONDecodeError):
            dataset_detail = dict()
            dataset_detail['dataset_details'] = {}

        if dataset_type(dataset) == 'spatial':
            install_postgres(dataset)

            dir_pathzz = DATASET_DATA_FOLDER.format(dataset_name=dataset.name)

            md5 = getmd5(dir_pathzz, data_type='dir')
            previous_md5 = dataset_detail['dataset_details'][dataset.name]['md5']

            if dataset.name not in dataset_detail['dataset_details'] \
                    or md5 != previous_md5:
                diff = diff_generator_spatial(dataset)
            else:
                for keys in dataset.tables:
                    file_name = '{}.{}'.format(
                        dataset.name.replace('-', '_'), keys)
                    html_file_name = '{}.html'.format(file_name)

                    old_diff = os.path.exists(os.path.join(file_location, 'diffs', html_file_name))
                    if os.path.exists(old_diff):
                        remove(old_diff)
            data_shift(dataset, is_spatial=True)

        else:
            md5 = get_dataset_md5(dataset)
            old_md5 =dataset_detail['dataset_details'][dataset.name]['md5']
            if md5 == old_md5:
                print("wrong KKKKKKKKKKKK")
                # exit()

            if dataset.name not in dataset_detail['dataset_details'] or md5 != old_md5:
                diff = diff_generator(dataset)
            else:
                for keys in dataset.tables:
                    file_name = '{}_{}'.format(
                        dataset.name.replace('-', '_'), keys)
                    html_file_name = '{}.html'.format(file_name)
                    if os.path.exists(join_path([file_location, 'diffs', html_file_name])):
                        remove(join_path([file_location, 'diffs', html_file_name]))
            data_shift(dataset)
        status = True
    except Exception as e:
        reason = str(e)
        status = False
    finally:
        json_file_details = dataset_detail
        json_file_details["dataset_details"][dataset.name] = {
            "md5": md5,
            "status": status,
            "reason": reason,
            "diff": diff}
        json_file_details["last_checked_on"] = datetime.now(
            timezone.utc).strftime("%d %b %Y")
        dataset_details_write = open(join_path([file_location, 'dataset_details.json']), 'w')
        json.dump(json_file_details, dataset_details_write,
                  sort_keys=True, indent=4)
        dataset_details_write.close()
        if os.path.exists(join_path([HOME_DIR, 'raw_data', dataset.name])):
            rmtree(join_path([HOME_DIR, 'raw_data', dataset.name]))


def run():
    create_dirs()
    datasets_to_check = []

    # if os.environ.get("RETR_TEST") == "true":
    if 1:
        datasets_to_check = [script for script in reload_scripts()
                             if script.name in DEV_LIST]
    else:
        datasets_to_check = [script for script in reload_scripts()
                             if script.name not in IGNORE]

    for dataset in datasets_to_check:
        print("Checking dataset {}:".format(dataset.name))
        check_dataset(dataset)


if __name__ == '__main__':
    run()
