from __future__ import annotations
from typing import List, Tuple, Union

import os
import shutil
import tempfile
import tarfile
import re
import requests
from copy import copy
from pathlib import Path


TEX_EXT = [".tex", ".sty", ".bst"]
FIGS_EXT = [".pdf", ".png", ".jpg"]


def list_files(directory):
    fig_files = []
    tex_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".tex") or file.endswith(".sty"):
                tex_files.append(os.path.join(root, file))
            elif (
                file.endswith(".pdf") or file.endswith(".png") or file.endswith(".jpg")
            ):
                fig_files.append(os.path.join(root, file))
    return fig_files, tex_files


def decompress_tar_gz(tar_gz_path, extract_path, extract_img):
    tex_paths = []
    if extract_img:
        img_paths = []
    with tarfile.open(tar_gz_path) as tar:
        # Iterate over each member in the tar.gz archive
        for member in tar.getmembers():
            # Check if the file name ends with .tex or .sty
            if any(member.name.endswith(ext) for ext in TEX_EXT):
                # Extract only the matching member
                tar.extract(member, path=extract_path)
                tex_paths.append(os.path.join(extract_path, member.name))
            elif extract_img and any(member.name.endswith(ext) for ext in FIGS_EXT):
                tar.extract(member, path=extract_path)
                img_paths.append(os.path.join(extract_path, member.name))
            else:
                print(f"Skipping {member.name}")
    return tex_paths, img_paths if extract_img else []


def get_equations_from_content(latex_content):
    equation_pattern = r"\\begin\{(equation|align|gather)\}(.*?)\\end\{\1\}"
    matches = re.findall(equation_pattern, latex_content, re.DOTALL)
    return [match[1] for match in matches]


def parse_url(url):
    # TODO: add assertions to ensure the URL is in the expected format
    _, id = url.split("/")[-2:]  # Simplified parsing logic for demonstration
    return f"https://arxiv.org/src/{id}"


