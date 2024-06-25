import requests
import tempfile
import os
import tarfile
from flask import Flask, render_template, request, send_from_directory

def parse_url(url):
    assert url.startswith('https://arxiv.org/'), 'URL must start with https://arxiv.org/'
    parts = url.replace('https://arxiv.org/', '').split('/')
    if len(parts) != 2:
        raise ValueError('URL must be of the form https://arxiv.org/ + {abs, pdf} + / + {id}')
    else:
        return parts

def decompress_tar_gz(file_name, extract_dir):
    tar = tarfile.open(file_name, 'r:gz')
    tar.extractall(path=extract_dir)
    tar.close()


app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        url = request.form['url']
        kind, id = parse_url(url)  # Assuming parse_url is defined elsewhere
        src_url = f'https://arxiv.org/src/{id}'
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_name = os.path.join(temp_dir, 'temp.tar.gz')
            response = requests.get(src_url, stream=True)
            if response.status_code == 200:
                print(f"Downloading file from {src_url}")
                with open(file_name, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            file.write(chunk)
                print(f"File downloaded successfully")
                
                extract_dir = os.path.join(temp_dir, 'extracted')
                decompress_tar_gz(file_name, extract_dir)  # Assuming decompress_tar_gz is defined elsewhere
                print("File decompressed successfully")
                
                files = os.listdir(extract_dir)
                all_equations = []
                for filename in files:
                    try:
                        with open(os.path.join(extract_dir, filename), 'r') as file:
                            content = file.read()
                        equations = get_equations(content)  # Assuming get_equations is defined elsewhere
                        all_equations.extend([f"\\[{equation}\\]" for equation in equations])
                    except Exception as e:
                        print(f"Error processing {filename}: {e}")
                
                return render_template('index.html', equations=all_equations)
            else:
                print(f"Failed to download file. Status code: {response.status_code}")
                return render_template('index.html', equations=[])
    else:
        return render_template('index.html', equations=[])


import re

def get_equations(latex_content):
    equation_pattern = r'\\begin\{(equation|align|gather)\}(.*?)\\end\{\1\}'
    matches = re.findall(equation_pattern, latex_content, re.DOTALL)
    # Replace double backslashes with single backslashes in each matched equation
    return [match[1] for match in matches]


if __name__ == '__main__':
    app.run(port=8000)