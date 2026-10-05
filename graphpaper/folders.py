"""Per-project workspaces. Local inbox files become sources without cloud calls."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from .ingest import MAX_BYTES, clean, digest, extract
from .models import Source

EXTENSIONS = {'.pdf','.docx','.txt','.md','.markdown','.csv','.html','.htm'}
ROLES = {'evidence','canon','inspiration','voice'}


def safe_name(value):
    text = re.sub(r'[^\w .-]', '_', value, flags=re.UNICODE).strip(' .')[:100] or 'source'
    if text.split('.')[0].upper() in {'CON','PRN','AUX','NUL', *[f'COM{i}' for i in range(1,10)], *[f'LPT{i}' for i in range(1,10)]}:
        text = '_' + text
    return text


class ProjectFolders:
    def __init__(self, store, runner):
        self.store, self.runner = store, runner
        self.lock = threading.RLock()
        self.observed = {}

    def path(self, project):
        if not re.fullmatch(r'p_[a-f0-9]{12}', project.id):
            raise ValueError('Invalid project ID for filesystem access.')
        parent = self.store.root / 'Projects'
        parent.mkdir(exist_ok=True)
        if parent.is_symlink() or (hasattr(parent, 'is_junction') and parent.is_junction()):
            raise ValueError('Project root must not be a symbolic link or junction.')
        folder = parent / project.id
        if folder.is_symlink() or (hasattr(folder, 'is_junction') and folder.is_junction()):
            raise ValueError('Project folder must not be a symbolic link or junction.')
        folder.mkdir(exist_ok=True)
        for name in ['Inbox', 'Originals', 'Exports', *['Inbox/'+r.capitalize() for r in sorted(ROLES)]]:
            target = folder / name
            if target.is_symlink() or (hasattr(target,'is_junction') and target.is_junction()):
                raise ValueError('Workspace subfolders must not be links or junctions.')
            target.mkdir(exist_ok=True)
        readme = folder/'ABOUT THIS PROJECT.txt'
        if not readme.exists():
            readme.write_text(f'{project.title}\nGraphPaper project: {project.id}\n\nDrop documents in Inbox (or a role subfolder). They are imported automatically while this project is open and idle, and on the next visit. Files in Inbox/Voice are writing-style samples. Inbox/Canon contains fictional canon. Inbox/Evidence contains citable sources. No AI calls happen during import.\n\nOriginals holds files uploaded through the app. Exports is available for your own work. Removing a file does not silently delete its imported source. Deleting a project in the app leaves this folder intact. SQLite remains the authoritative project store; export a project backup for portability.\n', encoding='utf-8')
        return folder

    def original(self, project, source, data=None, filename=None):
        with self.lock:
            folder = self.path(project)/'Originals'
            name = source.id + '-' + safe_name(filename or source.title)
            if data is None:
                name += '.txt'
                data = source.text.encode('utf-8')
            target = folder/name
            if target.is_symlink():
                raise ValueError('Original-file destination cannot be a symbolic link.')
            if not target.exists():
                target.write_bytes(data)
            return target

    def info(self, project):
        folder = self.path(project)
        return {'path': str(folder), 'inbox': str(folder/'Inbox'), 'automatic': project.auto_import,
                'note': 'Checks while the project is open and idle. No cloud calls. Deleting a project does not delete this folder.'}

    def scan(self, project_id, force=False):
        with self.runner.lock, self.lock, self.store.lock:
            project = self.store.get(project_id)
            if self.runner.active(project_id):
                return {'project': project.model_dump(), 'events': [], 'busy': True, **self.info(project)}
            inbox = self.path(project)/'Inbox'
            records = self.store.cache_get('inbox:'+project_id) or {}
            events, changed, seen = [], False, set()
            count = 0
            # No following symlink/junction directories, including links nested in user folders.
            for folder, dirs, names in os.walk(inbox, followlinks=False):
                dirs[:] = [d for d in dirs if not d.startswith('.') and not (Path(folder)/d).is_symlink() and not (hasattr(Path(folder)/d,'is_junction') and (Path(folder)/d).is_junction())]
                for name in sorted(names):
                    path = Path(folder)/name
                    if name.startswith(('.', '~$')) or path.suffix.lower() not in EXTENSIONS:
                        continue
                    count += 1
                    if count > 150:
                        events.append({'status':'warning','path':'Inbox','message':'Only the first 150 supported files were checked. Split larger collections.'})
                        break
                    if path.is_symlink() or inbox.resolve() not in path.resolve().parents:
                        events.append({'status':'error','path':name,'message':'Links outside the project inbox are not imported.'})
                        continue
                    relative = path.relative_to(inbox).as_posix()
                    seen.add(relative)
                    old = records.get(relative, {})
                    try:
                        stat = path.stat()
                        signature = [stat.st_size, stat.st_mtime_ns]
                        key = (project_id, relative)
                        observation = self.observed.get(key)
                        self.observed[key] = signature
                        if old.get('stat') == signature:
                            continue
                        if not force and observation != signature:
                            continue
                        if stat.st_size > MAX_BYTES:
                            raise ValueError('File exceeds 20 MB.')
                        data = path.read_bytes()
                        after = path.stat()
                        if [after.st_size, after.st_mtime_ns] != signature:
                            continue
                        binary_hash = hashlib.sha256(data).hexdigest()
                        if old.get('binary_hash') == binary_hash:
                            records[relative] = {**old, 'stat':signature}
                            continue
                        text, warnings = extract(data, name)
                        text_hash = digest(text)
                        first = Path(relative).parts[0].lower()
                        role = first if first in ROLES else ('canon' if project.mode == 'fiction' else 'evidence')
                        current = next((s for s in project.sources if s.id == old.get('source_id')), None)
                        duplicate = next((s for s in project.sources if s.digest == text_hash and s.role == role and s is not current), None)
                        if duplicate:
                            source = duplicate
                            status = 'duplicate'
                        elif current:
                            if current.digest != old.get('text_hash'):
                                raise ValueError('The imported source changed separately. Rename the inbox file to import a new source without overwriting edits.')
                            current.text, current.digest, current.warnings = text, text_hash, warnings
                            source, status, changed = current, 'updated', True
                        else:
                            if len(project.sources) >= 100:
                                raise ValueError('Project source limit of 100 reached.')
                            number = max([int(s.id[1:]) for s in project.sources if re.fullmatch(r'S\d+',s.id)] + [0])+1
                            source = Source(id=f'S{number}', title=name, text=text, role=role, kind=path.suffix[1:], digest=text_hash, warnings=warnings)
                            project.sources.append(source)
                            status, changed = 'imported', True
                        records[relative] = {'source_id':source.id,'binary_hash':binary_hash,'text_hash':text_hash,'stat':signature}
                        events.append({'status':status,'path':relative,'source_id':source.id,'role':source.role})
                    except Exception as exc:
                        events.append({'status':'error','path':relative,'message':str(exc)[:300]})
                if count > 150:
                    break
            for missing in sorted(set(records)-seen):
                if not records[missing].get('missing'):
                    events.append({'status':'retained','path':missing,'message':'File removed; imported source retained.'})
                    records[missing]['missing'] = True
            if changed:
                if project.graph.nodes:
                    project.graph.warnings = list(dict.fromkeys(project.graph.warnings + ['Sources changed after the last graph build. Rebuild before relying on coverage.']))
                project = self.store.save(project, project.version)
            self.store.cache_put('inbox:'+project_id, records)
            return {'project': project.model_dump(), 'events':events, 'changed':changed, **self.info(project)}
