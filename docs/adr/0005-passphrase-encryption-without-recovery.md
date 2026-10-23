# Encrypt the journal with a non-recoverable passphrase

Entries and the search index are encrypted at rest with a journal passphrase, separate from the LAN password. There is no recovery mechanism: a forgotten passphrase means the journal is unrecoverable, in exchange for preventing anyone with filesystem access or a recovery secret from reading it. Explicit plaintext export remains available after unlocking.
