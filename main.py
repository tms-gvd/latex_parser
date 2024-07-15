from flask import Flask, render_template, request, send_from_directory
from flask import Response
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
        eq_filename = parser.save_equations("equations")
        return render_template(
            "index.html", equations=all_equations, eq_filename=eq_filename
        )
    else:
        return render_template("index.html", equations=[])


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.static_folder, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(port=8000, debug=DEBUG)
