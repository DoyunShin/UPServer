from flask import Flask, request, send_from_directory, abort, Response, redirect
from flask_cors import CORS
import werkzeug
from pathlib import Path
from json import loads
import filesystem
import time

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
ASSETS_DIR = STATIC_DIR / "assets"

config = loads((BASE_DIR / "config.json").read_text())
if config["storage"] not in filesystem.storageTypes: 
    raise ValueError(f"Invalid storage type: {config['storage']}")
storage: filesystem.storage = getattr(filesystem, config["storage"])(config)
cache: dict[str, dict] = {}
# fileid: {time: int, metadata: dict}

app = Flask(__name__)
CORS(app)

if config["host"]["proxy"]:
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

def store_cache(fileid: str, metadata: dict):
    cache[fileid] = {"time": int(time.time()), "metadata": metadata}

def get_cache(fileid: str) -> dict | None:
    if fileid in cache:
        if cache[fileid]["time"] + config["host"]["cachetime"] > int(time.time()):
            return cache[fileid]["metadata"]
        else:
            cache.pop(fileid)
    return None

def clear_cache():
    for fileid in cache:
        if cache[fileid]["time"] + config["host"]["cachetime"] < int(time.time()):
            cache.pop(fileid)

def load_metadata(fileid: str, filename: str) -> dict:
    metadata = get_cache(fileid)
    if metadata is None:
        metadata = storage.load_metadata(fileid, filename)
        metadata.pop("folderid")
        metadata.pop("delete")
        store_cache(fileid, metadata)
    return metadata

@app.route('/info')
def info():
    return config["general"], 200

@app.route('/assets/<path:path>')
def send_assets(path):
    return send_from_directory(ASSETS_DIR, path)

@app.route('/', methods=['GET', 'POST'])
def main():
    return STATIC_DIR.joinpath("index.html").read_text(), 200

@app.route('/api/v1/<path:path>', methods=['GET'])
def v1api(path):
    dt = path.split("/")
    if len(dt) > 2: return abort(404)
    fileid = dt[0]
    filename = dt[1]

    try:
        data = load_metadata(fileid, filename)
        return data, 200
    except FileNotFoundError:
        return abort(404)

@app.route('/api/v1/clearcache')
def clearcache():
    clear_cache()
    return "OK", 200

@app.route('/<path:path>', methods=['GET'])
def get(path):
    if path == "favicon.ico": return redirect(config["general"]["icon"])
    if path == "index.html": return redirect("/")
    if path == "robots.txt": return "Disallow: /", 200
    dt = path.split("/")
    if len(dt) > 2: return abort(404)
    fileid = dt[0]
    filename = dt[1]
    if fileid == "ye" and filename == "hello.gif": return STATIC_DIR.joinpath("item.html").read_text(), 200

    try:
        if len(fileid) != config["folderidlength"]: return abort(404)
        load_metadata(fileid, filename)
        if "curl" in request.headers.get("User-Agent"): return redirect(f"{config['host']['domain']}get/{metadata['id']}/{metadata['name']}") # curl handler
        return STATIC_DIR.joinpath("item.html").read_text(), 200

    except FileNotFoundError:
        return abort(404)

@app.route('/get/<path:path>', methods=['GET'])
def getf(path):
    dt = path.split("/")
    if len(dt) > 2: return abort(404)
    fileid = dt[0]
    filename = dt[1]
    try:
        if config["host"]["cdn"]["enabled"]: return redirect(f"{config['host']['cdn']['url']}/{fileid}/{filename}")
        return storage.download(fileid, filename)
        #res = Response(storage.download(fileid, filename))
        #res.headers["Content-Type"] = storage.get_mimetype(filename)
        #return res
    except FileNotFoundError:
        return abort(404)

@app.route('/<path:path>', methods=['PUT'])
def putf(path):
    if "/" in path: return "Invalid path", 400
    if path[0] == ".": return "Invalid path", 400
    
    metadata = storage.save(request.stream, request.content_length, path)
    domain = config["host"]["domain"] if config["host"]["domain"] else request.host_url

    return f"{domain}{metadata['id']}/{metadata['name']}", 200

@app.errorhandler(404)
def E404(e):
    return error("404", "Not Found!")

@app.errorhandler(500)
def E500(e):
    return error("500", "Internal Server Error!")

@app.errorhandler(400)
def E400(e):
    return error("400", "Bad Request!")


def error(code: str, msg: str): 
    if "curl" in request.headers.get("User-Agent"): return f"{code}: {msg}", int(code)
    return STATIC_DIR.joinpath("error.html").read_text().replace("StatusCode", code).replace("StatusMessage", msg), int(code)

if __name__ == '__main__':
    app.debug = config["debug"]
    app.run(host=config["host"]["ip"], threaded=True, port=config["host"]["port"])
