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
#------------------------------
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
import slimit
import bs4
from slimit.parser import Parser
from slimit.visitors import nodevisitor
from slimit import ast


class Obsfucator(object):
    def __init__(self, config):
        self.ids_found = set()
        self.classes_found = set()
        self.id_map = {}
        self.class_map = {}
        self.config = config
        # TODO: figure out if we want to keep this huge class and move the logger
        # object into the appropriate scope
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
        all_css_files = list(filter( lambda fn: bool(re.search("\.css$", fn))
                              , find_all_files(self.config.css)
                              ))
        self.logger.info(all_css_files)
        all_html_files = list(filter( lambda fn: bool(re.search("\.html$", fn))
                               , find_all_files(self.config.views)
                               ))
        self.logger.info(all_html_files)
        all_js_files = list(filter( lambda fn: bool(re.search("\.js$", fn))
                             , find_all_files(self.config.js)
                             ))
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
            for tag in soup.html.find_all("style"):
                self.processCss(tag.string)

        self.logger.info("mapping classes and ids to new names...")
        # maps all classes and ids found to shorter names
        self.generateMaps()

        # optimize everything
        self.logger.info("munching css files...")
        
        for path in all_css_files:
            css = Util.fileGetContents(path)
            replaced_css = self.optimizeCss(css)
            new_path = path + ".obsfucated"
            with open(new_path, 'w') as f:
                f.write(replaced_css)

        self.logger.info("munching html files...")
        for path in all_html_files:
            html = Util.fileGetContents(path)
            replaced_html = self.optimizeHtml(html)
            new_path = path + ".obsfucated"
            with open(new_path, 'w') as f:
                f.write(replaced_html)

        self.logger.info("munching js files...")
        for path in all_js_files:
            js_content = Util.fileGetContents(path)
            replaced_js = self.optimizeJavascript(js_content)
            new_path = path + ".obsfucated"
            with open(new_path, 'w') as f:
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
            if node.type == 'qualified-rule':
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
        for class_name, suffix in zip(self.classes_found, selector_translation_generator):
            # apply the configured prefix
            new_class_name = "{prefix}{suffix}".format( prefix=self.config.prefix
                                                      , suffix=suffix
                                                      )
            # adblock extensions may block class "ad" so we should never
            # generate it
            while new_class_name == "ad":
                new_class_name = "{prefix}{suffix}".format( prefix=self.config.prefix
                                                          , suffix=next(selector_translation_generator)
                                                          )

            self.class_map[class_name] = new_class_name

        for id_name, suffix in zip(self.ids_found, selector_translation_generator):
            # apply the configured prefix
            new_id_name = "{prefix}{suffix}".format( prefix=self.config.prefix
                                                      , suffix=suffix
                                                      )
            while new_id_name == "ad":
                new_id_name = next(selector_translation_generator)
                new_id_name = "{prefix}{suffix}".format( prefix=self.config.prefix
                                                       , suffix=next(selector_translation_generator)
                                                       )

            self.id_map[id_name] = new_id_name


    def addId(self, selector):
        """adds a single id to the master list of ids

        Arguments:
        selector -- single id to add

        Returns:
        void

        """
        if selector in self.config.ignore or id == '#':
            return

        self.ids_found.add(selector)


    def addClass(self, class_name):
        """adds a single class to the master list of classes

        Arguments:
        class_name -- single class to add

        Returns:
        None

        """
        if class_name in self.config.ignore or class_name is '.':
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
            if node.type == 'qualified-rule':
                obsfucate_selector(node.prelude)

            elif node.type == 'at-rule':
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
            if x and x in self.class_map:
                return self.class_map[x]
            return x

        def rewrite_id(x):
            if x and x in self.id_map:
                return self.id_map[x]
            return x

        soup = bs4.BeautifulSoup(html, "html.parser")
        for tag in soup.html.find_all():            
            new_classes = list(map(rewrite_class, filter(lambda y: y is not None, tag.get_attribute_list('class'))))
            if new_classes:
                tag['class'] = new_classes

            new_ids = list(map(rewrite_id, filter(lambda y: y is not None, tag.get_attribute_list('id'))))
            if new_ids:
                tag['id'] = new_ids

        for tag in soup.html.find_all('style'):
            if tag.string is not None:
                tag.string = self.optimizeCss(tag.string) 

        for tag in soup.html.find_all('script'):
            if tag.string is not None:
                tag.string = self.optimizeJavascript(tag.string)

        return str(soup)


    def optimizeJavascript(self, js_content):
        """optimizes javascript for a specific file

        Arguments:
        js_content -- string containing javascript to optimize

        Returns:
        string -- contents to replace file with

        """
        if not js_content:
            return js_content

        parser = Parser()
        tree = parser.parse(js_content)

        for node in nodevisitor.visit(tree):
            if isinstance(node, ast.String):
                # apparently the value includes the string literal characters so we
                # need to remove those to get the contents of the string
                string_contents = node.value.rstrip("'").lstrip("'")
                # TODO: look for class names within the string instead. Right
                # now the replace inside javascript only works for elm generated
                # javascript using elm-css

                # We get to conviently ignore the proper escaping of any characters
                # inside the new value for the string because we are only replacing
                # css selectors with different valid css selectors restricted to
                # string.ascii_letters, so there should never be any special
                # characters to replace. TODO: maybe put a regex here to make sure
                # that the new value only contains [a-zA-Z]+ as we assume it does
                if string_contents in self.class_map:
                    new_value = "'{}'".format(self.class_map[string_contents])
                    self.logger.info("replacing {} with {}".format(node.value, new_value))
                    node.value = new_value
                if string_contents in self.id_map:
                    new_value = "'{}'".format(self.id_map[string_contents])
                    self.logger.info("replacing {} with {}".format(node.value, new_value))
                    node.value = new_value

        return tree.to_ecma()

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
