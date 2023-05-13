from pathlib import Path
from json import loads, dumps
import string
import random

class tmpdir():
    def __init__(self):
        from tempfile import gettempdir
        self.folder = Path(gettempdir()) / "UPServer"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.cleanupcache = []
        self.cleanall()

    def mkid(self, fid: str) -> Path:
        file = self.folder / fid
        file.mkdir(parents=True, exist_ok=True)
        return file
    
    def add_cleanup(self, fid: str):
        self.cleanupcache.append(fid)
        self.cleanup()

    def cleanup(self):
        for i in self.cleanupcache:
            i = self.folder / i
            try:
                for j in i.iterdir():
                    j.unlink()
                i.rmdir()
                self.cleanupcache.remove(i)
            except:
                pass
    
    def cleanall(self):
        # delete all of the files and folders in the temp folder
        for i in self.folder.iterdir():
            try:
                for j in i.iterdir():
                    j.unlink()
                i.rmdir()
            except:
                pass

    def __del__(self):
        self.cleanall()



class storage():
    folderidlength: int
    deletelength: int

    def __init__(self, config: dict):
        
        pass

    def default(self, config: dict):
        self.folderidlength = config["folderidlength"]
        self.deletelength = config["deletelength"]
        self.chunksize = 4096
        

    def save(self, file, filesize: int, filename: str) -> dict:
        pass

    def loadmetadata(self, fileid: str, filename: str) -> dict:
        pass
    
    def download(self, fileid: str, filename: str):
        pass

    def list(self, path: str) -> list:
        pass

    def rnd(self, length: int) -> str:
        return ''.join(random.choices(string.ascii_letters+ string.digits, k=length))
    
    def create_fileid(self) -> str:
        lst = self.list()
        while True:
            folderid = self.rnd(self.folderidlength)
            if folderid not in lst:
                break
        
        return folderid
        

    def make_metadata(self, filesize: int, filename: str, fileid: str, mimetype: str, folderid: str = None):        
        return {
            "id": fileid,
            "name": filename,
            "mimeType": mimetype,
            "size": filesize,
            "folderid": folderid,
            "delete": self.rnd(self.deletelength),
            "hidden": False,
        }
    
    def get_mimetype(self, filename: str) -> str:
        try:
            mimetype = loads(Path("mimetypes.json").read_text())[filename.split(".")[-1]]
        except:
            mimetype = "application/octet-stream"
    
        return mimetype
    
    def write_stream(self, file, path: Path):
        with path.open("wb") as f:
            while True:
                chunk = file.read(self.chunksize)
                if not chunk:
                    break
                f.write(chunk)
    



class gdrive(storage):
    def __init__(self, config: dict):
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        from googleapiclient.http import MediaFileUpload
        self.default(config)

        self.tmpdir = tmpdir()
        self.credential = service_account.Credentials.from_service_account_info(config["gdrive"]["credential"], scopes=config["gdrive"]["scopes"])
        self.service = build('drive', 'v3', credentials=self.credential)
        self.root = config["gdrive"]["root"]
        self.MediaFileUpload = MediaFileUpload
    
    def list(self, dir: str = None) -> dict[str, str]:
        path = self.root if dir is None else dir
        results = self.service.files().list(includeItemsFromAllDrives=True, supportsAllDrives=True, pageSize=1000, fields="nextPageToken, files(id, name, mimeType)",
                q=f"'{path}' in parents",).execute()
        files = {}
        for i in results["files"]:
            files[i["name"]] = i["id"]
        
        return files
    
    def folderlist(self, dir: str = None) -> list:
        return list(self.list(dir).keys())
    
    def getid(self, dir: str = None, name: str = None) -> str:
        try:
            return self.list(dir)[name]
        except KeyError:
            raise FileNotFoundError(f"File {name} not found in {dir}")
    
    def mkdir(self, name: str) -> str:
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [self.root]
        }
        file = self.service.files().create(body=file_metadata, supportsAllDrives=True, fields='id').execute()
        return file.get('id')

    def save(self, file, filesize: int, filename: str) -> dict:
        mimetype = self.get_mimetype(filename)
        fileid = self.create_fileid()
        folderid = self.mkdir(fileid)
        metadataname = filename+".metadata"

        file_metadata = {
            'name': filename,
            'parents': [folderid]
        }
        metadata_md = {
            'name': metadataname,
            'parents': [folderid]
        }
        metadata = self.make_metadata(filesize, filename, fileid, mimetype, folderid)
        thistemp = self.tmpdir.mkid(fileid)
        metaPath = thistemp / metadataname
        filePath = thistemp / filename

        metaPath.write_text(dumps(metadata))
        self.write_stream(file, filePath)

        media = self.MediaFileUpload(filePath, mimetype=mimetype)
        mtdata = self.MediaFileUpload(metaPath, mimetype="application/json")
        self.service.files().create(supportsAllDrives=True, body=file_metadata, media_body=media, fields='id').execute()
        self.service.files().create(supportsAllDrives=True, body=metadata_md, media_body=mtdata, fields='id').execute()

        self.tmpdir.add_cleanup(fileid)

        return metadata

    def loadmetadata(self, fileid: str, filename: str) -> dict:
        if fileid not in self.folderlist():
            raise FileNotFoundError(f"File {filename} not found in {fileid}")
        folderid = self.getid(name=fileid)
        metadataid = self.getid(dir=folderid, name=filename+".metadata")
        metadata = loads(self.service.files().get_media(fileId=metadataid).execute())

        if metadata["name"] != filename:
            raise FileNotFoundError(f"File {filename} not found in {fileid}")
        return metadata

    def download(self, fileid: str, filename: str):
        metadata = self.loadmetadata(fileid, filename)
        fid = self.getid(dir=metadata["folderid"], name=filename)
        return self.service.files().get_media(fileId=fid).execute()

    pass

class local(storage):
    def __init__(self, config: dict):
        self.default(config)
        
        root = Path(config["local"]["root"])
        if not root.exists(): raise FileNotFoundError(f"Root directory {root} not found")
        self.root = root.resolve()

    def save(self, file, filesize: int, filename: str) -> dict:
        fileid = self.create_fileid()
        mimetype = self.get_mimetype(filename)
        metadataname = filename+".metadata"
        folder = self.root / fileid
        folder.mkdir(exist_ok=False)

        metadata = self.make_metadata(filesize, filename, fileid, mimetype)
        self.write_stream(file, folder / filename)
        (folder / metadataname).write_text(dumps(metadata))

        return metadata
    
    def loadmetadata(self, fileid: str, filename: str) -> dict:
        folder = self.root / fileid
        metadataname = filename+".metadata"
        metadata = loads((folder / metadataname).read_text())

        if metadata["name"] != filename:
            raise FileNotFoundError(f"File {filename} not found in {fileid}")
        return metadata
    
    def download(self, fileid: str, filename: str):
        metadata = self.loadmetadata(fileid, filename)
        folder = self.root / fileid
        return (folder / metadata["name"]).read_bytes()
    
    def list(self, dir: str = None) -> list:
        path = self.root if dir is None else self.root / dir
        return [f.name for f in path.iterdir() if f.is_dir()]

    pass
