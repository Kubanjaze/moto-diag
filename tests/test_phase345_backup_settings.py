"""Phase 345 — the backup's key file and working folder.

The five names, the mode, the refusals naming a name and never a value, the
names-only repr with its planted-value control, and the synced-folder
refusal with its control.
"""

from __future__ import annotations

import pytest
from support.phase345 import FAKE_VALUES, write_env

from motodiag.backup import settings as bs
from motodiag.backup.settings import (
    ENV_NAMES,
    KEY_ID,
    PASSPHRASE,
    SECRET,
    BackupConfigError,
    load_backup_settings,
    names_in,
    refuse_synced,
    work_dir,
)

SECRET_VALUES = (FAKE_VALUES[SECRET], FAKE_VALUES[PASSPHRASE], FAKE_VALUES[KEY_ID])


def _leaks(text: str) -> list[str]:
    return [v for v in SECRET_VALUES if v in text]


def test_the_five_names_are_k62s_four_and_the_passphrase():
    assert ENV_NAMES == ("MOTODIAG_BACKUP_S3_ENDPOINT", "MOTODIAG_BACKUP_S3_BUCKET",
                         "MOTODIAG_BACKUP_S3_KEY_ID", "MOTODIAG_BACKUP_S3_SECRET",
                         "MOTODIAG_BACKUP_PASSPHRASE")


def test_a_600_file_is_read(tmp_path):
    s = load_backup_settings(write_env(tmp_path / "backup.env"))
    assert (s.secret, s.passphrase) == (FAKE_VALUES[SECRET], FAKE_VALUES[PASSPHRASE])
    assert s.bucket == FAKE_VALUES["MOTODIAG_BACKUP_S3_BUCKET"]


def test_the_env_variable_names_another_file(tmp_path, monkeypatch):
    path = write_env(tmp_path / "other.env")
    monkeypatch.setenv("MOTODIAG_BACKUP_ENV", str(path))
    assert load_backup_settings().path == path


@pytest.mark.parametrize("mode", [0o640, 0o604, 0o660])
def test_a_mode_granting_group_or_others_is_refused(tmp_path, mode):
    path = write_env(tmp_path / "backup.env", mode=mode)
    with pytest.raises(BackupConfigError, match="must be 600") as e:
        load_backup_settings(path)
    assert not _leaks(str(e.value))


def test_a_missing_file_is_refused(tmp_path):
    with pytest.raises(BackupConfigError, match="missing"):
        load_backup_settings(tmp_path / "nope.env")


@pytest.mark.parametrize("name", ENV_NAMES)
def test_one_missing_name_is_refused_by_its_name_and_no_value(tmp_path, name):
    values = {k: v for k, v in FAKE_VALUES.items() if k != name}
    path = write_env(tmp_path / "backup.env", values)
    with pytest.raises(BackupConfigError) as e:
        load_backup_settings(path)
    assert name in str(e.value)
    assert not _leaks(str(e.value))
    assert [v for v in FAKE_VALUES.values() if v in str(e.value)] == []


def test_an_empty_value_is_refused(tmp_path):
    path = write_env(tmp_path / "backup.env", {**FAKE_VALUES, SECRET: ""})
    with pytest.raises(BackupConfigError, match=SECRET):
        load_backup_settings(path)


def test_comments_blank_lines_and_quotes(tmp_path):
    path = tmp_path / "backup.env"
    lines = ["# the backup's key", ""] + [f'{k}="{v}"' for k, v in FAKE_VALUES.items()]
    path.write_text("\n".join(lines) + "\n")
    path.chmod(0o600)
    assert load_backup_settings(path).secret == FAKE_VALUES[SECRET]


def test_repr_and_str_carry_names_only_with_the_control(tmp_path):
    s = load_backup_settings(write_env(tmp_path / "backup.env"))
    for text in (repr(s), str(s), f"{s}", repr([s])):
        assert not _leaks(text), text
        assert SECRET in text
    # The control: the same assertion goes red on a value printed on purpose.
    assert _leaks(f"{s} {s.secret}") == [FAKE_VALUES[SECRET]]


def test_names_in_lists_names_present_and_never_values(tmp_path):
    path = write_env(tmp_path / "backup.env", {k: v for k, v in FAKE_VALUES.items()
                                               if k != PASSPHRASE})
    held = names_in(path)
    assert PASSPHRASE not in held and SECRET in held
    assert not _leaks(" ".join(held))
    assert names_in(tmp_path / "absent.env") == []


@pytest.mark.parametrize("folder", ["OneDrive/backups", "Library/CloudStorage/x",
                                    "Dropbox/m", "Library/Mobile Documents/y"])
def test_a_synced_work_folder_is_refused(tmp_path, folder):
    with pytest.raises(BackupConfigError, match="synced"):
        refuse_synced(tmp_path / folder)


def test_a_windows_drive_is_refused():
    with pytest.raises(BackupConfigError, match="Windows drive"):
        refuse_synced(bs.Path("/mnt/c/Users/someone/backups"))


def test_the_control_a_plain_temp_folder_is_not_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("MOTODIAG_BACKUP_WORK_DIR", str(tmp_path / "offsite"))
    folder = work_dir()
    assert folder == (tmp_path / "offsite").resolve() and folder.is_dir()
    assert oct(folder.stat().st_mode & 0o777) == oct(0o700)


def test_the_work_folder_override_is_refused_when_synced(tmp_path, monkeypatch):
    monkeypatch.setenv("MOTODIAG_BACKUP_WORK_DIR", str(tmp_path / "OneDrive" / "offsite"))
    with pytest.raises(BackupConfigError):
        work_dir()
    assert not (tmp_path / "OneDrive").exists()


def test_the_default_work_folder():
    assert bs.DEFAULT_WORK.parts[-3:] == ("backups", "motodiag", "offsite")
