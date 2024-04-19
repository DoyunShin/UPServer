from pathlib import Path
from json import loads, dumps
from flask import Response, send_file
from mimetypes import guess_type
from werkzeug.wsgi import LimitedStream
from io import BytesIO
import string
import random

storageTypes = ["gdrive", "local"]

class Metadata:
    id: str
    name: str
    mimeType: str
    size: int
    folderid: str
    delete: str
    hidden: bool

    def to_dict(self, public: bool = False):
        data = {
            "id": self.id,
            "name": self.name,
            "mimeType": self.mimeType,
            "size": self.size,
            "hidden": self.hidden,
        }

        if not public:
            data["folderid"] = self.folderid
            data["delete"] = self.delete

        return data
    
    def to_json(self, ensure_ascii: bool = False, indent: int = 0, public: bool = False):
        return dumps(self.to_dict(public=public), ensure_ascii=ensure_ascii, indent=indent)
    
    def load(self, data: dict = None, dataPath: Path = None):
        if data:
            self.id = data["id"]
            self.name = data["name"]
            self.mimeType = data["mimeType"]
            self.size = data["size"]
            self.folderid = data["folderid"]
            self.delete = data["delete"]
            self.hidden = data["hidden"]
        
        elif dataPath:
            data = loads(dataPath.read_text())
            self.load(data)

class storage():
    folderidlength: int
    deletelength: int
    chunksize: int

    def __init__(self, config: dict, configPath: Path):
        self.folderidlength = config["folderidlength"]
        self.deletelength = config["deletelength"]
        self.chunksize = config["chunk"]

    def _save(self, filename: str, fileid: str = None):
        if not fileid:
            fileid = self.create_fileid()
        mimetype = guess_type(filename)[0] or "application/octet-stream"
        metadataname = filename+".metadata"

        return fileid, mimetype, metadataname
    
    def remove(self, fileid: str, filename: str, deletepass: str, force: bool = False): ...
    def save(self, file: LimitedStream, filesize: int, filename: str, fileid: str = None) -> Metadata: ...
    def load_metadata(self, fileid: str, filename: str) -> Metadata: ...
    def download(self, fileid: str, filename: str) -> Response: ...
    def get_list(self, path, dir) -> list: ...
    def is_fid_exists(self, fileid: str) -> bool: ...

    def _create_id(self, length: int) -> str:
        return ''.join(random.choices(string.ascii_letters+ string.digits, k=length))
    
    def create_fileid(self) -> str:
        folderid = self._create_id(self.folderidlength)
        if self.is_fid_exists(folderid):
            return self.create_fileid()
        return folderid

    def make_metadata(self, filesize: int, filename: str, fileid: str, mimetype: str, folderid: str = None) -> Metadata:
        metadata = Metadata()
        metadata.id = fileid
        metadata.name = filename
        metadata.mimeType = mimetype
        metadata.size = filesize
        metadata.folderid = folderid
        metadata.delete = self._create_id(self.deletelength)
        metadata.hidden = False
        return metadata
    
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

            if chunksize != 1 and chunksize < 262144:
                chunksize = 262144

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

    def __init__(self, config: dict, configPath: Path):
        super().__init__(config, configPath)
        config = self._config_check(config, configPath)

        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        self.credential = service_account.Credentials.from_service_account_info(config["gdrive"]["credential"], scopes=config["gdrive"]["scopes"])
        self.service = build('drive', 'v3', credentials=self.credential)
        self.root: str = config["gdrive"]["root"]
        self.cache: bool = config["gdrive"]["cache"]
        self.cachequeue = []

    def _config_check(config: dict, configPath: Path):
        if not config["gdrive"]["root"]:
            raise ValueError("Google drive root is not defined.")
        if "cache" not in config["gdrive"]:
            config["gdrive"]["cache"] = False
            configPath.write_text(dumps(config, ensure_ascii=False, indent=4))
        
        return config

    def _get_files(self, **kwargs):
        if "fields" not in kwargs:
            kwargs["fields"] = "nextPageToken, files(id, name, mimeType)"
        return self.service.files().list(includeItemsFromAllDrives=True, supportsAllDrives=True, pageSize=1000, **kwargs)
    
    def remove(self, fileid: str, filename: str, deletepass: str, force: bool = False):
        try:
            metadata = self.load_metadata(fileid, filename)
        except FileNotFoundError:
            return False

        if metadata.delete != deletepass and not force:
            return False

        rootList = self.get_list(dir=self.root, mimeType="application/vnd.google-apps.folder")
        infiles = self.get_list(dir=rootList[metadata.folderid])
        if "delete" in rootList:
            deleteFolder = rootList["delete"]
            deleteFolderList = self.get_list(dir=deleteFolder)
        else:
            deleteFolder = self.mkdir("delete")
            deleteFolderList = {}

        while True: # deleted name duplication check
            newname = f"{metadata.name[0]}{self._create_id(5)}_{metadata.name}"
            duplicated = False
            for i in deleteFolderList:
                if newname == i:
                    duplicated = True
                    break
            
            if not duplicated:
                break

        filegid = infiles[metadata.name]
        metadatagid = infiles[f"{metadata.name}.metadata"]
        self.service.files().update(fileId=filegid, body={"name": newname}).execute()
        self.service.files().update(fileId=metadatagid, body={"name": f"{newname}.metadata"}).execute()
        self.service.files().update(fileId=filegid, addParents=deleteFolder, removeParents=metadata.folderid).execute()
        self.service.files().update(fileId=metadatagid, addParents=deleteFolder, removeParents=metadata.folderid).execute()
        if len(infiles) == 2:
            self.service.files().delete(fileId=metadata.folderid).execute()

        return True
        
        
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

    def save(self, file: LimitedStream, filesize: int, filename: str, fileid: str = None) -> Metadata:
        fileid, mimetype, metadataname = self._save(filename, fileid)
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
        metadataIO = BytesIO(metadata.to_json().encode("utf-8"))

        media = self.UPSMediaIoStreamUpload(file, mimetype, filesize, chunksize=filesize, resumable=True)
        mtdata = self.MediaIoBaseUpload(metadataIO, mimetype="application/json")
        self.upload(file_info, media)
        self.upload(file_metadata_info, mtdata)

        return metadata

    def load_metadata(self, fileid: str, filename: str) -> Metadata:
        rootList = self.get_list(dir=self.root, mimeType="application/vnd.google-apps.folder")
        if fileid not in rootList:
            raise FileNotFoundError(f"File id {fileid} or name {filename} not found")

        folderList = self.get_list(dir=rootList[fileid], mimeType="application/json")
        if f"{filename}.metadata" not in folderList: 
            raise FileNotFoundError(f"File id {fileid} or name {filename} not found")
        
        metadata = Metadata()
        metadata.load(data=self.service.files().get_media(fileId=folderList[f"{filename}.metadata"]).execute().decode("utf-8"))
        
        if metadata.name != filename:
            raise FileNotFoundError(f"File id {fileid} or name {filename} not found")
        
        return metadata

    def download(self, fileid: str, filename: str) -> Response:
        metadata = self.load_metadata(fileid, filename)
        fid = self.get_list(dir=metadata.folderid)[filename]
        return send_file(self.service.files().get_media(fileId=fid).execute(), mimetype=metadata.mimeType)
    pass

