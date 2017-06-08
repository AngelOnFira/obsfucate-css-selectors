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

import os, shutil, glob
import string


# Parse the html page and generate potential classnames by taking substrings
# from elements and strings that appear within the document. If the number of
# requested tokens exceeds the number of eligible substrings in the document,
# then the different will be made up by procedurally generating identifiers
#
# Our strategy for procedurally generating additional substrings is to take the
# K most common substrings (where K is chosen to synergize with the deflate
# compression algorithm dictionary size) and use those substrings as a new
# alphabet. Then we will generate new substrings by concatenating characters
# from our new alphabet.
#
# TODO: the naive generation system is bad because it does not preserve the
# frequency distribution of the corpus substrings that make up its alphabet.
# I would assume that adding a uniform frequency distribution into the document
# will not help creating efficient huffman trees. An naive approach would be
# to create tokens such that the frequency distribution of the finite set of
# generated tokens matches the frequency distribution of the incoming alphabet.
# The optimal solution seems like it would involve optimizing in the space of
# huffman trees generated from a finite edit distance.
def generate_gzip_friendly_tokens(html_corpus):
    # TODO: parse the html_corpus document and generate the gzip friendly
    # alphabet
    alphabet = string.ascii_lowercase
    return generator_from_alphabet(alphabet)

def generator_from_alphabet(alphabet):
    def suffix_generator(depth):
        if depth > 0:
            for character in alphabet:
                for suffix in suffix_generator(depth - 1):
                    yield character + suffix
        else:
            for character in alphabet:
                yield character

    depth = 0
    while True:
        for suffix in suffix_generator(depth):
            yield suffix
        depth += 1


def find_all_files(filepath_list):
    files = []
    for path in filepath_list:
        if not os.path.isdir(path):
            files.append(path)
        else:
            for dirname, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    files.append(os.path.join(dirname, filename))
    return files

class Util:
    """collection of various utility functions"""

    @staticmethod
    def getFilesFromDir(path, extension = ""):
        path = path + "/*"

        if not extension == "":
            path = path + "." + extension.lstrip(".")

        return glob.glob(path)


    @staticmethod
    def getExtension(path):
        """gets the extension from a file

        Arguments:
        path -- string of the file name

        Returns:
        string

        """
        return path.split(".").pop()

    @staticmethod
    def prependExtension(ext, path):
        current_ext = Util.getExtension(path)
        return path.replace("." + current_ext, "." + ext + "." + current_ext)

    @staticmethod
    def getBasePath(path):
        """gets the base directory one level up from the current path

        Arguments:
        path -- path to file or directory

        Returns:
        string

        """
        bits = path.split("/")
        last_bit = bits.pop()
        return "/".join(bits)
        # return "/".join(bits).rstrip(last_bit)

    @staticmethod
    def getFileName(path):
        return path.replace(Util.getBasePath(path), "").lstrip("/")

    @staticmethod
    def unlink(path):
        """deletes a file on disk

        Arguments:
        path -- path to file on disk

        Returns:
        void

        """
        if os.path.isfile(path):
            os.unlink(path)

    @staticmethod
    def unlinkDir(path):
        """removes an entire directory on disk

        Arguments:
        path -- path to directory to remove

        Returns:
        void

        """
        try:
            shutil.rmtree(path)
        except:
            pass

    @staticmethod
    def fileGetContents(path):
        """gets the contents of a file

        Arguments:
        path -- path to file on disk

        Returns:
        string

        """
        if not os.path.isfile(path):
            print("file does not exist at path " + path)
            print("skipping")
        file = open(path, "r")
        contents = file.read()
        file.close()
        return contents

    @staticmethod
    def filePutContents(path, contents):
        """puts contents into a file

        Arguments:
        path -- path to file to write to
        contents -- contents to put into file

        Returns:
        void

        """
        file = open(path, "w")
        file.write(contents)
        file.close()

    @staticmethod
    def keyInTupleList(key, tuple_list):
        """checks a list of tuples for the given key"""
        for tuple in tuple_list:
            if tuple[0] == key:
                return True
        return False
