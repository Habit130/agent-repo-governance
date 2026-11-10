#!/usr/bin/env python3
"""Independent bounded policy inputs and offline real-Codex recording for #76."""

import argparse
import hashlib
import json
from pathlib import Path
import random

SEEDS = (1, 2, 3, 4)
SPELLINGS = ('policy:', '"policy":', "'policy':", 'policy :')
HEADS = ('zzz: foo', 'zzz:', 'zzz: foo # c', 'zzz: # c', 'interface:',
         'dependencies:', 'x: -a', 'x: a:b', "zzz: 'q'", 'zzz: "q"', 'zzz: |', 'zzz: >-')
CONTS = ('  bar', '  : bar', '  # c', '# c', '', '  "x"', "  'x'", '  [a]',
         '  {a: b}', '  a:\tb', '  a: b', '  ? a', '  - a', '    deeper',
         '  bar # c', '  bar#c', '  -\tb', '  ?\tb', '  :\tb', '  a :b',
         '  display_name: v', '    more', '  tools:', '    - type: t',
         '      value: v', '        : w', '   odd', '  ...', '  ---',
         '  !t x', '  &a x', '  *a', '  %x', '  @x', '  `x`', '  ,x', '  ]', '  }')
FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'machine'
CORPUS = FIXTURES / 'codex-generated-policy-corpus.json'
RECORDING = FIXTURES / 'codex-generated-policy-recording.json'


def generate():
    """Never import or filter through either reader; keep valid and malformed inputs."""
    prefixes = []
    for line in ('  bar', '  : bar', '  "x"', '  [a]', '  a: b'):
        prefixes.append(('continuation', 'zzz: foo\n' + line + '\n'))
    for head in ('zzz: foo # c', 'zzz: foo\n  # c', 'zzz: foo\n# c'):
        for line in ('  bar', '  : bar'):
            prefixes.append(('comment', head + '\n' + line + '\n'))
    for line in ('  -\tb', '  ?\tb', '  :\tb', '\tbar', '  a:\tb'):
        prefixes.append(('tab', 'zzz: foo\n' + line + '\n'))
    for indicator in ('|', '>-', '|2', '>+'):
        for lines in ('  first\n    deeper\n  back\n', '    first\n  below\n', '\n  text\n'):
            prefixes.append(('block', 'zzz: ' + indicator + '\n' + lines))
    for seed in SEEDS:
        rng = random.Random(seed)
        for _ in range(32):
            lines = [rng.choice(HEADS)] + [rng.choice(CONTS) for _ in range(rng.randint(1, 4))]
            prefixes.append(('seeded', '\n'.join(lines) + '\n'))
    shapes, seen = [], set()
    for family, prefix in prefixes:
        for spelling, policy in enumerate(SPELLINGS):
            text = prefix + policy + '\n  allow_implicit_invocation: false\n'
            if text in seen:
                continue
            seen.add(text)
            shapes.append({'name': 'probe-%04d' % len(shapes), 'family': family,
                           'spelling': spelling, 'yaml': text})
    return {'recipe': 1, 'seeds': list(SEEDS), 'samples_per_seed': 32,
            'policy_spellings': list(SPELLINGS), 'shapes': shapes}


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def digest(corpus):
    return hashlib.sha256(encoded(corpus).encode('utf-8')).hexdigest()



BATCH_SIZE = 16
CONTROL = 'zz-probe-control'


def description(name):
    return 'Complete synthetic policy probe %s ending sentinel.' % name


def entries(texts):
    # Parse only verbatim skill-entry lines, independently of either policy detector.
    import re
    found = {}
    for text in texts:
        for line in text.splitlines():
            match = re.fullmatch(r'- ((?:probe-\d+|zz-probe-control)): (.*) \(file: [^)]+\)', line)
            if match:
                name, desc = match.groups()
                if name in found:
                    raise ValueError('duplicate entry: ' + name)
                found[name] = desc
    return found


def check_batch(batch, names):
    baseline = entries(batch['baseline'])
    policy = entries(batch['policy'])
    expected = {name: description(name) for name in names + [CONTROL]}
    if baseline != expected:
        raise ValueError('baseline omitted, shortened or unexpected entries')
    if policy.get(CONTROL) != expected[CONTROL]:
        raise ValueError('listable control omitted or shortened')
    if any(name not in expected or desc != expected[name] for name, desc in policy.items()):
        raise ValueError('policy entries shortened or unexpected')
    return policy


