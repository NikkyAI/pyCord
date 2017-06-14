import git
from pathlib import Path
import appdirs


class Gitwiki:
    """
    Manipulates a wiki and returns urls to files
    """
    def __init__(self, url: str, web_url_base: str):
        self.url = url
        self.web_url_base = web_url_base
        # clone
        dir =  appdirs.user_data_dir('pyCord', 'NikkyAI')
        self.wiki_path = Path(dir, "wiki")
        if self.wiki_path.exists() and self.wiki_path.is_dir():
            self.repo = git.Repo(self.wiki_path)
            self.reset()
        else:
            self.repo = git.Repo.clone_from(url, self.wiki_path)

    def upload(self, filename: str, content: str):
        self.reset()
        file_path: Path = Path(f"{filename}.txt")
        full_path = Path(self.wiki_path / file_path)
        file_dir = Path(full_path.parent)
        file_dir.mkdir(exist_ok=True, parents=True)
        with open(full_path, "w+") as text_file:
            text_file.write(content)
        self.repo.index.add([str(file_path)])
        # get names of all changed files
        diff = self.repo.git.diff('HEAD~1..HEAD', name_only=True)
        if diff:
            print("changed files " + diff)
            self.repo.index.commit(f"added {filename}")
            self.repo.remotes.origin.push()
        return self.web_url_base + "/" + "/".join(file_path.parts)


    def reset(self):
        repo = self.repo
        # blast any current changes
        repo.git.reset('--hard')
        # ensure master is checked out
        repo.heads.master.checkout()
        # blast any changes there (only if it wasn't checked out)
        repo.git.reset('--hard')
        # remove any extra non-tracked files (.pyc, etc)
        repo.git.clean('-xdf')
        # pull in the changes from from the remote
        repo.remotes.origin.pull()