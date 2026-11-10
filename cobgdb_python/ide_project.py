"""Independent reader for the portable schema-1 project configuration.

No IDE modules, preferences, Qt or IDE build scripts are used.
"""
from dataclasses import dataclass
from pathlib import Path
from itertools import chain
import json
import os
import sys
from .project_source import inspect_source

DEBUG_FLAGS = ('-g', '-fsource-location', '-ftraceall', '-O0', '-save-temps')

@dataclass
class ProjectPlan:
    root: Path
    source: Path
    program: str
    arguments: list
    environment: dict
    output: Path
    module: bool
    runtime_cwd: str
    runtime_environment: dict
    missing_debug_flags: list
    compiler: str
    flags: list
    sql: bool
    debug: bool
    copybook_paths: list


def project_root(path):
    path = Path(path).resolve()
    return next((p for p in path.parents if (p/'config/project.json').is_file()), None)


def original_source(root, path, executable=None):
    path = Path(path).resolve()
    path.relative_to(root)
    if path.suffix.lower() in ('.cbl', '.cob', '.pco') and path.is_file():
        return path
    stem = Path(executable).stem if path.suffix.lower() == '.cpy' and executable else path.stem
    # Flat example projects keep their COBOL entry point beside config/.
    candidates = [p for p in chain(root.iterdir(), (root/'src').rglob('*')) if p.is_file()
                  and p.suffix.lower() in ('.cbl', '.cob', '.pco') and p.stem.casefold() == stem.casefold()]
    if len(candidates) != 1:
        raise ValueError('Cannot identify a unique original project source. Select its original COBOL source.')
    return candidates[0].resolve()


def load_config(root):
    try:
        data = json.loads((Path(root)/'config/project.json').read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        raise ValueError(f'Cannot read project configuration: {exc}') from exc
    if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data['schema_version'] != 1:
        raise ValueError('Unsupported project configuration; expected schema_version 1.')
    if not isinstance(data.get('name'), str) or not isinstance(data.get('sources'), dict):
        raise ValueError('Project configuration requires name and sources.')
    options_list = [data.get('defaults'), *data['sources'].values()]
    for key in data['sources']:
        if not isinstance(key, str) or not key or Path(key).is_absolute() or ':' in key or '\\' in key or '..' in Path(key).parts:
            raise ValueError('Source overrides require project-relative paths.')
    for options in options_list:
        if not isinstance(options, dict):
            raise ValueError('Project compiler settings must be an object.')
        for key in ('flags', 'copybook_paths', 'library_paths', 'libraries'):
            value = options.get(key)
            if value is not None and (not isinstance(value, list) or not all(isinstance(v, str) and '\0' not in v for v in value)):
                raise ValueError(f'{key} must be a list of strings or null.')
        if 'enabled' in options and not isinstance(options['enabled'], bool):
            raise ValueError('Compiler settings enabled must be true or false.')
        env = options.get('environment', {})
        if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) and '\0' not in v for k, v in env.items()):
            raise ValueError('Project environment must contain string values.')
        if env.get('path_mode', 'inherit') not in ('inherit', 'prepend', 'replace'):
            raise ValueError('Invalid tools path_mode.')
        if options.get('source_format', 'inherit') not in ('inherit', 'free', 'fixed'):
            raise ValueError('Invalid source_format.')
        listing = options.get('listing', {})
        if not isinstance(listing, dict) or ('enabled' in listing and not isinstance(listing['enabled'], bool)) or ('filename' in listing and not isinstance(listing['filename'], str)):
            raise ValueError('Invalid listing settings.')
    debug = data.get('debug', {})
    if not isinstance(debug, dict) or not isinstance(debug.get('enabled', False), bool):
        raise ValueError('Debug enabled must be true or false.')
    runtime = data.get('runtime', {})
    if not isinstance(runtime, dict) or not isinstance(runtime.get('accepted', False), bool):
        raise ValueError('Invalid runtime settings.')
    if not isinstance(runtime.get('working_directory', 'bin'), str) or not runtime.get('working_directory', 'bin'):
        raise ValueError('Choose a runtime working directory.')
    paths = runtime.get('data_directories', [])
    if not isinstance(paths, list) or not all(isinstance(p, str) and p for p in paths):
        raise ValueError('Runtime data_directories must be a list of paths.')
    return data


def resolve(root, value):
    return str((Path(root)/value).resolve()) if not os.path.isabs(value) else value


def project_runtime(root, cwd, environment, data=None):
    data = load_config(root) if data is None else data
    env = dict(environment)
    runtime = data.get('runtime', {})
    if not runtime.get('accepted'):
        return resolve(root, 'bin'), env
    cwd = resolve(root, runtime.get('working_directory', 'bin'))
    paths = [resolve(root, p) for p in runtime.get('data_directories', [])]
    for path in [cwd, *paths]:
        if not Path(path).is_dir():
            raise ValueError('Project runtime folder is missing: '+path+'; review project runtime settings.')
    if paths:
        env['COB_FILE_PATH'] = os.pathsep.join(paths)
    return cwd, env


def effective_options(data, source_key):
    defaults = data['defaults'] if data['defaults'].get('enabled', True) else {}
    source = data['sources'].get(source_key, {})
    result = dict(defaults)
    for key, value in source.items():
        if key not in ('environment', 'listing', 'source_format') and value is not None:
            result[key] = value
    result['listing'] = {**defaults.get('listing', {}), **source.get('listing', {})}
    result['source_format'] = source.get('source_format', 'inherit')
    if result['source_format'] == 'inherit':
        result['source_format'] = defaults.get('source_format', 'inherit')
    env = dict(defaults.get('environment', {}))
    override = source.get('environment', {})
    for key, value in override.items():
        if key not in ('path', 'path_mode') and value:
            env[key] = value
    if override.get('path_mode', 'inherit') != 'inherit':
        env['path_mode'] = override['path_mode']
        env['path'] = override.get('path', '')
    result['environment'] = env
    return result


