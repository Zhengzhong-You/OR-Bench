# Local Research Archive

Historical research material that is not needed for the two current submissions is stored in the following local ZIP. Retired public package versions remain recoverable from prior Git history and are not part of the current repository tree.

- File: `OR-Bench-internal-archive-2026-08-04.zip`
- Size: 9,637,496 bytes (approximately 9.2 MiB)
- SHA-256: `ab79a095a4f10364ace42328f25d5ca1ee688c1d5ee75560357f0e497fe7f827`
- Integrity check: passed for all 496 ZIP entries

The archive contains internal experiment logs and raw model records, literature and call documents, superseded candidate problems, old modular scripts, temporary research outputs, the retired two-echelon PDF, and the detailed prompts, generated programs, manifests, and standalone checkers removed during the five-file package cleanup. It is intentionally excluded from GitHub because some contents are internal or third-party reference material.

To restore it into a separate directory:

```bash
unzip OR-Bench-internal-archive-2026-08-04.zip -d restored-internal-archive
```

Each active problem keeps only its README, DOCX business brief, CSV data, combined solver/verifier, and LaTeX source. The two compiled PDFs and repository-level licenses remain uncompressed.
