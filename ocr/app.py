from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
import json
import os

UPLOAD_FOLDER = "static/uploads"
JSON_FOLDER = "static/jsons"
ALLOWED_EXTENSIONS = {"pdf"}

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["JSON_FOLDER"] = JSON_FOLDER

# --- Helper ---
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Rutas ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "file" not in request.files:
            return "No file part"

        file = request.files["file"]

        if file.filename == "":
            return "No selected file"

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            # Convertimos PDF en imágenes
            pages = convert_from_path(filepath, dpi=150)
            img_paths = []
            for i, page in enumerate(pages):
                img_filename = f"{filename}_{i+1}.jpg"
                img_path = os.path.join(app.config["UPLOAD_FOLDER"], img_filename)
                page.save(img_path, "JPEG")

                # ❌ Antes estabas pasando la ruta completa con \\
                # img_paths.append(img_path)

                # ✅ Mejor solo pasar el nombre de archivo relativo
                img_paths.append(img_filename)

            return render_template("index.html", images=img_paths, pdfname=filename)

    return render_template("index.html", images=None)


@app.route("/save_lines", methods=["POST"])
def save_lines():
    data = request.json  # { "pdfname": "file.pdf", "lines": { "page1.jpg": [x1, x2,...], ... }}
    pdfname = data.get("pdfname", "unknown")
    out_path = os.path.join(app.config["JSON_FOLDER"], "lines.json")

    with open(out_path, "w") as f:
        json.dump(data["lines"], f, indent=4)

    return jsonify({"status": "success", "saved_to": out_path})


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(JSON_FOLDER, exist_ok=True)
    app.run(debug=True)
