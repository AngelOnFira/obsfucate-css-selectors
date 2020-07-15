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

import sys, re, glob, os
import logging
from operator import itemgetter
from .util import Util, generate_gzip_friendly_tokens, find_all_files

import tinycss2
import bs4
import esprima


class Obsfucator(object):
    def __init__(self, config):
        self.ids_found = set()
        self.classes_found = set()

        self.id_map = {}
        self.class_map = {}

        self.unlinked_html_classes = set()
        self.unlinked_html_ids = set()
        self.config = config
        # TODO: figure out if we want to keep this huge class and move the logger
        # object into the appropriate scope
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        logger = logging.getLogger(__name__)
        ch = logging.StreamHandler()
        if self.config.verbose:
            ch.setLevel(logging.DEBUG)
        else:
            ch.setLevel(logging.ERROR)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        # Log all of the details to file log so build slave runs can be debugged
        fh = logging.FileHandler("main.log")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        self.logger = logger

    def run(self):
        """runs the optimizer and does all the magic

        Returns:
        void

        """
        all_css_files = list(
            filter(
                lambda fn: bool(re.search("\.css$", fn)),
                find_all_files(self.config.css),
            )
        )
        self.logger.info(all_css_files)
        all_html_files = list(
            filter(
                lambda fn: bool(re.search("\.html$", fn)),
                find_all_files(self.config.views),
            )
        )
        self.logger.info(all_html_files)
        all_js_files = list(
            filter(
                lambda fn: bool(re.search("\.js$", fn)), find_all_files(self.config.js)
            )
        )
        self.logger.info(all_js_files)

        self.logger.info("searching for classes and ids...")
        # assume the css file is small enought to be read completely into memory
        # TODO: enforce this assumption by stating the file
        for path in all_css_files:
            self.processCss(Util.fileGetContents(path))

        # also look inside the views for inline styles
        for path in all_html_files:
            contents = Util.fileGetContents(path)
            soup = bs4.BeautifulSoup(contents, "html.parser")
            for tag in soup.find_all("style"):
                self.processCss(tag.string)

        self.logger.info("mapping classes and ids to new names...")
        # maps all classes and ids found to shorter names
        self.generateMaps()

        # optimize everything
        self.logger.info("munching css files...")

        for path in all_css_files:
            css = Util.fileGetContents(path)
            replaced_css = self.optimizeCss(css)
            with open(path, "w") as f:
                f.write(replaced_css)

        self.logger.info("munching html files...")
        for path in all_html_files:
            html = Util.fileGetContents(path)
            replaced_html = self.optimizeHtml(html)
            with open(path, "w") as f:
                f.write(replaced_html)

        self.logger.info("munching js files...")
        for path in all_js_files:
            js_content = Util.fileGetContents(path)
            replaced_js = self.optimizeJavascript(js_content)
            with open(path, "w") as f:
                f.write(replaced_js)

        self.logger.info("done")

        # TODO: compute space savings???

    def processCss(self, contents):
        """processes a single css file to find all classes and ids to replace

        Arguments:
        contents -- string containing css to process

        Returns:
        string

        """

        stylesheet = tinycss2.parse_stylesheet(contents)

        for node in stylesheet:
            if node.type == "qualified-rule":
                for found_class in get_classes_from_token_list(node.prelude):
                    self.addClass(found_class)

                for found_id in get_ids_from_token_list(node.prelude):
                    self.addId(found_id)

    def generateMaps(self):
        """
        loops through classes and ids to process to determine shorter names to use for them
        and creates a dictionary with these mappings

        Returns:
        void

        """
        selector_translation_generator = generate_gzip_friendly_tokens(None)

        # Note that class and id selectors will be unique
        for class_name, suffix in zip(
            self.classes_found, selector_translation_generator
        ):
            # apply the configured prefix
            new_class_name = "{prefix}{suffix}".format(
                prefix=self.config.prefix, suffix=suffix
            )
            # adblock extensions may block class "ad" so we should never
            # generate it
            while new_class_name == "ad":
                new_class_name = "{prefix}{suffix}".format(
                    prefix=self.config.prefix,
                    suffix=next(selector_translation_generator),
                )

            self.class_map[class_name] = new_class_name

        for id_name, suffix in zip(self.ids_found, selector_translation_generator):
            # apply the configured prefix
            new_id_name = "{prefix}{suffix}".format(
                prefix=self.config.prefix, suffix=suffix
            )
            while new_id_name == "ad":
                new_id_name = next(selector_translation_generator)
                new_id_name = "{prefix}{suffix}".format(
                    prefix=self.config.prefix,
                    suffix=next(selector_translation_generator),
                )

            self.id_map[id_name] = new_id_name

    def addId(self, selector):
        """adds a single id to the master list of ids

        Arguments:
        selector -- single id to add

        Returns:
        void

        """
        if selector in self.config.ignore or id == "#":
            return

        self.ids_found.add(selector)

    def addClass(self, class_name):
        """adds a single class to the master list of classes

        Arguments:
        class_name -- single class to add

        Returns:
        None

        """
        if class_name in self.config.ignore or class_name == ".":
            return

        self.classes_found.add(class_name)

    def optimizeCss(self, css):
        """replaces classes and ids with new values in a css file

        Arguments:
        path -- string path to css file to optimize

        Returns:
        string

        """

        def obsfucate_selector(token_list):
            begin_class = False
            for token in token_list:
                if token.type == "literal" and token.value == ".":
                    begin_class = True
                else:
                    if token.type == "ident" and begin_class:
                        if token.value in self.class_map:
                            token.value = self.class_map[token.value]
                    elif token.type == "hash" and token.value in self.id_map:
                        token.value = self.id_map[token.value]
                    begin_class = False

        stylesheet = tinycss2.parse_stylesheet(css)
        for node in stylesheet:
            print(node)
            if node.type == "qualified-rule":
                obsfucate_selector(node.prelude)

            elif node.type == "at-rule":
                if node.content is not None:
                    obsfucate_selector(node.content)

        return "".join(list(map(lambda x: x.serialize(), stylesheet)))

    def optimizeHtml(self, html):
        """replaces classes and ids with new values in an html file

        Uses:
        Muncher.replaceHtml

        Arguments:
        path -- string path to file to optimize

        Returns:
        string

        """

        def rewrite_class(x):
            if x:
                if x in self.class_map:
                    return self.class_map[x]
                else:
                    self.unlinked_html_classes.add(x)
            return x

        def rewrite_id(x):
            if x:
                if x in self.id_map:
                    return self.id_map[x]
                else:
                    self.unlinked_html_ids.add(x)
            return x

        soup = bs4.BeautifulSoup(html, "html.parser")
        print(self.class_map)
        print(self.id_map)
        for tag in soup.find_all():
            new_classes = list(
                map(
                    rewrite_class,
                    filter(lambda y: y is not None, tag.get_attribute_list("class")),
                )
            )
            if new_classes:
                tag["class"] = new_classes

            new_ids = list(
                map(
                    rewrite_id,
                    filter(lambda y: y is not None, tag.get_attribute_list("id")),
                )
            )
            if new_ids:
                tag["id"] = new_ids

            # remember to replace for attributes that point to ids as well
            new_fors = list(
                map(
                    rewrite_id,
                    filter(lambda y: y is not None, tag.get_attribute_list("for")),
                )
            )
            if new_fors:
                tag["for"] = new_fors

        print("There are {} classes in the html that aren't in the stylesheet".format(len(self.unlinked_html_classes)))
        print("There are {} ids in the html that aren't in the stylesheet".format(len(self.unlinked_html_ids)))

        for tag in soup.find_all("style"):
            if tag.string is not None:
                tag.string = self.optimizeCss(tag.string)

        for tag in soup.find_all("script"):
            if tag.string is not None:
                tag.string = self.optimizeJavascript(tag.string)

        return str(soup)

    def analyzeJavascriptString(self, string):
        new_string = ""
        string_words = string.split(" ")

        for word in string_words:
            if len(word) < 2:
                continue

            # Classes
            if word[0] == ".":
                if word[1:] in self.class_map.keys():
                    new_string += ".{} ".format(self.class_map[word[1:]])
                else:
                    new_string += word + " "
            # IDs
            elif word[0] == "#":
                if word[1:] in self.id_map.keys():
                    new_string += "#{} ".format(self.id_map[word[1:]])
                else:
                    new_string += word + " "
        self.logger.info(
            "replacing '{}' with '{}'".format(string, new_string)
        )
        print("replacing '{}' with '{}'".format(string, new_string))

        return new_string.rstrip() if new_string != "" else string

    def optimizeJavascript(self, js_content):
        """optimizes javascript for a specific file

        Arguments:
        js_content -- string containing javascript to optimize

        Returns:
        string -- contents to replace file with

        """

        if not js_content:
            return js_content

        tree = esprima.tokenize(js_content)

        for node in tree:
            if node.type == "String":
                # apparently the value includes the string literal characters so we
                # need to remove those to get the contents of the string
                string_contents = node.value.rstrip("'").rstrip("\"").lstrip("'").lstrip("\"")

                changed_string = self.analyzeJavascriptString(string_contents)
                js_content = re.sub(string_contents, changed_string, js_content)

                is_css_string = True

        return js_content


# Take the raw list of tokens produced by tinycss2 and find all the classnames
# and return them as a list
def get_classes_from_token_list(token_list):
    css_classes = []
    begin_class = False
    for token in token_list:
        if token.type == "literal" and token.value == ".":
            begin_class = True
        elif token.type == "ident" and begin_class:
            css_classes.append(token.value)
            begin_class = False
        else:
            begin_class = False
    return css_classes


# Take the raw list of tokens produced by tinycss2 and find all the ids
# and return them as a list
def get_ids_from_token_list(token_list):
    css_ids = []
    for token in token_list:
        if token.type == "hash":
            css_ids.append(token.value)
    return css_ids
