"""Interactive patch application with backup."""

from __future__ import annotations

import shutil
from pathlib import Path

from selftest.fixer.patch_generator import PatchSuggestion


def apply_patches(
    patches: list[PatchSuggestion],
    source_file: Path,
    backup_dir: Path,
    selected_indices: list[int] | None = None,
) -> list[int]:
    """Apply selected patches to source file.

    Args:
        patches: list of patch suggestions
        source_file: path to the original source file
        backup_dir: directory to store backup
        selected_indices: which patches to apply (1-based). None = all.

    Returns:
        List of applied patch indices
    """
    if not patches:
        return []

    if selected_indices is None:
        selected_indices = [p.index for p in patches]

    to_apply = [p for p in patches if p.index in selected_indices]
    if not to_apply:
        return []

    # Backup
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{source_file.name}.bak"
    shutil.copy2(source_file, backup_path)

    # Read source
    source_lines = source_file.read_text(encoding="utf-8").splitlines()

    # Apply patches in reverse order (to preserve line numbers)
    to_apply_sorted = sorted(to_apply, key=lambda p: p.line, reverse=True)
    applied = []

    for patch in to_apply_sorted:
        line_idx = patch.line - 1
        if 0 <= line_idx < len(source_lines):
            replacement_lines = patch.replacement.splitlines()
            source_lines[line_idx:line_idx + 1] = replacement_lines
            applied.append(patch.index)

    # Write back
    source_file.write_text("\n".join(source_lines) + "\n", encoding="utf-8")

    return sorted(applied)


def restore_backup(source_file: Path, backup_dir: Path) -> bool:
    """Restore file from backup.

    Returns:
        True if restored successfully
    """
    backup_path = backup_dir / f"{source_file.name}.bak"
    if not backup_path.exists():
        return False
    shutil.copy2(backup_path, source_file)
    return True
