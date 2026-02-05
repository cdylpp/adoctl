import unittest


from adoctl.util.url import encode_path_segment, join_url


class TestUrlEncoding(unittest.TestCase):
    def test_encode_path_segment_space(self) -> None:
        self.assertEqual(encode_path_segment("Black Lagoon"), "Black%20Lagoon")

    def test_encode_path_segment_no_double_encode(self) -> None:
        self.assertEqual(encode_path_segment("Black%20Lagoon"), "Black%20Lagoon")

    def test_encode_path_segment_slash(self) -> None:
        self.assertEqual(encode_path_segment("A/B"), "A%2FB")

    def test_encode_path_segment_unicode(self) -> None:
        self.assertEqual(encode_path_segment("München"), "M%C3%BCnchen")

    def test_join_url_encodes_each_segment(self) -> None:
        url = join_url("https://dev.azure.com/MyOrg", "Black Lagoon", "_apis", "teams")
        self.assertEqual(url, "https://dev.azure.com/MyOrg/Black%20Lagoon/_apis/teams")

    def test_join_url_preserves_base_path(self) -> None:
        url = join_url("https://example.com/foo/bar/", "Black Lagoon", "_apis", "projects")
        self.assertEqual(url, "https://example.com/foo/bar/Black%20Lagoon/_apis/projects")


if __name__ == "__main__":
    unittest.main()