def download_file(src_url, save_directory):
    file_name = os.path.join(save_directory, "temp.tar.gz")
    response = requests.get(src_url, stream=True)

    if response.status_code == 200:
        print(f"Downloading file from {src_url}")
        with open(file_name, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
        print(f"File downloaded successfully")
        return file_name

    else:
        print(f"Failed to download file. Status code: {response.status_code}")
        return None


def extract_file(directory, extract_img):
    # Check if the tar.gz file exists
    path2tar = os.path.join(directory, "temp.tar.gz")
    assert os.path.exists(path2tar), f"File {path2tar} does not exist"

    # Create a directory to extract the contents of the tar.gz file
    extract_dir = os.path.join(directory, "extracted")
    os.makedirs(extract_dir, exist_ok=True)

    decompress_tar_gz(path2tar, extract_dir, extract_img)
    print("File decompressed successfully")

    return extract_dir


def not_commented_empty(line):
    return re.match(r"^\s*(%.*|$)", line) is None


def not_commented(line):
    # Returns True for lines that are not commented and not empty
    return not re.match(r"^\s*(%.*)?$", line) is not None


def is_new_command(line):
    return re.match(r"\\newcommand", line) is not None


def handle_exceptions(line):
    # not useful for us, so we remove it
    # for now, we keep the brackets that were used for simplicity
    # TODO: remove them
    if "\\ensuremath" in line:
        line = line.replace("\\ensuremath", "")
    # similar to the above case, but there is no bracket
    if "\\xspace" in line:
        line = line.replace("\\xspace", "")
    return line


def parse_equations(file):
    # Look for equation inside \begin{...} and \end{...}, including equation*, align*, alignat*, gather*, and also $$...$$
    equation_pattern = (
        r"(\\begin\{(equation|align|gather|alignat)\*?\})(.*?)(\\end\{\2\*?\})"  # Adjusted for optional asterisk handling
        r"|"  # OR
        r"(\$\$(.*?)\$\$)"  # Matches $$...$$ including the $$
    )
    matches = re.findall(equation_pattern, file, re.DOTALL)
    # Extract matches, including the tags
    equations_with_tags = []
    for match in matches:
        if match[0]:  # This is for \begin{...} \end{...} environments
            equations_with_tags.append(
                match[0] + match[2] + match[3]
            )  # \begin{...}, content, \end{...}
        else:  # This is for $$...$$
            # Wrap the content in \begin{equation}...\end{equation} instead of keeping $$...$$
            equations_with_tags.append(
                "\\begin{equation}\n" + match[5].strip() + "\n\\end{equation}"
            )  # match[5] contains the content between $$...$$
    return equations_with_tags


def get_raw_nc(files):
    new_commands = []
    print("Looking for new commands...")
    for file in files:
        print(Path(file).name, end=": ")
        with open(file, "r") as f:
            useful_lines = map(
                handle_exceptions, filter(not_commented_empty, f.readlines())
            )
            # Convert to list immediately to avoid consuming the iterator
            file_new_commands = list(filter(is_new_command, useful_lines))
            print(len(file_new_commands))
            # Extend the list of new commands
            new_commands.extend(file_new_commands)
    return new_commands


def parse_new_command(new_command):
    # remove leading and trailing whitespace
    new_command = new_command.strip()
    # remove the leading \newcommand
    new_command = new_command[11:]

    if new_command[-1] != "}":
        print("Cannot handle: ", new_command)
        # return None, None, 0
        return None

    # find if there are optional arguments
    if "[" in new_command and "]" in new_command:
        # get the number of optional arguments
        inside_bracks = new_command[new_command.index("[") + 1 : new_command.index("]")]
        if inside_bracks.isdigit():
            n_args = int(inside_bracks)
            # remove the optional arguments
            new_command = new_command.replace(f"[{n_args}]", "")
    else:
        n_args = 0

    if new_command[0] == "*":
        new_command = new_command[1:]

    if new_command[0] == "\\":
        # the new command is between the beginning and the first {
        new = new_command[: new_command.index("{")]
        # old the first { and the last }
        old = new_command[new_command.index("{") + 1 : new_command.rindex("}")]
    elif new_command[0] == "{":
        # the new command is between the beginning and the first }
        new = new_command[1 : new_command.index("}")]
        # remove the new command from the string
        new_command = new_command.replace(f"{{{new}}}", "")
        # old the first { and the last }
        old = new_command[new_command.index("{") + 1 : new_command.rindex("}")]
    else:
        print("Cannot handle: ", new_command)
        new, old, n_args = None, None, 0

    # return new, old, n_args
    return new


def parse_new_commands(new_commands):
    command_dict = {}
    for new_command in new_commands:
        # new, old, n_args = parse_new_command(new_command)
        # if new is not None:
        #     command_dict[new] = (old, n_args)
        new = parse_new_command(new_command)
        if new is not None:
            command_dict[new] = new_command.lstrip()

    # Add some common commands that are not defined in the tex files
    command_dict["infdivx"] = (
        "\DeclarePairedDelimiterX{\infdivx}[2]{(}{)}{#1\;\delimsize\|\;#2}"
    )
    return command_dict


class TexParser:
    def __init__(self, directory: str = None) -> None:
        """
        Use instead the class methods `from_url` or `from_directory` to create an instance.
        This constructor is used internally to initialize the instance.
        """

        # Initialize values for variables that will be set when initializing from an URL or an existing directory
        self.url = None
        self.src_url = None
        self.extract_dir = None
        self.path2tar = None

        # Following variables are always used
        self.directory = directory or tempfile.mkdtemp()
        self.use_temp_dir = directory is None

    @classmethod
    def from_url(
        cls, url: str, extract_img: str = False, save_directory: str = None
    ) -> TexParser:
        """
        Class method to initialize TexParser with a URL to an arXiv paper.
        """

        instance = cls(directory=save_directory)
        instance.url = url
        instance.src_url = parse_url(url)

        # Download the tar.gz file
        instance.path2tar = download_file(instance.src_url, instance.directory)

        # Extract the contents of the tar.gz file
        instance.extract_dir = extract_file(instance.directory, extract_img)
        return instance

    @classmethod
    def from_directory(cls, directory: str) -> TexParser:
        """
        Class method to initialize TexParser with a directory of extracted files.
        Assumes the directory contains the necessary .tex, .sty, and figure files.
        """

        instance = cls(directory=directory)
        instance.use_temp_dir = False  # Since we're using an existing directory, no need for a temp directory
        instance.extract_dir = os.path.join(directory, "extracted")
        return instance

    def get_equations(self):
        # Get the pathes of tex and fig files
        fig_paths, tex_paths = list_files(self.extract_dir)

        # For tex files, get the lines with new commands
        raw_nc = get_raw_nc(tex_paths)

        # Parse the new commands into a dictionary
        new_commands = parse_new_commands(raw_nc)

        # Get the raw equations from the tex files
        all_equations = []
        for file in tex_paths:
            with open(file, "r") as f:
                clean_file = "".join(
                    map(handle_exceptions, filter(not_commented, f.readlines()))
                )
                raw_equations = parse_equations(clean_file)
            for equation in raw_equations:
                for new, nc in new_commands.items():
                    if new in equation:
                        equation = nc + "\n" + equation
                all_equations.append(f"\\[{equation}\\]")

        if self.use_temp_dir:
            shutil.rmtree(
                self.directory
            )  # Clean up the temporary directory if one was used

        return all_equations
