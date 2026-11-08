import sys
import textwrap

from filmdeck.core.runner import ProcessRunner


def collect(argv, env=None, idle=0.0, answer=True):
    lines, prompts = [], []
    holder = {}

    def on_prompt(kind, text):
        prompts.append((kind, text))
        if answer:
            holder["r"].send_enter()

    r = ProcessRunner(argv, env or {}, on_line=lambda s, l: lines.append((s, l)), on_prompt=on_prompt,
                      idle_prompt_seconds=idle)
    holder["r"] = r
    r.start()
    return r, lines, prompts


def test_prompt_without_newline_is_seen_once_and_answered():
    code = textwrap.dedent('''
        import sys
        print("JOG done. take it out", flush=True)
        input("Press Enter when it is at the stop (Ctrl-C aborts; a power cycle is then required): ")
        print("after the prompt", flush=True)
        print("err line", file=sys.stderr, flush=True)
    ''')
    r, lines, prompts = collect([sys.executable, "-u", "-c", code])
    assert r.wait(20) == 0
    assert len(prompts) == 1 and prompts[0][0] == "reinsert"
    texts = [l for _, l in lines]
    assert "JOG done. take it out" in texts and "after the prompt" in texts
    assert ("err", "err line") in lines
    # the prompt text that ended up in front of "after the prompt" must not trigger a second dialog
    assert len(prompts) == 1


def test_split_chunks_and_crlf():
    code = ("import sys,time\n"
            "sys.stdout.write('abc'); sys.stdout.flush(); time.sleep(0.3)\n"
            "sys.stdout.write('def\\r\\nsecond\\rthird\\n'); sys.stdout.flush()\n")
    r, lines, _ = collect([sys.executable, "-u", "-c", code])
    assert r.wait(20) == 0
    assert [l for _, l in lines] == ["abcdef", "second", "third"]


def test_unknown_prompt_needs_the_word_enter_and_idle():
    code = "x = input('Hit Enter to go on: ')\nprint('go')\n"
    r, lines, prompts = collect([sys.executable, "-u", "-c", code], idle=0.5)
    assert r.wait(20) == 0
    assert prompts and prompts[0][0] == "unknown" and ("out", "go") in lines
    # a partial line that is not asking for Enter is never a prompt
    code2 = "import sys,time\nsys.stdout.write('working: '); sys.stdout.flush(); time.sleep(1.2)\nprint('done')\n"
    r2, _, prompts2 = collect([sys.executable, "-u", "-c", code2], idle=0.4)
    assert r2.wait(20) == 0 and not prompts2


def test_interrupt_exit_code_and_output():
    code = ("import time,sys\nprint('started', flush=True)\n"
            "try:\n    time.sleep(30)\nexcept KeyboardInterrupt:\n    print('bye', flush=True); sys.exit(130)\n")
    r, lines, _ = collect([sys.executable, "-u", "-c", code])
    while ("out", "started") not in lines:
        pass
    r.interrupt()
    assert r.wait(20) == 130 and "bye" in r.output()


def test_cannot_start():
    r = ProcessRunner(["/nonexistent/binary"], {})
    try:
        r.start()
        raise AssertionError("expected OSError")
    except OSError:
        pass
