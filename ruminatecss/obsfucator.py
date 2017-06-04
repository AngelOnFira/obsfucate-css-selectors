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
from .util import Util, generate_gzip_friendly_tokens

import tinycss
import slimit
import bs4
from slimit.parser import Parser
from slimit.visitors import nodevisitor
from slimit import ast

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)
# Log all of the details to file log so build slave runs can be debugged
fh = logging.FileHandler("main.log")
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

class Obsfucator(object):
    def __init__(self, config):
        self.ids_found = set()
        self.classes_found = set()
        self.id_map = {}
        self.class_map = {}
        self.config = config
        # TODO: figure out if we want to keep this huge class and move the logger
        # object into the appropriate scope
        self.logger = logger

    def run(self):
        """runs the optimizer and does all the magic

        Returns:
        void

        """
        self.logger.info("searching for classes and ids...")


        self.processCss()
        for filepath in self.config.views:
            if not Util.isDir(filepath):
                self.processView(filepath)
                continue
            self.processViewDirectory(filepath)


        self.logger.info("mapping classes and ids to new names...")
        # maps all classes and ids found to shorter names
        self.generateMaps()

        # optimize everything
        self.logger.info("munching css files...")
        self.optimizeFiles(self.config.css, self.optimizeCss)

        self.logger.info("munching html files...")
        self.optimizeFiles(self.config.views, self.config.view_extension)

        self.logger.info("munching js files...")
        self.optimizeFiles(self.config.js, self.optimizeJavascript)

        self.logger.info("done")

        # TODO: compute space savings???

    def processCssDirectory(self, file):
        """processes a directory of css files

        Arguments:
        file -- path to directory

        Returns:
        void

        """
        if ".svn" in file:
            return

        for dir_file in Util.getFilesFromDir(file):
            if Util.isDir(dir_file):
                self.processCssDirectory(dir_file)
                continue

            self.processCssFile(dir_file)

    def processCss(self):
        """gets all css files from config and processes them to see what to replace

        Returns:
        void

        """
        files = self.config.css
        for file in files:
            if not Util.isDir(file):
                self.processCssFile(file)
                continue
            self.processCssDirectory(file)

    def processViewDirectory(self, file):
        """processes a directory of view files

        Arguments:
        file -- path to directory

        Returns:
        void

        """
        if ".svn" in file:
            return

        for dir_file in Util.getFilesFromDir(file):
            if Util.isDir(dir_file):
                self.processViewDirectory(dir_file)
                continue

            self.processView(dir_file)

    def processView(self, file):
        """processes a single view file

        Arguments:
        file -- path to directory

        """
        self.processCssFile(file, True)

    def processCssFile(self, path, inline = False):
        """processes a single css file to find all classes and ids to replace

        Arguments:
        path -- path to css file to process

        Returns:
        void

        """


        # Take the raw list of tokens produced by tinycss and find all the classnames
        # and return them as a list
        def get_classes_from_token_list(token_list):
            css_classes = []
            begin_class = False
            for token in token_list:
                if token.type == "DELIM" and token.value == ".":
                    begin_class = True
                elif token.type == "IDENT" and begin_class:
                    css_classes.append(token.value)
                else:
                    begin_class = False
            return css_classes

        # Take the raw list of tokens produced by tinycss and find all the ids
        # and return them as a list
        def get_ids_from_token_list(token_list):
            css_ids = []
            for token in token_list:
                if token.type == "HASH":
                    css_ids.append(token.value)
            return css_ids

        # assume the css file is small enought to be read completely into memory
        # TODO: enforce this assumption by stating the file
        contents = Util.fileGetContents(path)
        if inline is True:
            blocks = self.getCssBlocks(contents)
            contents = ""
            for block in blocks:
                contents = contents + block


        stylesheet = tinycss.make_parser().parse_stylesheet(contents)

        for rule in stylesheet.rules:
            for found_class in get_classes_from_token_list(rule.selector):
                self.addClass(found_class)

            for found_id in get_ids_from_token_list(rule.selector):
                self.addId(found_id)

    def processJsFile(self, path, inline = False):
        """processes a single js file to find all classes and ids to replace

        Arguments:
        path -- path to css file to process

        Returns:
        void

        """
        contents = Util.fileGetContents(path)
        if inline is True:
            blocks = self.getJsBlocks(contents)
            contents = ""
            for block in blocks:
                contents = contents + block

        for selector in selectors:
            if selector[0] in self.config.id_selectors:
                if ',' in selector[2]:
                    id_to_add = re.search(r'(\'|\")(.*?)(\'|\")', selector[2])
                    if id_to_add is None:
                        continue

                    if not id_to_add.group(2):
                        continue

                    self.addId("#" + id_to_add.group(2))

                # if this is something like document.getElementById(variable) don't add it
                if not '\'' in selector[2] and not '"' in selector[2]:
                    continue

                self.addId("#" + selector[2].strip("\"").strip("'"))
                continue

            if selector[0] in self.config.class_selectors:
                class_to_add = re.search(r'(\'|\")(.*?)(\'|\")', selector[2])
                if class_to_add is None:
                    continue

                if not class_to_add.group(2):
                    continue

                self.addClass("." + class_to_add.group(2))
                continue

            if selector[0] in self.config.custom_selectors:
                matches = re.findall(r'((#|\.)[a-zA-Z0-9_]*)', selector[2])
                for match in matches:
                    if match[1] == "#":
                        self.addId(match[0])
                        continue

                    self.addClass(match[0])


    def generateMaps(self):
        """
loops through classes and ids to process to determine shorter names to use for them
        and creates a dictionary with these mappings

        Returns:
        void

        """
        selector_translation_generator = generate_gzip_friendly_tokens(None)

        for class_name, new_class_name in zip(self.classes_found, selector_translation_generator):

            # adblock extensions may block class "ad" so we should never
            # generate it also if the generated class already exists as a class
            # to be processed we can't use it or bad things will happen
            while new_class_name == "ad" or Util.keyInTupleList(new_class_name, classes):
                new_class_name = selector_translation_generator.next()

            self.class_map[class_name] = new_class_name

        for id_name, new_id_name in zip(self.ids_found, selector_translation_generator):
            small_id = "#" + VarFactory.getNext("id")

            # same holds true for ids as classes
            while small_id == "#ad" or Util.keyInTupleList(small_id, ids):
                small_id = "#" + VarFactory.getNext("id")

            self.id_map[id] = small_id


    def addId(self, selector):
        """adds a single id to the master list of ids

        Arguments:
        selector -- single id to add

        Returns:
        void

        """
        if selector in self.config.ignore or id == '#':
            return

        # skip $ ids from manifest
        if self.config.js_manifest is not None and selector[1] == '$':
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

        # skip $$ class names from manifest
        if self.config.js_manifest is not None and class_name[1:2] == '$$':
            return

        self.classes_found.add(class_name)

    def optimizeFiles(self, paths, callback, extension = ""):
        """loops through a bunch of files and directories, runs them through a callback, then saves them to disk

        Arguments:
        paths -- array of files and directories
        callback -- function to process each file with

        Returns:
        void

        """
        for file in paths:
            if not Util.isDir(file):
                self.optimizeFile(file, callback)
                continue

            self.optimizeDirectory(file, callback, extension)

    def optimizeFile(self, file, callback, new_path = None, prepend = "opt"):
        """optimizes a single file

        Arguments:
        file -- path to file
        callback -- function to run the file through
        prepend -- what extension to prepend

        Returns:
        void

        """
        content = callback(file)
        if new_path is None:
            new_path = Util.prependExtension(prepend, file)
        self.logger.info("optimizing " + file + " to " + new_path)
        Util.filePutContents(new_path, content)

        if self.config.show_savings:
            SizeTracker.trackFile(file, new_path)

    def prepareDirectory(self, path):
        if ".svn" in path:
            return True

        if Util.isDir(path):
            return False

        Util.unlinkDir(path)
        self.logger.info("creating directory " + path)
        os.mkdir(path)
        return False

    def optimizeDirectory(self, path, callback, extension = ""):
        """optimizes a directory

        Arguments:
        path -- path to directory
        callback -- function to run the file through
        extension -- extension to search for in the directory

        Returns:
        void

        """
        directory = path + "_opt"
        skip = self.prepareDirectory(directory)
        if skip is True:
            return

        for dir_file in Util.getFilesFromDir(path, extension):
            if Util.isDir(dir_file):
                self.optimizeSubdirectory(dir_file, callback, directory, extension)
                continue

            new_path = directory + "/" + Util.getFileName(dir_file)
            self.optimizeFile(dir_file, callback, new_path)

    def optimizeSubdirectory(self, path, callback, new_path, extension = ""):
        """optimizes a subdirectory within a directory being optimized

        Arguments:
        path -- path to directory
        callback -- function to run the file through
        new_path -- path to optimized parent directory
        extension -- extension to search for in the directory

        Returns:
        void

        """
        subdir_path = new_path + "/" + path.split("/").pop()
        skip = self.prepareDirectory(subdir_path)
        if skip is True:
            return

        for dir_file in Util.getFilesFromDir(path, extension):
            if Util.isDir(dir_file):
                self.optimizeSubdirectory(dir_file, callback, subdir_path, extension)
                continue

            new_file_path = subdir_path + "/" + Util.getFileName(dir_file)
            self.optimizeFile(dir_file, callback, new_file_path)


    def optimizeCss(self, path):
        """replaces classes and ids with new values in a css file

        Arguments:
        path -- string path to css file to optimize

        Returns:
        string

        """
        css = Util.fileGetContents(path)
        return self.replaceCss(css)

    def optimizeHtml(self, path):
        """replaces classes and ids with new values in an html file

        Uses:
        Muncher.replaceHtml

        Arguments:
        path -- string path to file to optimize

        Returns:
        string

        """
        html = Util.fileGetContents(path)
        html = self.replaceHtml(html)
        html = self.optimizeCssBlocks(html)
        html = self.optimizeJavascriptBlocks(html)

        return html

    def replaceHtml(self, html):
        """replaces classes and ids with new values in an html file

        Arguments:
        html -- contents to replace

        Returns:
        string

        """
        html = self.replaceHtmlIds(html)
        html = self.replaceHtmlClasses(html)
        return html

    def replaceHtmlIds(self, html):
        """replaces any instances of ids in html markup

        Arguments:
        html -- contents of file to replaces ids in

        Returns:
        string

        """
        for key, value in list(self.id_map.items()):
            key = key[1:]
            value = value[1:]
            html = html.replace("id=\"" + key + "\"", "id=\"" + value + "\"")

        return html

    def replaceClassBlock(self, class_block, key, value):
        """replaces a class string with the new class name

        Arguments:
        class_block -- string from what would be found within class="{class_block}"
        key -- current class
        value -- new class

        Returns:
        string

        """
        key_length = len(key)
        classes = class_block.split(" ")
        i = 0
        for class_name in classes:
            if class_name == key:
                classes[i] = value

            # allows support for things like a.class_name as one of the js selectors
            elif key[0] in (".", "#") and class_name[-key_length:] == key:
                classes[i] = class_name.replace(key, value)
            i = i + 1

        return " ".join(classes)

    def replaceHtmlClasses(self, html):
        """replaces any instances of classes in html markup

        Arguments:
        html -- contents of file to replace classes in

        Returns:
        string

        """
        for key, value in list(self.class_map.items()):
            key = key[1:]
            value = value[1:]
            class_blocks = re.findall(r'class\=((\'|\")(.*?)(\'|\"))', html)
            for class_block in class_blocks:
                new_block = self.replaceClassBlock(class_block[2], key, value)
                html = html.replace("class=" + class_block[0], "class=" + class_block[1] + new_block + class_block[3])

        return html

    def optimizeCssBlocks(self, html):
        """rewrites css blocks that are part of an html file

        Arguments:
        html -- contents of file we are replacing

        Returns:
        string

        """
        result_css = ""
        matches = self.getCssBlocks(html)
        for match in matches:
            match = self.replaceCss(match)
            result_css = result_css + match

        if len(matches):
            return html.replace(matches[0], result_css)

        return html

    @staticmethod
    def getCssBlocks(html):
        """searches a file and returns all css blocks <style type="text/css"></style>

        Arguments:
        html -- contents of file we are replacing

        Returns:
        list

        """
        return re.compile(r'\<style.*?\>(.*)\<\/style\>', re.DOTALL).findall(html)

    def replaceCss(self, css):
        """single call to handle replacing ids and classes

        Arguments:
        css -- contents of file to replace

        Returns:
        string

        """
        css = self.replaceCssFromDictionary(self.class_map, css)
        css = self.replaceCssFromDictionary(self.id_map, css)
        return css

    def replaceCssFromDictionary(self, dictionary, css):
        """replaces any instances of classes and ids based on a dictionary

        Arguments:
        dictionary -- map of classes or ids to replace
        css -- contents of css to replace

        Returns:
        string

        """
        # this really should be done better
        for key, value in list(dictionary.items()):
            css = css.replace(key + "{", value + "{")
            css = css.replace(key + " {", value + " {")
            css = css.replace(key + "#", value + "#")
            css = css.replace(key + " #", value + " #")
            css = css.replace(key + ".", value + ".")
            css = css.replace(key + " .", value + " .")
            css = css.replace(key + ",", value + ",")
            css = css.replace(key + " ", value + " ")
            css = css.replace(key + ":", value + ":")
            # if key == ".svg":
                # print "replacing " + key + " with " + value

        return css

    def optimizeJavascriptBlocks(self, html):
        """rewrites javascript blocks that are part of an html file

        Arguments:
        html -- contents of file we are replacing

        Returns:
        string

        """
        matches = self.getJsBlocks(html)

        for match in matches:
            new_js = match
            if self.config.compress_html:
                matches = re.findall(r'((:?)\/\/.*?\n|\/\*.*?\*\/)', new_js, re.DOTALL)
                for single_match in matches:
                    if single_match[1] == ':':
                        continue
                    new_js = new_js.replace(single_match[0], '');
            new_js = self.replaceJavascript(new_js)
            html = html.replace(match, new_js)

        return html

    @staticmethod
    def getJsBlocks(html):
        """searches a file and returns all javascript blocks: <script type="text/javascript"></script>

        Arguments:
        html -- contents of file we are replacing

        Returns:
        list

        """
        return re.compile(r'\<script(?! src).*?\>(.*?)\<\/script\>', re.DOTALL).findall(html)

    def optimizeJavascript(self, path):
        """optimizes javascript for a specific file

        Arguments:
        path -- path to js file on disk that we are optimizing

        Returns:
        string -- contents to replace file with

        """
        js_content = Util.fileGetContents(path)

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

