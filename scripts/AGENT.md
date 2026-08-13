# Script Agent Rules

- Use `argparse`, `pathlib`, explicit exit codes, and `if __name__ == "__main__"`.
- Never use `shell=True`, embed cloud endpoints, auto-download without confirmation,
  delete originals, or accept an unchecked path.
- `--help` performs no I/O. Destructive/replacement operations require explicit target
  and preserve backup according to the migration/save policy.
- Add CLI tests for help, success, invalid input, and dependency/capability absence.
- Keep scripts import-safe and delegate all rules to typed library functions.
