from nanolance.counting import CountingFile


def test_a_fresh_file_has_an_empty_tally(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(bytes(range(10)))
    with CountingFile(path) as f:
        assert f.tally() == "reads 0, bytes read 0, seeks 0"


def test_reads_and_their_bytes_are_counted(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(bytes(range(10)))
    with CountingFile(path) as f:
        assert f.read(4) == bytes([0, 1, 2, 3])
        assert f.read(4) == bytes([4, 5, 6, 7])
        assert f.read(4) == bytes([8, 9])  # only two bytes were left
        assert (f.reads, f.bytes_read, f.seeks) == (3, 10, 0)


def test_seeks_are_counted_and_move_the_position(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(bytes(range(10)))
    with CountingFile(path) as f:
        f.seek(7)
        assert f.read(2) == bytes([7, 8])
        f.seek(0)
        assert f.read(1) == bytes([0])
        assert (f.reads, f.bytes_read, f.seeks) == (2, 3, 2)
