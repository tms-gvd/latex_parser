from flask import Flask, render_template, request
from src.tex_parser import TexParser
import os

app = Flask(__name__)
DEBUG = os.environ.get("DEBUG", False)


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        url = request.form["url"]
        parser = TexParser.from_url(url, save_directory="debug" if DEBUG else None)
        all_equations = parser.get_equations()
        return render_template("index.html", equations=all_equations)
    else:
        return render_template("index.html", equations=[])


if __name__ == "__main__":
    app.run(port=8000)
