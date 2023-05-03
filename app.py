from flask import Flask, request, send_from_directory, render_template, abort, Response
import werkzeug
from pathlib import Path
from json import loads
import filesystem

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
UPLOAD_DIR = Path()

config = loads((BASE_DIR / "config.json").read_text())
storage = getattr(filesystem, config["storage"])(config)


app = Flask(__name__)

@app.route('/api/name')
def name():
    return config["name"], 200


@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory(ASSETS_DIR, path)

@app.route('/', methods=['GET', 'POST'])
def main():
    return render_template("index.html")

@app.route('/<path:path>', methods=['GET'])
def get(path):
    if path == "favicon.ico": return abort(404)
    dt = path.split("/")
    if len(dt) > 2: return abort(404)
    fileid = dt[0]
    filename = dt[1]

    try:
        metadata = storage.loadmetadata(fileid, filename)
    except FileNotFoundError:
        return abort(404)
    
    return metadata, 200

@app.route('/get/<path:path>', methods=['GET'])
def getf(path):
    dt = path.split("/")
    if len(dt) > 2: return abort(404)
    fileid = dt[0]
    filename = dt[1]
    try:
        res = Response(storage.download(fileid, filename))
        res.headers["Content-Type"] = storage.get_mimetype(filename)
        return res
    except FileNotFoundError:
        return abort(404)

@app.route('/<path:path>', methods=['PUT'])
def putf(path):
    if "/" in path: return "Invalid path", 400
    if path[0] == ".": return "Invalid path", 400
    metadata = storage.save(request.data, path)
    
    domain = request.host_url
    return f"{domain}{metadata['id']}/{metadata['name']}", 200

if __name__ == '__main__':
    app.debug = True
    app.run(host="0.0.0.0", threaded=True, port=8080)