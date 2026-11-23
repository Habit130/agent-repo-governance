"""The machine and generator must redact text at the terminal boundary (#254)."""

import unittest
from pathlib import Path
from textwrap import dedent

from output_redaction import program_writes, unredacted_writes


class OutputRedaction(unittest.TestCase):
    def program_sources(self):
        root = Path(__file__).resolve().parents[2]
        sources = {}
        for directory in ("machine/scripts", "generator/govern-repository/scripts"):
            programs = sorted((root / directory).rglob("*.py"))
            self.assertTrue(programs, "No Python sources found in " + directory)
            for program in programs:
                path = program.relative_to(root).as_posix()
                sources[path] = program.read_bytes()
        return sources

    def test_machine_and_generator_terminal_writes_are_redacted(self):
        """write_line handles CLI diagnostics (and the fixed govlib bootstrap refusal).
        govern.emit serializes generator facts. wizard.say prints account guidance.
        Each writer's own payload must pass the same check as a new direct write.
        """
        try:
            problems = ["%s:%d" % location for location in program_writes(self.program_sources())]
        except SyntaxError as error:
            raise self.failureException("Cannot parse %s:%d" % (error.filename, error.lineno or 1)) from None
        if problems:
            self.fail("Unredacted terminal write:\n" + "\n".join(problems))

    def test_checks_each_terminal_write_and_only_its_emitted_payload(self):
        source = dedent("""\
            import os, sys
            from govlib import secrets
            print(message)
            sys.stdout.write(secrets.redact(message))
            sys.stderr.write(message)
            os.write(1, raw_bytes)
            os.write(2, secrets.redact(message).encode())
            print(secrets.redact(message), end=raw_suffix)
            print(secrets.redact(message), raw_suffix)
            print(secrets.redact(message) + raw_suffix)
            os.write(3, raw_bytes)
            with open("report", "w") as report:
                print(message, file=report)
                report.write(message)
            subprocess.run(args, stdout=subprocess.PIPE)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [3, 5, 6, 8, 9, 10])

    def test_a_writer_name_or_a_nearby_redaction_cannot_bless_a_raw_write(self):
        paths_and_sinks = (
            ("machine/scripts/machine.py", "write_line", "stream"),
            ("machine/scripts/machinelib/wizard.py", "say", "sys.stdout"),
            ("generator/govern-repository/scripts/govern.py", "emit", "sys.stdout"),
        )
        for path, writer, sink in paths_and_sinks:
            source = dedent("""\
                import sys
                from govlib.secrets import redact
                def %s(text, stream):
                    safe = redact(text)
                    %s.write(safe)
                    %s.write(text)
            """) % (writer, sink, sink)
            with self.subTest(writer=writer):
                self.assertEqual(unredacted_writes(path, source), [6])

    def test_standard_streams_and_descriptors_keep_their_identity_through_aliases(self):
        source = dedent("""\
            from builtins import print as display
            from os import fdopen, write as send
            from sys import stderr as err
            from govlib.secrets import redact as scrub
            output = err.buffer.write
            display(message, file=None)
            output(raw_bytes)
            output(scrub(message).encode())
            fd = err.fileno()
            send(fd, raw_bytes)
            with fdopen(2, "w") as stream:
                stream.writelines([scrub(first), second])
            with open(1, "w", closefd=False) as stream:
                print(scrub(message), file=stream, end="\\n")
            with fdopen(2, "wb", closefd=False) as binary:
                binary.write(scrub(raw_bytes))
                binary.write(scrub(message).encode())
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [6, 7, 10, 12, 16])

    def test_only_the_shared_function_can_establish_redaction(self):
        source = dedent("""\
            from govlib.secrets import redact
            def local(redact, text):
                print(redact(text))
            def other(text):
                from unrelated import redact
                print(redact(text))
            def mixed(text, condition):
                value = redact(text)
                if condition:
                    value = text
                print(value)
            def genuine(text):
                from .secrets import redact
                print(redact(text))
        """)
        path = "generator/govern-repository/scripts/govlib/sample.py"
        self.assertEqual(unredacted_writes(path, source), [3, 6, 11])

    def test_machine_uri_cleanup_preserves_only_its_redacted_input_and_fixed_refusal(self):
        source = dedent("""\
            import re
            from govlib.secrets import redact as scrub
            _URI = re.compile(".+")
            def _hide_private_uri(match):
                return raw
            def write_line(message, stream):
                cleaned = scrub(message)
                line = cleaned if scrub else "拒绝：找不到 generator 的 govlib"
                stream.write(line)
                stream.write(_URI.sub(_hide_private_uri, cleaned))
                stream.write(cleaned if scrub else message)
        """)
        self.assertEqual(unredacted_writes("machine/scripts/machine.py", source), [10, 11])

    def test_changing_redacted_data_before_the_write_invalidates_its_origin(self):
        source = dedent("""\
            from govlib.secrets import redact
            facts = redact(report)
            facts["extra"] = message
            print(facts)
            lines = redact(messages)
            lines.append(message)
            print(lines)
            original = redact(report)
            alias = original
            alias["extra"] = message
            print(original)
            def add_note(target):
                target["extra"] = message
            other = redact(report)
            add_note(other)
            print(other)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [4, 7, 11, 16])

    def test_a_write_uses_the_value_reaching_that_statement(self):
        source = dedent("""\
            from govlib.secrets import redact
            def show(text, condition):
                print(text)
                text = redact(text)
                print(text)
                if condition:
                    text = raw
                print(text)
                text = redact(text)
                text = text + "\\n"
                print(text)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [3, 8])

    def test_opaque_descriptors_and_bound_stream_methods_are_checked_at_the_write(self):
        source = dedent("""\
            import sys
            fd = int("2")
            with open(fd, "w", closefd=False) as destination:
                destination.write(message)
            send = getattr(sys.stderr, "write")
            send(message)
            def announce(message, send=print):
                send(message)
            with open(b"/dev/stderr", "wb") as binary:
                binary.write(message)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [4, 6, 8, 10])

    def test_a_file_path_from_a_list_requires_a_path_return_and_no_other_list_writes(self):
        library = "generator/govern-repository/scripts/govlib/storedform.py"
        program = "generator/govern-repository/scripts/sample.py"
        source = dedent("""\
            from govlib import storedform
            rows = []
            rows.append((storedform.check_target(root, name), data))
            for path, text in rows:
                with open(path, "w") as report:
                    report.write(text)
        """)
        helper = 'import os\ndef check_target(root, name):\n    return os.path.join(root, "report.txt")\n'
        self.assertEqual(program_writes({library: helper, program: source}), [])
        self.assertEqual(program_writes({library: helper.replace('os.path.join(root, "report.txt")', "2"),
                                         program: source}), [(program, 6)])
        self.assertEqual(program_writes({library: helper.replace('"report.txt"', "name"), program: source}), [])
        extra = source.replace("for path,", "rows.extend(other_rows)\nfor path,")
        self.assertEqual(program_writes({library: helper, program: extra}), [(program, 7)])

    def test_definition_expressions_and_shared_bindings_use_their_python_scope(self):
        source = dedent("""\
            from govlib.secrets import redact
            def report(print=print(message)):
                pass
            value = redact(message)
            def replace():
                global value
                value = message
            replace()
            print(value)
            def outer():
                data = redact(message)
                def change():
                    nonlocal data
                    data = message
                change()
                print(data)
            def comprehension(items):
                print(message)
                return [print for print in items]
            def captured():
                facts = redact(message)
                def insert():
                    facts["note"] = message
                insert()
                print(facts)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [2, 9, 16, 18, 25])

    def test_reconstructed_terminal_paths_and_methods_remain_terminal(self):
        source = dedent("""\
            import os, sys
            root = "/dev/"
            open(root + "stderr", "w").write(raw)
            open(os.path.join(base, "/dev/stderr"), "w").write(raw)
            name = "write"
            getattr(sys.stderr, name)(raw)
            class Report:
                def emit(self):
                    self.path = "/tmp/log"
                    alias = self
                    alias.path = "/dev/stderr"
                    open(self.path, "w").write(raw)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [3, 4, 6, 12])

    def test_an_escaped_or_augmented_redacted_container_needs_fresh_redaction(self):
        source = dedent("""\
            from govlib.secrets import redact
            data = redact(messages)
            alias = data
            alias += [raw]
            print(data)
            rows = redact(messages)
            add = rows.append
            add(raw)
            print(rows)
            groups = redact(data)
            modify(groups[0], raw)
            print(groups)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [5, 9, 12])

    def test_declarations_resolve_reads_and_keep_possible_terminal_callables(self):
        source = dedent("""\
            import sys
            from govlib.secrets import redact
            message = raw
            def outer():
                message = redact(raw)
                emit = None
                def show():
                    global message
                    print(message)
                def setup():
                    nonlocal emit
                    emit = sys.stderr.write
                setup()
                emit(raw)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [9, 14])

    def test_builtin_fallbacks_and_getattr_defaults_can_write_to_the_terminal(self):
        source = dedent("""\
            import sys
            def emit(raw):
                global print
                print(raw)
                attr = "missing"
                getattr(sys.stderr, attr, sys.stderr.write)(raw)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [4, 6])
        source = "if quiet:\n    print = lambda *items: None\n" + source
        self.assertEqual(unredacted_writes("sample.py", source), [6, 8])
        source = dedent("""\
            emit = print
            class Reporter:
                if quiet:
                    emit = muted
                    print = muted
                emit(raw)
                print(raw)
            print = muted
            del print
            print(raw)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [6, 7, 10])
        locally_shadowed = "if quiet:\n    print = lambda *items: None\n    print(raw)"
        self.assertEqual(unredacted_writes("sample.py", locally_shadowed), [])

    def test_returned_and_stored_references_can_change_the_value_eventually_printed(self):
        source = dedent("""\
            from govlib.secrets import redact
            data = redact(messages)
            def expose():
                return data
            external = expose()
            external.append(raw)
            print(data)
            values = redact(messages)
            holder.data = values
            holder.data.append(raw)
            print(values)
            rows = redact(messages)
            handler.write(rows)
            print(rows)
            nested = redact(messages)
            holder.data = nested if enabled else []
            holder.data.append(raw)
            print(nested)
            another = redact(messages)
            (holder.data,) = (another,)
            holder.data.append(raw)
            print(another)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [7, 11, 14, 18, 22])

    def test_setting_a_destination_through_an_alias_revokes_the_file_proof(self):
        source = dedent("""\
            class Writer:
                def run(self):
                    self.path = "/tmp/report"
                    alias = self
                    setattr(alias, "path", "/dev/stderr")
                    open(self.path, "w").write(raw)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [6])
        unrelated = dedent("""\
            class Other:
                def __init__(self):
                    self.path = "/dev/stderr"
            class FileReport:
                def save(self, raw):
                    self.path = "/tmp/report"
                    open(self.path, "w").write(raw)
        """)
        self.assertEqual(unredacted_writes("sample.py", unrelated), [])

    def test_aliases_can_cross_scopes_but_formatted_text_is_a_snapshot(self):
        source = dedent("""\
            from govlib.secrets import redact
            rows = redact(messages)
            def save():
                global exposed
                exposed = rows
            save()
            exposed.append(raw)
            print(rows)
            clean = redact(messages)
            holder.summary = f"Message: {clean}"
            print(clean)
            def outer():
                data = redact(messages)
                def inner():
                    local = data
                    local.append(raw)
                inner()
                print(data)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [8, 18])

    def test_file_path_arguments_and_direct_terminal_destinations(self):
        source = dedent("""\
            import os
            def save(root, filename, data):
                with open(os.path.join(root, filename), "wb") as disk:
                    disk.write(data)
                with open(os.path.join("/dev", filename), "wb") as possible_terminal:
                    possible_terminal.write(data)
                fd = get_descriptor()
                with open(fd, "wb", closefd=False) as possible_terminal:
                    possible_terminal.write(data)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [6, 9])
        other = "class Runner:\n    def __init__(self, task):\n        self.run = task\n"
        findings = program_writes({"sample.py": source, "worker.py": other})
        self.assertEqual(findings, [("sample.py", 6), ("sample.py", 9)])

    def test_pathname_literals_survive_unpacking_and_string_interpolation(self):
        source = dedent("""\
            import os
            device = "stderr"
            parts = ("/dev", device)
            open(os.path.join(root, *("/dev", "stderr")), "w").write(raw)
            open(os.path.join(root, *parts), "w").write(raw)
            open(os.path.join(f"/dev/{device}"), "w").write(raw)
            open(os.path.join("/tmp", *("dev", device)), "w").write(raw)
            open(f"/tmp/{device}", "w").write(raw)
            base = "/dev/std" if condition else "/tmp/std"
            open(f"{base}err", "w").write(raw)
            branches = ("/tmp", "log")
            def redirect():
                global branches
                branches = ("/dev", "stderr")
            redirect()
            open(os.path.join(root, *branches), "w").write(raw)
            open(f"/dev/shm/report-{request_id}.txt", "w").write(raw)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [4, 5, 6, 10, 16])

    def test_global_deletion_restores_print_for_nested_and_module_reads(self):
        source = dedent("""\
            print = lambda *items: None
            def clear():
                global print
                del print
            clear()
            print(raw)
            def emit():
                global print
                print(raw)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [6, 9])

    def test_inherited_methods_see_subclass_fields_but_unrelated_classes_keep_their_own(self):
        source = dedent("""\
            class Base:
                def save(self):
                    self.path = self.destination
                    open(self.path, "w").write(raw)
                def __init__(self):
                    self.destination = "/tmp/report"
            class Child(Base):
                def __init__(self):
                    self.destination = "/dev/stderr"
            class Separate:
                def save(self):
                    self.path = "/tmp/separate"
                    open(self.path, "w").write(raw)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [4])

    def test_class_attribute_overrides_and_rebound_imports_do_not_hide_device_writes(self):
        target = dedent("""\
            class Target:
                def __init__(self):
                    self.path = "/tmp/report"
                def emit(self, data):
                    open(self.path, "w").write(data)
            class Other: pass
            Other = Target
        """)
        caller = 'from target import Other\nitem = Other()\nitem.path = "/dev/stderr"\nitem.emit(data)\n'
        self.assertEqual(program_writes({"target.py": target, "caller.py": caller}), [("target.py", 5)])
        original = target.replace("Other = Target\n", "")
        redirect = "import target\ntarget.Other = target.Target\n"
        self.assertEqual(program_writes({"target.py": original, "redirect.py": redirect, "caller.py": caller}),
                         [("target.py", 5)])
        subclass = dedent("""\
            class Child(Target):
                path = "/dev/stderr"
                def __init__(self): pass
        """)
        self.assertEqual(unredacted_writes("target.py", target + subclass), [5])
        alias = original + "Alias = Target\n"
        child = 'from target import Alias\nclass Child(Alias):\n    def __init__(self): self.path = "/dev/stderr"\n'
        self.assertEqual(program_writes({"target.py": alias, "child.py": child}), [("target.py", 5)])

    def test_field_annotations_are_not_assignments(self):
        source = dedent("""\
            class Report:
                path: str
                def __init__(self):
                    self.path = "/tmp/report"
                def save(self):
                    self.path: str
                    open(self.path, "w").write(raw)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [])

    def test_shared_tuple_alternatives_keep_their_components_together(self):
        source = dedent("""\
            import os
            parts = ("/dev", "shm/report.txt")
            def select():
                global parts
                parts = ("/tmp", "stderr")
            select()
            open(os.path.join(*parts), "w").write(raw)
        """)
        self.assertEqual(unredacted_writes("sample.py", source), [])
        identical = source.replace('("/tmp", "stderr")', '("/dev", "shm/report.txt")')
        self.assertEqual(unredacted_writes("sample.py", identical), [])
        mutated = 'import os\nparts = ["/tmp", "log"]\nparts[:] = ["/dev", "stderr"]\n'
        self.assertEqual(unredacted_writes("sample.py", mutated + 'open(os.path.join(*parts), "w").write(raw)'), [4])
        split = 'import os\npath = "/dev/stderr" if mode else "/tmp/log"\n'
        emit = 'open(os.path.join("/", *path.split("/")), "w").write(raw)'
        self.assertEqual(unredacted_writes("sample.py", split + emit), [3])
