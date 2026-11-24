from scripts.ailina_previews import add_previews, candidates, public_url, MARKER
from scripts.ailina_postprocess import parse_stories


def digest(n=18):
    return "\n\n".join(
        f'<a id="item-ailina-{i}"></a>\n### [Story {i}](https://example.com/{i}) ⭐️ 6.0/10\n\nBody {i}\n\n---'
        for i in range(n)
    ) + "\n"


def test_preview_priority_and_relative_urls():
    html = '''<head><meta name="twitter:image" content="/social.png">
        <meta property="og:image" content="https://cdn.example.com/photo.jpg">
        </head><meta property="og:image:secure_url" content="/fake.jpg">'''
    assert candidates(html, "https://example.com/article") == [
        "https://cdn.example.com/photo.jpg", "https://example.com/social.png"
    ]


def test_preview_limit_preserves_news_and_is_idempotent():
    original = digest()
    def lookup(url):
        return "https://example.com/p.jpg?x=1&y=2" if url.endswith("/0") else ""
    result, count, found = add_previews(original, lookup)
    assert (count, found) == (15, 1)
    assert len(MARKER.findall(result)) == 15
    assert "x=1&amp;y=2" in result
    assert MARKER.sub("", result) == original
    assert len(parse_stories(result)) == 18
    assert add_previews(result, lookup)[0] == result


def test_reject_unsafe_urls():
    for url in ("file:///etc/passwd", "https://localhost/a", "https://127.0.0.1/a",
                "http://169.254.169.254/latest", "https://user:pass@example.com/x",
                "https://example.com:8443/x"):
        assert public_url(url) is None
    assert public_url("http://example.com/image.jpg", image=True) is None