def verify(corpus, recording, machine_reader, copies_reader):
    if recording['corpus_sha256'] != digest(corpus):
        raise ValueError('recording corpus digest mismatch')
    if not recording['consumer_version'].startswith('codex-cli '):
        raise ValueError('missing consumer version')
    shapes = corpus['shapes']
    batches = recording['batches']
    if recording['batch_size'] != BATCH_SIZE or len(batches) != (len(shapes) + BATCH_SIZE - 1) // BATCH_SIZE:
        raise ValueError('incomplete batches')
    for index, batch in enumerate(batches):
        group = shapes[index * BATCH_SIZE:(index + 1) * BATCH_SIZE]
        names = [shape['name'] for shape in group]
        if batch['names'] != names:
            raise ValueError('batch inputs mismatch')
        listed = check_batch(batch, names)
        for shape in group:
            data = shape['yaml'].encode('utf-8')
            machine = machine_reader(data) == 'false'
            copies = copies_reader(data)
            if machine != copies:
                raise ValueError('detectors disagree: ' + shape['name'])
            if (machine or copies) and shape['name'] in listed:
                raise ValueError('unsafe certification: ' + shape['name'])


def record(corpus, cli):
    """Real CLI only on explicit invocation. Never inherited credentials or real homes."""
    import os
    import sys
    import tempfile
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'machine' / 'scripts'))
    from machinelib.home import Home

    batches = []
    with tempfile.TemporaryDirectory(prefix='policy-corpus-') as scratch:
        scratch = Path(scratch).resolve()
        # Home.run_codex creates disposable CODEX_HOME and cwd via tempfile too.
        old_tempdir = tempfile.tempdir
        tempfile.tempdir = str(scratch)
        try:
            env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'en_US.UTF-8'}
            for key in ('HOME', 'CODEX_HOME', 'TMPDIR', 'XDG_CONFIG_HOME', 'XDG_STATE_HOME',
                        'XDG_DATA_HOME', 'XDG_CACHE_HOME'):
                path = scratch / key.lower()
                path.mkdir()
                env[key] = str(path)
            home = Home(env['HOME'], env)
            code, version, err = home.run_codex(cli, ['--version'])
            if code or err or not version.startswith('codex-cli '):
                raise ValueError('consumer version probe failed')

            def capture():
                import re
                code, out, err = home.run_codex(cli, ['debug', 'prompt-input', 'x'])
                if code or err:
                    raise ValueError('prompt-input failed: exit %s; %s' % (code, err))
                texts = []
                def walk(node):
                    if isinstance(node, dict):
                        for value in node.values():
                            walk(value)
                    elif isinstance(node, list):
                        for value in node:
                            walk(value)
                    elif isinstance(node, str) and node.startswith('<skills_instructions>'):
                        text = node.replace(str(scratch), '/fixture-scratch')
                        text = re.sub(r'/machine-codex-[^/\s`]+', '/machine-codex-disposable', text)
                        texts.append(text)
                walk(json.loads(out))
                if not texts:
                    raise ValueError('no skills instructions in prompt-input')
                return texts

            skills_root = Path(home.skills)
            skills_root.mkdir(parents=True)
            for offset in range(0, len(corpus['shapes']), BATCH_SIZE):
                import shutil
                for child in skills_root.iterdir():
                    shutil.rmtree(str(child))
                group = corpus['shapes'][offset:offset + BATCH_SIZE]
                names = [shape['name'] for shape in group]
                for name in names + [CONTROL]:
                    skill = skills_root / name
                    skill.mkdir()
                    (skill / 'SKILL.md').write_text(
                        '---\nname: %s\ndescription: %s\ndisable-model-invocation: true\n---\n\nSynthetic.\n'
                        % (name, description(name)), encoding='utf-8')
                baseline = capture()
                for shape in group:
                    agents = skills_root / shape['name'] / 'agents'
                    agents.mkdir()
                    (agents / 'openai.yaml').write_text(shape['yaml'], encoding='utf-8')
                batch = {'names': names, 'baseline': baseline, 'policy': capture()}
                check_batch(batch, names)
                batches.append(batch)
                print('Recorded batch %d: %d inputs' % (len(batches), len(group)), flush=True)
        finally:
            tempfile.tempdir = old_tempdir
    return {'corpus_sha256': digest(corpus), 'consumer_version': version.strip(),
            'batch_size': BATCH_SIZE, 'command': ['debug', 'prompt-input', 'x'],
            'projection': 'Verbatim skills_instructions strings; scratch paths normalized; other prompt content omitted.',
            'batches': batches}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('generate', 'record'))
    parser.add_argument('--codex', help='absolute path to the installed CLI; used only by record')
    args = parser.parse_args()
    if args.command == 'generate':
        CORPUS.write_text(encoded(generate()), encoding='utf-8')
        print('Generated', len(generate()['shapes']), 'shapes; seeds', SEEDS)
    else:
        if not args.codex or not Path(args.codex).is_absolute():
            parser.error('record requires --codex with an absolute executable path')
        corpus = json.loads(CORPUS.read_text())
        if corpus != generate():
            parser.error('regenerate the corpus first')
        result = record(corpus, args.codex)
        RECORDING.write_text(encoded(result), encoding='utf-8')
        print(result['consumer_version'], result['corpus_sha256'])
