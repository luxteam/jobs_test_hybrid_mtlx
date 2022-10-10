import argparse
import os
import subprocess
import psutil
import json
import platform
from datetime import datetime
from shutil import copyfile, copytree, move, rmtree
import sys
from utils import is_case_skipped
from subprocess import PIPE, Popen
import traceback
from time import time

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *
from jobs_launcher.core.system_info import get_gpu


def copy_test_cases(args):
    try:
        copyfile(os.path.realpath(os.path.join(os.path.dirname(
            __file__), '..', 'Tests', args.test_group, 'test_cases.json')),
            os.path.realpath(os.path.join(os.path.abspath(
                args.output), 'test_cases.json')))

        cases = json.load(open(os.path.realpath(
            os.path.join(os.path.abspath(args.output), 'test_cases.json'))))

        with open(os.path.join(os.path.abspath(args.output), 'test_cases.json'), 'r') as json_file:
            cases = json.load(json_file)

        if os.path.exists(args.test_cases) and args.test_cases:
            with open(args.test_cases) as file:
                test_cases = json.load(file)['groups'][args.test_group]
                if test_cases:
                    necessary_cases = [
                        item for item in cases if item['case'] in test_cases]
                    cases = necessary_cases

            with open(os.path.join(args.output, 'test_cases.json'), "w+") as file:
                json.dump(duplicated_cases, file, indent=4)
    except Exception as e:
        main_logger.error('Can\'t load test_cases.json')
        main_logger.error(str(e))
        exit(-1)


def copy_baselines(args, case, baseline_path, baseline_path_tr):
    try:
        copyfile(os.path.join(baseline_path_tr, case['case'] + CASE_REPORT_SUFFIX),
                 os.path.join(baseline_path, case['case'] + CASE_REPORT_SUFFIX))

        with open(os.path.join(baseline_path, case['case'] + CASE_REPORT_SUFFIX)) as baseline:
            baseline_json = json.load(baseline)

        for thumb in [''] + THUMBNAIL_PREFIXES:
            if os.path.exists(os.path.join(baseline_path_tr, baseline_json[thumb + 'render_color_path'])):
                copyfile(os.path.join(baseline_path_tr, baseline_json[thumb + 'render_color_path']),
                         os.path.join(baseline_path, baseline_json[thumb + 'render_color_path']))
    except:
        main_logger.error('Failed to copy baseline ' +
                                      os.path.join(baseline_path_tr, case['case'] + CASE_REPORT_SUFFIX))


def prepare_empty_reports(args, current_conf):
    main_logger.info('Create empty report files')

    baseline_path = os.path.join(args.output, os.path.pardir, os.path.pardir, os.path.pardir, 'Baseline', args.test_group)

    if not os.path.exists(baseline_path):
        os.makedirs(baseline_path)
        os.makedirs(os.path.join(baseline_path, 'Color'))

    baseline_dir = 'hybrid_mtlx_autotests_baselines'

    if platform.system() == 'Windows':
        baseline_path_tr = os.path.join('c:/TestResources', baseline_dir, args.test_group)
    else:
        baseline_path_tr = os.path.expandvars(os.path.join('$CIS_TOOLS/../TestResources', baseline_dir, args.test_group))

    copyfile(os.path.abspath(os.path.join(args.output, '..', '..', '..', '..', 'jobs_launcher',
                                          'common', 'img', 'error.png')), os.path.join(args.output, 'Color', 'failed.jpg'))

    with open(os.path.join(os.path.abspath(args.output), "test_cases.json"), "r") as json_file:
        cases = json.load(json_file)

    for case in cases:
        if is_case_skipped(case, current_conf):
            case['status'] = 'skipped'

        if case['status'] == 'inprogress':
            case['status'] = 'active'
        elif case['status'] == 'inprogress_observed':
            case['status'] = 'observed'

        test_case_report = RENDER_REPORT_BASE.copy()
        test_case_report['test_case'] = case['case']
        test_case_report['render_device'] = get_gpu()
        test_case_report['render_duration'] = -0.0
        test_case_report['script_info'] = case['script_info']
        test_case_report['test_group'] = args.test_group
        test_case_report['tool'] = 'HybridPro'
        test_case_report['date_time'] = datetime.now().strftime(
            '%m/%d/%Y %H:%M:%S')

        if case['status'] == 'skipped':
            test_case_report['test_status'] = 'skipped'
            test_case_report['file_name'] = f"{case['case']}.jpg"
            test_case_report['render_color_path'] = os.path.join('Color', test_case_report['file_name'])
            test_case_report['group_timeout_exceeded'] = False

            try:
                skipped_case_image_path = os.path.join(args.output, 'Color', test_case_report['file_name'])
                if not os.path.exists(skipped_case_image_path):
                    copyfile(os.path.join(args.output, '..', '..', '..', '..', 'jobs_launcher', 
                        'common', 'img', 'skipped.jpg'), skipped_case_image_path)
            except OSError or FileNotFoundError as err:
                main_logger.error(f"Can't create img stub: {str(err)}")
        else:
            test_case_report['test_status'] = 'error'
            test_case_report['file_name'] = 'failed.jpg'
            test_case_report['render_color_path'] = os.path.join('Color', 'failed.jpg')

        case_path = os.path.join(args.output, case['case'] + CASE_REPORT_SUFFIX)

        with open(case_path, 'w') as f:
            f.write(json.dumps([test_case_report], indent=4))

        copy_baselines(args, case, baseline_path, baseline_path_tr)
    with open(os.path.join(args.output, 'test_cases.json'), 'w+') as f:
        json.dump(cases, f, indent=4)