def map_flags(root, flags):
    result = []
    operand = False
    for flag in flags:
        if operand:
            if flag.startswith('-'):
                raise ValueError('A compiler path option is missing its filename/path.')
            result.append(resolve(root, flag))
            operand = False
        elif flag in ('-I', '-L', '-T', '-t'):
            result.append(flag)
            operand = True
        elif flag.startswith(('-I', '-L')) and len(flag) > 2:
            result.append(flag[:2]+resolve(root, flag[2:]))
        elif flag in ('-x', '-m', '-o', '-C', '-E', '-S', '-c', '-fsyntax-only') or flag.startswith('-o'):
            raise ValueError(f'Project flags contain build-control option {flag}; the internal builder controls mode and output.')
        else:
            result.append(flag)
    if operand:
        raise ValueError('A compiler path option is missing its filename/path.')
    return result


def build_plan(path, executable=None):
    root = project_root(path)
    if root is None:
        return None
    source = original_source(root, path, executable)
    data = load_config(root)
    options = effective_options(data, source.relative_to(root).as_posix())
    env = dict(os.environ)
    overrides = options['environment']
    tool_path = overrides.get('path', '')
    if tool_path:
        tool_path = os.pathsep.join(resolve(root, p) for p in tool_path.split(os.pathsep) if p)
    if overrides.get('path_mode') == 'prepend' and tool_path:
        env['PATH'] = tool_path+os.pathsep+env.get('PATH', '')
    elif overrides.get('path_mode') == 'replace':
        env['PATH'] = tool_path
    for key, variable in [('cob_copy_dir', 'COB_COPY_DIR'), ('gixpp_path', 'GIXPP'),
                          ('gixsql_copy_dir', 'GIXSQL_COPY_DIR'), ('gixsql_library_dir', 'GIXSQL_LIBRARY_DIR')]:
        if overrides.get(key):
            value = overrides[key]
            if key == 'cob_copy_dir':
                value = os.pathsep.join(resolve(root, p) for p in value.split(os.pathsep) if p)
            elif key != 'gixpp_path' or '/' in value or '\\' in value:
                value = resolve(root, value)
            env[variable] = value
    compiler = overrides.get('compiler_path') or env.get('COBC') or 'cobc'
    if '/' in compiler or '\\' in compiler:
        compiler = resolve(root, compiler)
    flags = map_flags(root, options.get('flags') or [])
    copybooks = [resolve(root, p) for p in options.get('copybook_paths') or []]
    if (root/'copybooks').is_dir():
        copybooks.append(str(root/'copybooks'))
    copybooks.extend(p for p in env.get('COB_COPY_DIR', '').split(os.pathsep) if p)
    copybooks.extend([str(root)])
    scan_paths = copybooks + [flag[2:] for flag in flags if flag.startswith('-I') and len(flag)>2]
    scan_paths.extend(flags[i+1] for i, flag in enumerate(flags[:-1]) if flag == '-I')
    gixcopy = env.get('GIXSQL_COPY_DIR', '/usr/share/gixsql/copy' if os.name != 'nt' else '')
    if gixcopy:
        scan_paths.append(gixcopy)
    if options['source_format'] != 'inherit':
        flags.append('-free' if options['source_format'] == 'free' else '-fixed')
    free = False
    for flag in flags:
        if flag in ('-free', '-fixed'):
            free = flag == '-free'
    sql, module = inspect_source(source, scan_paths, free)
    for p in dict.fromkeys(copybooks):
        flags.extend(['-I', p])
    for p in options.get('library_paths') or []:
        flags.extend(['-L', resolve(root, p)])
    for library in options.get('libraries') or []:
        flags.append('-l'+library)
    listing = options['listing']
    # An explicit source listing filename supersedes an inherited -T/-t.
    source_options = data['sources'].get(source.relative_to(root).as_posix(), {})
    replace_listing = bool(source_options.get('listing', {}).get('filename') and source_options.get('flags') is None)
    listing_enabled = listing.get('enabled', True)
    clean, found = [], False
    i = 0
    while i < len(flags):
        flag = flags[i]
        if flag in ('-T', '-t'):
            if listing_enabled and not replace_listing:
                clean.extend([flag, flags[i+1].replace('{stem}', source.stem)])
                found = True
            i += 2
        else:
            if listing_enabled or flag not in ('-X', '--Xref', '-ftsymbols'):
                clean.append(flag)
            i += 1
    flags = clean
    if listing_enabled:
        if not found:
            flags.extend(['-T', resolve(root, (listing.get('filename') or 'build/{stem}.lst').replace('{stem}', source.stem))])
        for flag in ('--Xref', '-ftsymbols'):
            if flag not in flags:
                flags.append(flag)
    debug = data.get('debug', {}).get('enabled', False)
    extension = ('.dll' if os.name == 'nt' else '.dylib' if sys.platform == 'darwin' else '.so') if module else ('.exe' if os.name == 'nt' else '')
    output = root/'bin'/(source.stem+extension)
    runtime_cwd, runtime_env = project_runtime(root, str(root/'bin'), env, data)
    worker = ('--cobgdb-build' if getattr(sys, 'frozen', False)
              else str(Path(__file__).with_name('project_build.py')))
    return ProjectPlan(root, source, sys.executable, [worker, str(root), str(source)],
                       env, output, module, runtime_cwd, runtime_env,
                       [] if debug else [f for f in DEBUG_FLAGS if f not in flags],
                       compiler, flags, sql, debug, list(dict.fromkeys(scan_paths)))
