from filmdeck.core import parser


def test_classify_lines():
    c = parser.classify_line
    assert c("wrote /s/.driver/roll-001/f3.tiff (450x300, 16-bit RGB)").data == {
        "frame": 3, "path": "/s/.driver/roll-001/f3.tiff"}
    assert c("wrote /s/my film/roll-002/f12.tiff (1x1)").kind == "wrote_main"
    assert c("wrote /s/roll-001/f3.overscan.tiff (1x1)").kind == "text"
    assert c("wrote /s/roll-001/f3-ir.tiff (1x1)").kind == "text"
    assert c("=== digitize roll 4 -> /x/roll-004 ===").data == {"roll": 4, "dir": "/x/roll-004"}
    assert c("stopping: empty aperture at frame 5 after film; x").kind == "stopping"
    assert c("ejected").kind == "ejected"
    assert c("roll 2 done: 6 frames -> /x").data == {"roll": 2, "frames": 6}
    assert c("error: boom").kind == "problem" and c("Warning: x").kind == "problem"
    assert c("running the vendor app-start jog (a)").kind == "load_jog"
    assert c("load sequence completed").kind == "load_done"
    assert c("something else").kind == "text"


def test_classify_failure():
    f = parser.classify_failure
    assert f(3, "") == ("busy", False)
    assert f(2, "usage") == ("bad_args", False)
    assert f(1, "error: Plustek OpticFilm 135i not found on the host USB bus") == ("no_scanner", False)
    assert f(1, "usb.core.USBError: [Errno 13] Access denied (insufficient permissions)") == ("no_permission", False)
    assert f(1, "usb.core.NoBackendError: No backend available") == ("no_backend", False)
    assert f(1, "error: no magazine present in the slot (loader sensor clear)") == ("no_magazine", False)
    assert f(1, "refused: --next-strip: the scanner is COLD (x)") == ("cold", False)
    assert f(1, "error: the load feed did not engage. Power the scanner OFF and ON") == ("load_failed", True)
    assert f(130, "interrupted") == ("interrupted", True)
    assert f(1, "error: x. Restarting this program is NOT sufficient") == ("scan_failed", True)
    assert f(1, "error: something") == ("scan_failed", False)


def test_parse_status():
    ok = parser.parse_status(0, "reg 0x01 = 0x22\n  start state: idle-homed\n"
                                "magazine: sensor reports present (does not prove it is locked)\nbutton: idle\n", "")
    assert ok.ok and ok.magazine is True and ok.start_state == "idle-homed" and not ok.power_cycle
    none = parser.parse_status(0, "  start state: unsafe\nmagazine: not detected\n", "")
    assert none.magazine is False and none.power_cycle
    bad = parser.parse_status(1, "", "error: ... not found on the host USB bus")
    assert not bad.ok and bad.error == "no_scanner"
    odd = parser.parse_status(1, "", "error: weird")
    assert odd.error == "status_failed"