def save_results(args, case, test_case_status, render_time = 0.0):
    with open(os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX), "r") as file:
        test_case_report = json.loads(file.read())[0]
        test_case_report["test_status"] = test_case_status
        test_case_report["render_time"] = render_time
        test_case_report["render_log"] = os.path.join("render_tool_logs", f"{case['case']}.log")
        test_case_report["testing_start"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        test_case_report["number_of_tries"] += 1
        test_case_report["group_timeout_exceeded"] = False

        image_output_path = os.path.join(os.path.split(args.tool)[0], "img_00000.png")

        if test_case_status == "timeout_exceeded":
            test_case_report["testcase_timeout_exceeded"] = True
        elif test_case_status != "error":
            if os.path.exists(image_output_path):
                test_case_report["file_name"] = f"{case['case']}.png"
                test_case_report["render_color_path"] = os.path.join("Color", test_case_report["file_name"])
                move(image_output_path, os.path.join(args.output, test_case_report["render_color_path"]))
            else:
                test_case_report["message"] = ["Output image not found"]

    with open(os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX), "w") as file:
        json.dump([test_case_report], file, indent=4)


def execute_tests(args, current_conf):
    rc = 0

    with open(os.path.join(os.path.abspath(args.output), "test_cases.json"), "r") as json_file:
        cases = json.load(json_file)

    process = None
    material_files = None

    for case in [x for x in cases if not is_case_skipped(x, current_conf)]:
        try:
            tool_absolute_path = os.path.abspath(args.tool)
            tool_path, tool_name = os.path.split(tool_absolute_path)

            material_files = os.listdir(os.path.join(args.res_path, case["material_name"]))

            material_path = os.path.join(args.res_path, case["material_name"], "material.mtlx")

            if platform.system() == "Windows":
                execution_script = f"cd {tool_path} && {tool_name} {material_path}"

                script_name = f"{case['case']}.bat"
                execution_script_path = os.path.join(args.output, script_name)
                with open(execution_script_path, "w") as f:
                    f.write(execution_script)
            else:
                # Linux system
                execution_script = f"cd {tool_path}; {tool_name} {material_path}"

                script_name = f"{case['case']}.sh"
                execution_script_path = os.path.join(args.output, script_name)
                with open(execution_script_path, "w") as f:
                    f.write(execution_script)

                os.system(f"chmod +x {execution_script_path}")

            for material_file in material_files:
                src_path = os.path.join(args.res_path, case["material_name"], material_file)
                dest_path = os.path.join(tool_path, "materials", material_file)

                if os.path.isdir(src_path):
                    if os.path.exists(dest_path):
                        rmtree(dest_path)

                    copytree(src_path, dest_path)
                else:
                    if os.path.exists(dest_path):
                        os.remove(dest_path)

                    copyfile(src_path, dest_path)

            process = psutil.Popen(execution_script_path, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            start_time = time()

            process.communicate(timeout=args.timeout)

            save_results(args, case, "passed", render_time=time() - start_time)
        except Exception as e:
            for child in reversed(process.children(recursive=True)):
                child.terminate()
            process.terminate()

            if isinstance(e, subprocess.TimeoutExpired):
                save_results(args, case, "timeout_exceeded")
            else:
                save_results(args, case, "error")

            main_logger.error(f"Failed to execute test case (try #{current_try}): {str(e)}")
            main_logger.error(f"Traceback: {traceback.format_exc()}")
            rc = -1
        finally:
            stdout, stderr = process.communicate(timeout=args.timeout)

            log_path = os.path.join(args.output, "render_tool_logs", f"{case['case']}.log")

            with open(log_path, "wb") as file:
                file.write(stdout)
                file.write(stderr)

            for material_file in material_files:
                target_path = os.path.join(tool_path, "materials", material_file)

    return rc


def createArgsParser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--tool", required=True, metavar="<path>")
    parser.add_argument("--output", required=True, metavar="<dir>")
    parser.add_argument("--test_group", required=True)
    parser.add_argument("--res_path", required=True)
    parser.add_argument("--test_cases", required=True)
    parser.add_argument('--timeout', required=False, default=180)
    parser.add_argument('--update_refs', required=True)

    return parser


if __name__ == '__main__':
    main_logger.info('simpleRender start working...')


    args = createArgsParser().parse_args()

    try:
        if not os.path.exists(os.path.join(args.output, "Color")):
            os.makedirs(os.path.join(args.output, "Color"))
        if not os.path.exists(os.path.join(args.output, "render_tool_logs")):
            os.makedirs(os.path.join(args.output, "render_tool_logs"))

        render_device = get_gpu()
        system_pl = platform.system()
        current_conf = set(platform.system()) if not render_device else {platform.system(), render_device}
        main_logger.info(f"Detected GPUs: {render_device}")
        main_logger.info(f"PC conf: {current_conf}")
        main_logger.info("Creating predefined errors json...")

        copy_test_cases(args)
        prepare_empty_reports(args, current_conf)
        exit(execute_tests(args, current_conf))
    except Exception as e:
        main_logger.error(f"Failed during script execution. Exception: {str(e)}")
        main_logger.error(f"Traceback: {traceback.format_exc()}")
        exit(-1)
