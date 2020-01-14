#!/usr/bin/env python3

import requests

from github_connect import GitHub
from functools import partial
from multiprocessing.pool import ThreadPool as Pool
from os import sep, getenv
from os.path import isdir, sys


def download_from_repo(github_token, org, repo, branch, globs, extract_dir):
    """
    Takes github info and file globs and downloads files from github using multiple processes
    :param org: github organization or person
    :param repo: github repo name
    :param branch: the branch name
    :param globs: list of strings in glob format of what to extract
    :return:
    """
    pool_size = 5

    with GitHub(github_token) as gh:
        listing = gh.list(org, repo, branch, globs)
        dest = "{0}{1}{2}".format(
            extract_dir, repo, sep
        )
        with Pool(processes=pool_size) as pool:
            with requests.Session() as s:
                r = [
                    x
                    for x in pool.imap_unordered(
                        partial(
                            gh.raw,
                            request_session=s,
                            org=org,
                            repo=repo,
                            branch=branch,
                            dest_dir=dest,
                        ),
                        listing,
                    )
                ]


def update_globs(new_path, globs):
    """
    Depending if the repo is local or we downloaded it we need to update the globs to match
    the final version of the repo to use
    :param new_path: new_path to update the globs with
    :param globs: list of globs to update
    """
    new_globs = []
    for item in globs:
        new_globs.append("{}{}".format(new_path, item))
    return new_globs


def local_or_upstream(github_token, extract_dir, list_of_contents):
    """
    This goes through the list_of_contents and check for each repo specified
    If a local version exists otherwise we download it from the upstream repo on Github
    Local version of the repo should be in the same folder as the documentation/ folder.
    """
    for content in list_of_contents:
        repo_name = "../" + content["repo_name"] + sep
        if isdir(repo_name):
            print("\x1b[32mINFO\x1b[0m: Local version of {} found".format(
                content["repo_name"]))
            content["globs"] = update_globs(
                repo_name,
                content["globs"],
            )
        elif github_token != "False":
            print(
                "\x1b[32mINFO\x1b[0m: No local version of {} found, downloading content from upstream version".format(
                    content["repo_name"]
                )
            )
            download_from_repo(github_token,
                               content["org_name"],
                               content["repo_name"],
                               content["branch"],
                               content["globs"],
                               extract_dir
                               )
            content[
                "globs"
            ] = update_globs(
                "{0}{1}{2}".format(
                    extract_dir,
                    content["repo_name"],
                    sep,
                ),
                content["globs"],
            )
        elif getenv("LOCAL") == 'True':
            print(
                "\x1b[33mWARNING\x1b[0m: Local mode detected: No local version of {} found, no GITHUB_TOKEN available. Documentation is now in degraded mode".format(content["repo_name"]))
            content["action"] = "Not Available"
        else:
            print(
                "\x1b[31mERROR\x1b[0m: No local version of {} found, no GITHUB_TOKEN available.".format(
                    content["repo_name"]
                )
            )
            raise ValueError
    return list_of_contents


def extract_config(configuration):
    """
    This pulls the content from the configuration file at CONFIGURATION_FILE location
    then parses it to populate the list_of_content variable that contains all contents
    that needs to be pulled and processed.
    """
    list_of_contents = []

    for org in configuration:
        for repo in org["repos"]:
            for content in repo["contents"]:
                content_temp = {}
                content_temp["org_name"] = org[
                    "org_name"
                ]
                content_temp["repo_name"] = repo[
                    "repo_name"
                ]
                content_temp["branch"] = content[
                    "branch"
                ]
                content_temp["action"] = content[
                    "action"
                ]
                content_temp["globs"] = content["globs"]

                if (content["action"] == "pull-and-push-folder" or content["action"] == "pull-and-push-file"):
                    content_temp["options"] = content["options"]

                list_of_contents.append(
                    content_temp
                )

    return list_of_contents


def prepare_content(configuration, github_token, extract_dir):
    try:
        list_of_contents = local_or_upstream(
            github_token, extract_dir, extract_config(configuration))
    except:
        if getenv("LOCAL") == 'True':
            print(
                "\x1b[33mWARNING\x1b[0m: Local mode detected: Downloading files failed, documentation is now in degraded mode.")
        else:
            print(
                "\x1b[31mERROR\x1b[0m: Downloading files failed, stoping build.")
            sys.exit(1)
    return list_of_contents