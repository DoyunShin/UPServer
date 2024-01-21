from pathlib import Path
from json import loads, dumps
from flask import Response, send_file
from mimetypes import guess_type
from werkzeug.wsgi import LimitedStream
from io import BytesIO
import string
import random

storageTypes = ["gdrive", "local"]

class storage():
    folderidlength: int
    deletelength: int
    chunksize: int

    def __init__(self, config: dict):
        self.folderidlength = config["folderidlength"]
        self.deletelength = config["deletelength"]
        self.chunksize = config["chunk"]

    def _save(self, filename: str):
        fileid = self.create_fileid()
        mimetype = guess_type(filename)[0] or "application/octet-stream"
        metadataname = filename+".metadata"

        return fileid, mimetype, metadataname

    def save(self, file: LimitedStream, filesize: int, filename: str) -> dict:
        pass

    def load_metadata(self, fileid: str, filename: str) -> dict:
        pass
    
    def download(self, fileid: str, filename: str) -> Response:
        pass

    def get_list(self, path, dir) -> list:
        pass

    def is_fid_exists(self, fileid: str) -> bool:
        pass

    def _create_id(self, length: int) -> str:
        return ''.join(random.choices(string.ascii_letters+ string.digits, k=length))
    
    def create_fileid(self) -> str:
        folderid = self._create_id(self.folderidlength)
        if self.is_fid_exists(folderid):
            return self.create_fileid()
        return folderid

    def make_metadata(self, filesize: int, filename: str, fileid: str, mimetype: str, folderid: str = None) -> dict:
        return {
            "id": fileid,
            "name": filename,
            "mimeType": mimetype,
            "size": filesize,
            "folderid": folderid,
            "delete": self._create_id(self.deletelength),
            "hidden": False,
        }
    
    def write_stream(self, stream: LimitedStream, path: Path):
        with path.open("wb") as f:
            while True:
                chunk = stream.read(self.chunksize)
                if not chunk: break
                f.write(chunk)

