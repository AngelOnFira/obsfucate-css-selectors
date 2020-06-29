#!/usr/bin/env python3

# Copyright 2017 Th!nk Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ------------------------------
#
# Copyright 2011 Craig Campbell
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import argparse


class Config(object):
    def __init__(self):
        parser = argparse.ArgumentParser(
            description="Obsfucate css selectors in CSS, HTML, and JavaScript files"
        )
        parser.add_argument(
            "--html",
            default="",
            required=True,
            help="comma separated list of directories and files",
        )
        parser.add_argument(
            "--css", default="", help="comma separated list of directories and files"
        )
        parser.add_argument(
            "--js",
            default="",
            help="js files to rewrite (comma separated list of directories and files)",
        )
        parser.add_argument(
            "--view-ext",
            default="html",
            help="sets the extension to look for in the view directory.",
        )
        parser.add_argument(
            "--ignore",
            default="",
            help="comma separated list of classes or ids to ignore when rewriting css (ie .sick_class,#sweet_id)",
        )
        parser.add_argument(
            "--verbose",
            default=False,
            help="output more information while the script runs",
        )
        parser.add_argument(
            "--prefix", default="", help="prefix for generated css class names"
        )
        parser.add_argument("--output", default="", help="output folder")

        args = parser.parse_args()

        self.css = filter(lambda x: bool(x), args.css.split(","))
        self.views = filter(lambda x: bool(x), args.html.split(","))
        self.js = filter(lambda x: bool(x), args.js.split(","))
        self.ignore = [x.lstrip(".") for x in args.ignore.split(",")]
        self.view_extension = "html"
        self.verbose = args.verbose
        self.prefix = args.prefix
        self.output = args.output
