# Allow optional phone capture over the LAN

The end product may let a phone record, review, and save Entries through the desktop app over the local network, departing from the localhost-only MVP. LAN access is off by default and requires HTTPS plus a shared password; phones cannot browse the archive or capture offline. This trades a larger attack surface and certificate setup for more convenient nightly capture while keeping the journal on one machine.
