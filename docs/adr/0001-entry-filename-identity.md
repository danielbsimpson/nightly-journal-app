# Entry filenames embed both a human label and the Entry ID

Entries are stored as one JSON file each, and we want the folder to stay browsable in a file manager without adding an index that could drift out of agreement with the files. Files are therefore named `YYYY-MM-DD_slug_ab12cd34.json`, where the suffix is the first eight characters of the Entry's UUID: the date sorts, the slug reads, and the suffix makes lookup by ID a directory glob rather than a parse of every file.

## Considered Options

- **`<uuid>.json`** — correct and trivial, but the folder becomes unreadable, which gives up most of the reason to use files instead of a database.
- **Human name plus a separate ID-to-path index file** — keeps names readable, but creates a second source of truth that can desynchronise from the files it describes.

## Consequences

The slug is a snapshot of the Title at the moment the Entry was saved. Editing an Entry's Title deliberately does **not** rename its file, so filenames may drift from Titles over time. The UUID inside the file remains authoritative; the filename is a convenience.
