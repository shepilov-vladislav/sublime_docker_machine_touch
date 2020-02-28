import sublime
import sublime_plugin
import os
from Default import exec
import time
import sys
import logging
import subprocess
import ast


logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.DEBUG)


__version__ = "0.1.0"
__authors__ = ['"Vladislav Shepilov" <shepilov.v@protonmail.com>']


def plugin_loaded():
    pass


class DockerMachineTouchListener(sublime_plugin.EventListener):
    encoding = "utf-8"

    def on_post_save_async(self, view):
        settings = view.settings()
        plugin_settings = sublime.load_settings("sdmt.sublime-settings")
        DOCKER_MACHINE_NAME, file_extensions, watch_paths, method = (
            settings.get(
                "DOCKER_MACHINE_NAME",
                plugin_settings.get(
                    "DOCKER_MACHINE_NAME",
                    os.getenv(
                        "DOCKER_MACHINE_NAME",
                        "default"
                    )
                )
            ),
            settings.get(
                "file_extensions",
                plugin_settings.get("file_extensions", [])
            ),
            settings.get(
                "watch_paths",
                plugin_settings.get("watch_paths", [os.getenv("HOME")])
            ),
            settings.get(
                "method",
                plugin_settings.get("method", "ssh")
            ),
        )
        fname = view.file_name()
        if not self.is_valid_fname(fname, watch_paths, file_extensions):
            return
        saveddir = os.path.dirname(fname)
        if method == "ssh":
            sublime.status_message("Manually saving " + fname)
            cmd = 'docker-machine ssh {} touch -c {}'.format(DOCKER_MACHINE_NAME, fname)
            print(cmd)
            process = exec.AsyncProcess(None, shell_cmd=cmd, env={}, listener=self)
            self.timestamp = process.start_time
        elif method == "docker":
            sublime.status_message("Manually saving " + fname)
            cmd = 'docker run --rm -v "{}":"{}" busybox touch {}'.format(
                saveddir, saveddir, fname
            )
            print(cmd)
            result_env = subprocess.check_output(
                ["docker-machine", "env", DOCKER_MACHINE_NAME]
            )
            data_env = [
                x.replace("export ", "")
                for x in result_env.decode("utf-8").split("\n")
                if x.startswith("export ") and "=" in x
            ]
            env = {
                v.split("=")[0]: ast.literal_eval(v.split("=")[1])
                for v in data_env
            }
            process = exec.AsyncProcess(None, shell_cmd=cmd, env=env, listener=self)
            self.timestamp = process.start_time
        else:
            logger.error("Unknown method: %s", method)

    def is_valid_fname(self, fname, watch_paths, file_extensions):
        valid_path = False
        for path in watch_paths:
            if fname.startswith(path):
                valid_path = True
                break
        valid_ext = True
        if file_extensions:
            valid_ext = fname.split(".")[-1] in file_extensions
        return all([valid_path, valid_ext])

    def on_data(self, process, data):
        print(data)

    def on_finished(self, process):
        exit_code = process.exit_code()
        if exit_code == 0:
            print("\n<<< # Finished use %.2fs\n" % (time.time() - self.timestamp))
        else:
            print("\n<<< ! Unexpected exit %d use %.2fs" % (exit_code, time.time() - self.timestamp))
        self.process = None
