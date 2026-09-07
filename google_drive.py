from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config import settings

SCOPES=["https://www.googleapis.com/auth/drive.file"]

class GoogleDriveStorage:
    def __init__(self):
        if not settings.google_service_account_json:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is not configured.")
        creds=service_account.Credentials.from_service_account_file(settings.google_service_account_json, scopes=SCOPES)
        self.drive=build("drive","v3",credentials=creds)
        self.root=settings.google_drive_root_folder_id or self._folder("TikTok LIVE Recordings",None)

    def _folder(self,name,parent):
        q=f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent: q+=f" and '{parent}' in parents"
        r=self.drive.files().list(q=q,fields="files(id,name)",pageSize=1).execute()
        if r["files"]: return r["files"][0]["id"]
        body={"name":name,"mimeType":"application/vnd.google-apps.folder"}
        if parent: body["parents"]=[parent]
        return self.drive.files().create(body=body,fields="id").execute()["id"]

    def creator_tree(self,username):
        c=self._folder(username,self.root)
        return c,self._folder("recordings",c),self._folder("analysis",c),self._folder("clips",c)

    def upload(self,path,username,kind="recordings"):
        c,r,a,cl=self.creator_tree(username); parent={"recordings":r,"analysis":a,"clips":cl}[kind]
        media=MediaFileUpload(str(path),mimetype="video/mp4" if path.suffix==".mp4" else None,resumable=True)
        return self.drive.files().create(body={"name":path.name,"parents":[parent]},media_body=media,fields="id").execute()["id"]
