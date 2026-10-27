"""Analogy: the tally — the picker's clipboard, marked on every trip.

A file you read through a CountingFile counts its own work: how many reads
were issued, how many bytes came back, and how many times the reader told
the file where to go next (every seek request counts, even one to the
current position). Every "this reads less" claim in the course is one of
these counts.
"""

from pathlib import Path


class CountingFile:
    """A binary file opened for reading that counts reads, bytes, and seeks."""

    def __init__(self, path: Path) -> None:
        self._file = open(path, "rb")
        self.reads = 0
        self.bytes_read = 0
        self.seeks = 0

    def read(self, size: int) -> bytes:
        """Read up to `size` bytes from the current position."""
        data = self._file.read(size)
        self.reads += 1
        self.bytes_read += len(data)
        return data

    def seek(self, offset: int) -> None:
        """Jump to byte `offset`, counted from the start of the file."""
        self._file.seek(offset)
        self.seeks += 1

    def tally(self) -> str:
        return f"reads {self.reads}, bytes read {self.bytes_read}, seeks {self.seeks}"

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "CountingFile":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