class gdrive(storage):
    from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
    import googleapiclient.http

    class _UPSStreamSlice(object):
        """Truncated stream.

        Takes a stream and presents a stream that is a slice of the original stream.
        This is used when uploading media in chunks. In later versions of Python a
        stream can be passed to httplib in place of the string of data to send. The
        problem is that httplib just blindly reads to the end of the stream. This
        wrapper presents a virtual stream that only reads to the end of the chunk.
        """

        def __init__(self, stream: LimitedStream, begin, chunksize):
            """Constructor.

            Args:
            stream: (io.Base, file object), the stream to wrap.
            begin: int, the seek position the chunk begins at.
            chunksize: int, the size of the chunk.
            """
            self._stream = stream
            self._begin = begin
            self._chunksize = chunksize

            if chunksize != -1 and chunksize < 262144:
                from googleapiclient.errors import InvalidChunkSizeError
                raise InvalidChunkSizeError()

        def read(self, n=-1):
            """Read n bytes.

            Args:
            n, int, the number of bytes to read.

            Returns:
            A string of length 'n', or less if EOF is reached.
            """
            # The data left available to read sits in [cur, end)
            cur = self._stream.tell()
            end = self._begin + self._chunksize
            if n == -1 or cur + n > end:
                n = end - cur
            return self._stream.read(n)

    class UPSMediaIoStreamUpload(MediaIoBaseUpload):
        from googleapiclient import _helpers as util
        DEFAULT_CHUNK_SIZE = 100 * 1024 * 1024

        @util.positional(3)
        def __init__(self, fd, mimetype, size, chunksize=DEFAULT_CHUNK_SIZE, resumable=False):
            from googleapiclient.errors import InvalidChunkSizeError
            self._fd = fd
            self._mimetype = mimetype
            if not (chunksize == -1 or chunksize > 0):
                raise InvalidChunkSizeError()
            self._chunksize = chunksize
            self._resumable = resumable
            self._size = size

    
    del(googleapiclient.http._StreamSlice)
    googleapiclient.http._StreamSlice = _UPSStreamSlice


    def __init__(self, config: dict):
        super().__init__(config)

        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        self.credential = service_account.Credentials.from_service_account_info(config["gdrive"]["credential"], scopes=config["gdrive"]["scopes"])
        self.service = build('drive', 'v3', credentials=self.credential)
        self.root: str = config["gdrive"]["root"]

    def _get_files(self, **kwargs):
        if "fields" not in kwargs:
            kwargs["fields"] = "nextPageToken, files(id, name, mimeType)"
        return self.service.files().list(includeItemsFromAllDrives=True, supportsAllDrives=True, pageSize=1000, **kwargs)
        
    def get_list(self, dir: str, mimeType: str = None) -> dict[str, str]:
        """
        Return:
            dict[name, gid]
        """
        query = f"'{dir}' in parents"
        if mimeType: query += f" and mimeType='{mimeType}'"
        results = self._get_files(q=query).execute()
        files = {}
        for i in results["files"]:
            files[i["name"]] = i["id"]
        
        return files

    def is_fid_exists(self, fileid: str) -> bool:
        results = self._get_files(q=f"'{self.root}' in parents and mimeType='application/vnd.google-apps.folder' and name='{fileid}'").execute()
        return len(results["files"]) > 0
    
    def upload(self, metadata: dict, media = None) -> str:
        kwargs = {"body": metadata, "fields": "id"}
        if media: kwargs["media_body"] = media
        file = self.service.files().create(supportsAllDrives=True, **kwargs).execute()
        return file.get('id')

    def mkdir(self, name: str) -> str:
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [self.root]
        }
        return self.upload(file_metadata)

    def save(self, file: LimitedStream, filesize: int, filename: str) -> dict:
        fileid, mimetype, metadataname = self._save(filename)
        folderid = self.mkdir(fileid)

        file_info = {
            'name': filename,
            'parents': [folderid]
        }
        file_metadata_info = {
            'name': metadataname,
            'parents': [folderid]
        }
        metadata = self.make_metadata(filesize, filename, fileid, mimetype, folderid)
        metadataIO = BytesIO(dumps(metadata, ensure_ascii=False).encode("utf-8"))

        media = self.UPSMediaIoStreamUpload(file, mimetype, filesize, chunksize=filesize, resumable=True)
        mtdata = self.MediaIoBaseUpload(metadataIO, mimetype="application/json")
        self.upload(file_info, media)
        self.upload(file_metadata_info, mtdata)

        return metadata

    def load_metadata(self, fileid: str, filename: str) -> dict:
        rootList = self.get_list(dir=self.root, mimeType="application/vnd.google-apps.folder")
        if fileid not in rootList: 
            raise FileNotFoundError(f"File id {fileid} or name {filename} not found")

        folderList = self.get_list(dir=rootList[fileid], mimeType="application/json")
        if f"{filename}.metadata" not in folderList: 
            raise FileNotFoundError(f"File id {fileid} or name {filename} not found")
        
        metadata: dict = loads(self.service.files().get_media(fileId=folderList[f"{filename}.metadata"]).execute().decode("utf-8"))
        
        if metadata["name"] != filename:
            raise FileNotFoundError(f"File id {fileid} or name {filename} not found")
        
        return metadata

    def download(self, fileid: str, filename: str) -> Response:
        metadata = self.load_metadata(fileid, filename)
        fid = self.get_list(dir=metadata["folderid"])[filename]
        #resp = Response(self.service.files().get_media(fileId=fid).execute())
        #resp.headers["Content-Type"] = metadata["mimeType"]
        #return resp
        return send_file(self.service.files().get_media(fileId=fid).execute(), mimetype=metadata["mimeType"])

    pass

class local(storage):
    def __init__(self, config: dict):
        super().__init__(config)
        
        root = Path(config["local"]["root"])
        if not root.exists(): raise FileNotFoundError(f"Root directory {root} not found")
        self.root = root.resolve()
    
    def get_list(self, path: Path, dir: bool = False) -> list:
        if dir:
            return [f.name for f in path.iterdir() if f.is_dir()]
        else:
            return [f.name for f in path.iterdir() if f.is_file()]
    
    def is_fid_exists(self, fileid: str) -> bool:
        return (self.root / fileid).exists()

    def save(self, file, filesize: int, filename: str) -> dict:
        fileid, mimetype, metadataname = self._save(filename)
        folder = self.root / fileid
        folder.mkdir(exist_ok=False)

        metadata = self.make_metadata(filesize, filename, fileid, mimetype)
        self.write_stream(file, folder / filename)
        (folder / metadataname).write_text(dumps(metadata, ensure_ascii=False), encoding="utf-8")

        return metadata
    
    def load_metadata(self, fileid: str, filename: str) -> dict:
        folderPath = self.root / fileid
        if not folderPath.exists(): 
            raise FileNotFoundError(f"File id {fileid} or name {filename} not found")
        
        metadataPath = (folderPath / f"{filename}.metadata")
        if not metadataPath.exists(): 
            raise FileNotFoundError(f"File id {fileid} or name {filename} not found")
        
        metadata = loads(metadataPath.read_text())

        if metadata["name"] != filename:
            raise FileNotFoundError(f"File id {fileid} or name {filename} not found")
        
        return metadata
    
    def download(self, fileid: str, filename: str) -> Response:
        metadata = self.load_metadata(fileid, filename)
        return send_file(self.root / fileid / filename, mimetype=metadata["mimeType"])
        #return (folder / metadata["name"]).read_bytes()
