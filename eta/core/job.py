'''
Job infrastructure for running modules in a pipeline.

Copyright 2017, Voxel51, LLC
voxel51.com

Brian Moore, brian@voxel51.com
'''
import os
import subprocess
import sys

from config import Config
import utils


def run(job_config, overwrite=True):
    '''Run the job specified by the JobConfig.

    If the job completes succesfully, the hash of the config file is written to
    disk.

    If the job raises an error, execution is terminated immediately.

    Args:
        job_config: a JobConfig instance
        overwrite: overwrite mode. When True, always run the job. When False,
            only run the job if the config file has changed since the last time
            the job was (succesfully) run

    Returns:
        True/False: if the job was run

    Raises:
        JobConfigError: if the JobConfig was invalid
    '''
    with utils.WorkingDir(job_config.working_dir):
        hasher = utils.MD5FileHasher(job_config.config_path)
        if hasher.has_changed:
            print "Config '%s' changed" % job_config.config_path

        if overwrite or not hasher.has_record or hasher.has_changed:
            print "Starting job '%s'" % job_config.name
            print "Working directory: %s" % os.getcwd()

            code = _run(job_config)
            if code:
                sys.exit()

            hasher.write()

            print "Job '%s' complete" % job_config.name
            return True
        else:
            print "Skipping job '%s'" % job_config.name
            return False

def _run(job_config):
    if job_config.binary:
        # Run binary
        code = subprocess.call([
            job_config.binary,          # binary
            job_config.config_path,     # config file
        ], shell=False)
    elif job_config.script:
        # Run script
        code = subprocess.call([
            job_config.interpreter,     # interpreter
            job_config.script,          # script
            job_config.config_path,     # config file
        ], shell=False)
    elif job_config.custom:
        # Run custom command-line
        code = subprocess.call(
            job_config.custom +         # custom args
            [job_config.config_path],   # config file
            shell=False,
        )
    else:
        raise JobConfigError("Invalid JobConfig")

    return code


class JobConfigError(Exception):
    pass


class JobConfig(Config):
    '''Job configuration settings'''

    def __init__(self, d):
        self.name = self.parse_string(d, "name", default="")
        self.working_dir = self.parse_string(d, "working_dir", default=".")
        self.interpreter = self.parse_string(d, "interpreter", default="python")
        self.script = self.parse_string(d, "script", default=None)
        self.binary = self.parse_string(d, "binary", default=None)
        self.custom = self.parse_array(d, "custom", default=None)
        self.config_path = self.parse_string(d, "config_path")


if __name__ == "__main__":
    run(JobConfig.from_json(sys.argv[1]))