class local(storage):
    def __init__(self, config: dict, configPath: Path):
        super().__init__(config, configPath)
        
        root = Path(config["local"]["root"])
        root.mkdir(exist_ok=True, parents=True)
        self.root = root.resolve()
    
    def get_list(self, path: Path, dir: bool = False) -> list:
        if dir:
            return [f.name for f in path.iterdir() if f.is_dir()]
        else:
            return [f.name for f in path.iterdir() if f.is_file()]
    
    def is_fid_exists(self, fileid: str) -> bool:
        return (self.root / fileid).exists()

    def save(self, file: LimitedStream, filesize: int, filename: str, fileid: str = None) -> Metadata:
        fileid, mimetype, metadataname = self._save(filename, fileid)
        folder = self.root / fileid
        folder.mkdir(exist_ok=False)

        metadata = self.make_metadata(filesize, filename, fileid, mimetype)
        self.write_stream(file, folder / filename)
        (folder / metadataname).write_text(metadata.to_json(), encoding="utf-8")

        return metadata
    
    def remove(self, fileid: str, filename: str, deletepass: str, force: bool = False):
        try:
            metadata = self.load_metadata(fileid, filename)
        except FileNotFoundError:
            return False
        
        if metadata.delete != deletepass and not force:
            return False
        
        deleteFolder = self.root / "delete"
        deleteFolder.mkdir(exist_ok=True)

        while True: # deleted name duplication check
            newname = f"{metadata.name[0]}{self._create_id(5)}_{metadata.name}"
            if not (deleteFolder / newname).exists():
                break

        (self.root / fileid / filename).rename(deleteFolder / newname)
        (self.root / fileid / f"{filename}.metadata").rename(deleteFolder / f"{newname}.metadata")

        return True

    def _remove_permanent(self, fileid: str, filename: str):
        try:
            metadata = self.load_metadata(fileid, filename)
        except FileNotFoundError:
            return False
        
        (self.root / fileid / filename).unlink()
        (self.root / fileid / f"{filename}.metadata").unlink()
        (self.root / fileid).rmdir()

        return True
    
    def load_metadata(self, fileid: str, filename: str) -> Metadata:
        folderPath = self.root / fileid
        if not folderPath.exists(): 
            raise FileNotFoundError(f"File id {fileid} or name {filename} not found")
        
        metadataPath = (folderPath / f"{filename}.metadata")
        if not metadataPath.exists(): 
            raise FileNotFoundError(f"File id {fileid} or name {filename} not found")
        
        metadata = Metadata()
        metadata.load(dataPath=metadataPath)

        if metadata.name != filename:
            raise FileNotFoundError(f"File id {fileid} or name {filename} not found")
        
        return metadata
    
    def download(self, fileid: str, filename: str) -> Response:
        metadata = self.load_metadata(fileid, filename)
        return send_file(self.root / fileid / filename, mimetype=metadata.mimeType)
        #return (folder / metadata["name"]).read_bytes()
