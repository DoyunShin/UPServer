from flask import Flask, request, send_from_directory, abort, Response, redirect, jsonify, send_file
from flask_cors import CORS
import werkzeug
from pathlib import Path
from json import loads
import filesystem
import time

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
ASSETS_DIR = STATIC_DIR / "assets"

configPath: Path = None
config: dict = None
storage: filesystem.storage = None
cache: dict[str, dict] = {}
# fileid: {time: int, metadata: dict}

app = Flask(__name__)
CORS(app)

def load_config():
    global storage, app, config, configPath
    if not configPath:
        configPath = BASE_DIR / "config.json"

    if not configPath.exists():
        print("Config file not found!")
        exit(-1)

    config = loads(configPath.read_text())
    if config["storage"] not in filesystem.storageTypes: 
        raise ValueError(f"Invalid storage type: {config['storage']}")
    storage = getattr(filesystem, config["storage"])(config, configPath)

    if config["host"]["proxy"]:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
        )

def check_config():
    if not config:
        load_config()

def store_cache(metadata: filesystem.Metadata):
    cache[metadata.id] = {"time": int(time.time()), "metadata": metadata}

def get_cache(fileid: str, filename: str) -> filesystem.Metadata:
    if fileid in cache and filename == cache[fileid]["metadata"].name:
        if cache[fileid]["time"] + config["host"]["cachetime"] > int(time.time()):
            return cache[fileid]["metadata"]
        else:
            cache.pop(fileid)
    return None

def clear_cache():
    for fileid in cache:
        if cache[fileid]["time"] + config["host"]["cachetime"] < int(time.time()):
            cache.pop(fileid)

def load_metadata(fileid: str, filename: str):
    metadata = get_cache(fileid, filename)
    if metadata is None:
        metadata = storage.load_metadata(fileid, filename)
        metadata.folderid = None
        metadata.delete = None
        store_cache(metadata)
    return metadata

@app.before_request
def before_request():
    check_config()

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
        data = load_metadata(fileid, filename).to_dict()
        return jsonify(data), 200
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
    # if fileid == "ye" and filename == "hello.gif": return STATIC_DIR.joinpath("item.html").read_text(), 200
    if "curl" in request.headers.get("User-Agent"): return getf(path)

    try:
        if len(fileid) != config["folderidlength"]: return abort(404)
        metadata = load_metadata(fileid, filename)
        return STATIC_DIR.joinpath("item.html").read_text(), 200

    except FileNotFoundError:
        return abort(404)

@app.route('/get/<path:path>', methods=['GET'])
def getf(path):
    if path.startswith("delete/"): return abort(404)
    dt = path.split("/")
    if len(dt) > 2: return abort(404)
    fileid = dt[0]
    filename = dt[1]
    try:
        if storage.cache and storage.is_cached(fileid, filename):
            return send_file(storage.get_cached(fileid, filename))
        if config["host"]["cdn"]["enabled"]:
            redirect_url = config['host']['cdn']['url']
            redirect_url = redirect_url[:-1] if redirect_url[-1] == "/" else redirect_url
            return redirect(f"{redirect_url}/{fileid}/{filename}")
        
        return storage.download(fileid, filename)
    
    except FileNotFoundError:
        return abort(404)

@app.route('/<path:path>', methods=['PUT'])
def putf(path):
    if "/" in path: return "Invalid path", 400
    if path[0] == ".": return "Invalid path", 400

    metadata = storage.save(request.stream, request.content_length, path)
    store_cache(metadata)

    unknown_domains = ["localhost", "127.0.0.1"]
    if request.host_url.split("//")[1].split("/")[0] in unknown_domains:
        print("WARNING: Host URL is not set correctly! Check your proxy settings. (HOST Header)")

    return f"{request.host_url}{metadata.id}/{metadata.name}", 200

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
    load_config()
    app.debug = config["debug"]
    app.run(host=config["host"]["ip"], port=config["host"]["port"])
