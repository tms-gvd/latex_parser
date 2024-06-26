import os
import re
import requests
import shutil
import tarfile
import tempfile

def decompress_tar_gz(tar_gz_path, extract_path):
    with tarfile.open(tar_gz_path) as tar:
        tar.extractall(path=extract_path)

def get_equations_from_content(latex_content):
    equation_pattern = r'\\begin\{(equation|align|gather)\}(.*?)\\end\{\1\}'
    matches = re.findall(equation_pattern, latex_content, re.DOTALL)
    return [match[1] for match in matches]

def list_files(directory):
    fig_files = []
    tex_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.tex') or file.endswith('.sty'):
                tex_files.append(os.path.join(root, file))
            elif file.endswith('.pdf') or file.endswith('.png') or file.endswith('.jpg'):
                fig_files.append(os.path.join(root, file))
    return fig_files, tex_files


class TexParser:
    def __init__(self, url, directory=None):
        self.url = url
        self.src_url = self.parse_url(url)
        self.directory = directory or tempfile.mkdtemp()
        self.use_temp_dir = directory is None
    
    @classmethod
    def from_directory(cls, directory):
        """
        Class method to initialize TexParser with a directory of extracted files.
        Assumes the directory contains the necessary .tex, .sty, and figure files.
        """
        instance = cls(url=None, directory=None)
        instance.use_temp_dir = False  # Since we're using an existing directory, no need for a temp directory
        instance.extract_dir = os.path.join(directory, 'extracted')
        return instance

    def parse_url(self, url):
        if url is None:
            return None
        else:
            kind, id = url.split('/')[-2:]  # Simplified parsing logic for demonstration
            return f'https://arxiv.org/src/{id}'

    def download_file(self):
        file_name = os.path.join(self.directory, 'temp.tar.gz')
        response = requests.get(self.src_url, stream=True)
        if response.status_code == 200:
            print(f"Downloading file from {self.src_url}")
            with open(file_name, 'wb') as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
            print(f"File downloaded successfully")
            return file_name
        else:
            print(f"Failed to download file. Status code: {response.status_code}")
            return None
    
    def extract_file(self, file_name):
        extract_dir = os.path.join(self.directory, 'extracted')
        os.makedirs(extract_dir, exist_ok=True)
        decompress_tar_gz(file_name, extract_dir)
        print("File decompressed successfully")
        return extract_dir
    
    def get_equations(self):
        file_name = self.download_file()
        if not file_name:
            return []

        self.extract_dir = self.extract_file(file_name)
        fig_paths, tex_paths = list_files(self.extract_dir)
        all_equations = []
        for path in tex_paths:
            try:
                with open(path, 'r') as file:
                    content = file.read()
                equations = get_equations_from_content(content)
                all_equations.extend([f"\\[{equation}\\]" for equation in equations])
            except Exception as e:
                print(f"Error processing {path}: {e}")
        if self.use_temp_dir:
            shutil.rmtree(self.directory)  # Clean up the temporary directory if one was used
            
        return all_equations
    

if __name__ == "__main__":
    url = 'https://arxiv.org/abs/1706.03762'
    parser = TexParser(url, directory='temp')
    equations = parser.get_equations()
    print(f"Found {len(equations)} equations")