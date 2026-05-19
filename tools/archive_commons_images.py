import argparse
import html
import json
import mimetypes
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


USER_AGENT = "CocktailWiki/0.1 (https://example.local; local-dev@example.local)"
ENWIKI_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"

TITLE_OVERRIDES = {
    "Dark ‘n' stormy": ["Dark 'n' Stormy", "Dark 'n' Stormy (cocktail)"],
    "KIR": ["Kir (cocktail)", "Kir"],
    "Last word": ["Last Word (cocktail)", "Last Word"],
    "Long Island Ice Tea": ["Long Island iced tea", "Long Island iced tea (cocktail)"],
    "Pina Colada": ["Piña colada", "Pina colada"],
    "Spritz": ["Spritz (cocktail)", "Spritz Veneziano"],
    "Vieux Carrè": ["Vieux Carré (cocktail)", "Vieux Carré"],
}


def request_json(api_url, params, delay=0.8):
    time.sleep(delay)
    params = {"format": "json", **params}
    url = f"{api_url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Api-User-Agent": USER_AGENT,
        },
    )

    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise
            retry_after = error.headers.get("Retry-After")
            wait = int(retry_after) if retry_after and retry_after.isdigit() else 8 * (attempt + 1)
            time.sleep(wait)
        except urllib.error.URLError:
            if attempt == 4:
                raise
            time.sleep(3 * (attempt + 1))

    raise RuntimeError("API request failed")


def download_file(url, output_path):
    time.sleep(1.0)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                output_path.write_bytes(response.read())
            return
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise
            retry_after = error.headers.get("Retry-After")
            wait = int(retry_after) if retry_after and retry_after.isdigit() else 10 * (attempt + 1)
            time.sleep(wait)
        except urllib.error.URLError:
            if attempt == 4:
                raise
            time.sleep(10 * (attempt + 1))


def chunked(items, size):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def normalize_title(value):
    value = value.replace("File:", "", 1)
    value = value.replace("_", " ")
    return re.sub(r"\s+", " ", value).strip().lower()


def normalize_match(value):
    value = html.unescape(strip_html(value or ""))
    value = value.lower()
    value = value.replace("‘", "'").replace("’", "'").replace("è", "e").replace("é", "e")
    value = value.replace("ñ", "n").replace("í", "i")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def slugify(value):
    value = normalize_match(value)
    slug = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return slug or "cocktail"


def strip_html(value):
    return re.sub(r"<[^>]+>", "", value or "").strip()


def clean_text(value):
    return html.unescape(strip_html(value or "")).strip()


def get_meta_value(metadata, key):
    value = metadata.get(key, {})
    return value.get("value", "") if isinstance(value, dict) else ""


def is_free_license(license_name, usage_terms):
    text = f"{license_name} {usage_terms}".lower()
    blocked = ["non-commercial", "noncommercial", "no derivatives", "nonderivatives", "fair use"]
    if any(term in text for term in blocked):
        return False

    allowed = ["public domain", "cc0", "cc by", "cc-by", "attribution", "share alike", "share-alike"]
    return any(term in text for term in allowed)


def candidate_titles(name):
    titles = []
    for title in TITLE_OVERRIDES.get(name, []):
        titles.append(title)
    titles.extend([f"{name} (cocktail)", name])

    seen = set()
    unique_titles = []
    for title in titles:
        key = title.lower()
        if key not in seen:
            unique_titles.append(title)
            seen.add(key)
    return unique_titles


def fetch_wikipedia_pageimages(cocktails):
    title_to_name = {}
    ordered_titles = []

    for cocktail in cocktails:
        name = cocktail["name"]
        for title in candidate_titles(name):
            title_to_name[title] = name
            ordered_titles.append(title)

    page_images = {}
    redirects = {}
    normalized = {}

    for titles in chunked(ordered_titles, 20):
        response = request_json(
            ENWIKI_API,
            {
                "action": "query",
                "redirects": "1",
                "titles": "|".join(titles),
                "prop": "pageimages",
                "piprop": "original|name",
            },
        )

        for item in response.get("query", {}).get("redirects", []):
            redirects[item["from"]] = item["to"]
        for item in response.get("query", {}).get("normalized", []):
            normalized[item["from"]] = item["to"]

        for page in response.get("query", {}).get("pages", {}).values():
            if "missing" in page or "pageimage" not in page:
                continue
            page_images[page["title"]] = {
                "file_title": f"File:{page['pageimage']}",
                "page_title": page["title"],
            }

    result = {}
    for cocktail in cocktails:
        name = cocktail["name"]
        for title in candidate_titles(name):
            resolved = redirects.get(normalized.get(title, title), normalized.get(title, title))
            if resolved in page_images:
                result[name] = {
                    **page_images[resolved],
                    "matched_by": "wikipedia-pageimage",
                }
                break

    return result


def search_wikipedia_pageimage(name):
    response = request_json(
        ENWIKI_API,
        {
            "action": "query",
            "list": "search",
            "srsearch": f'"{name}" cocktail',
            "srlimit": "5",
        },
        delay=0.8,
    )

    for result in response.get("query", {}).get("search", []):
        title = result["title"]
        page_response = request_json(
            ENWIKI_API,
            {
                "action": "query",
                "redirects": "1",
                "titles": title,
                "prop": "pageimages",
                "piprop": "original|name",
            },
            delay=0.8,
        )

        pages = page_response.get("query", {}).get("pages", {}).values()
        for page in pages:
            if "pageimage" in page:
                return {
                    "file_title": f"File:{page['pageimage']}",
                    "page_title": page["title"],
                    "matched_by": "wikipedia-search-pageimage",
                }

    return None


def fetch_commons_metadata(file_titles, thumb_width):
    metadata_by_title = {}

    for titles in chunked(sorted(set(file_titles)), 20):
        response = request_json(
            COMMONS_API,
            {
                "action": "query",
                "titles": "|".join(titles),
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|size|mime",
                "iiurlwidth": str(thumb_width),
            },
        )

        for page in response.get("query", {}).get("pages", {}).values():
            infos = page.get("imageinfo")
            if not infos:
                continue

            info = infos[0]
            ext = info.get("extmetadata", {})
            license_name = clean_text(get_meta_value(ext, "LicenseShortName"))
            usage_terms = clean_text(get_meta_value(ext, "UsageTerms"))

            if not is_free_license(license_name, usage_terms):
                continue

            metadata_by_title[normalize_title(page["title"])] = {
                "fileTitle": page["title"],
                "sourcePage": info.get("descriptionurl", ""),
                "downloadUrl": info.get("thumburl") or info.get("url", ""),
                "originalUrl": info.get("url", ""),
                "width": info.get("width"),
                "height": info.get("height"),
                "mime": info.get("mime", ""),
                "title": clean_text(get_meta_value(ext, "ObjectName")),
                "description": clean_text(get_meta_value(ext, "ImageDescription")),
                "author": clean_text(get_meta_value(ext, "Artist")),
                "credit": clean_text(get_meta_value(ext, "Credit")),
                "license": license_name,
                "usageTerms": usage_terms,
                "licenseUrl": clean_text(get_meta_value(ext, "LicenseUrl")),
            }

    return metadata_by_title


def search_commons_image(name, thumb_width):
    for query in (f'"{name}" cocktail', f"{name} cocktail"):
        response = request_json(
            COMMONS_API,
            {
                "action": "query",
                "generator": "search",
                "gsrsearch": query,
                "gsrnamespace": "6",
                "gsrlimit": "8",
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|size|mime",
                "iiurlwidth": str(thumb_width),
            },
            delay=0.8,
        )

        pages = sorted(
            response.get("query", {}).get("pages", {}).values(),
            key=lambda page: page.get("index", 999),
        )

        for page in pages:
            infos = page.get("imageinfo")
            if not infos:
                continue

            info = infos[0]
            if not info.get("mime", "").startswith("image/"):
                continue

            ext = info.get("extmetadata", {})
            license_name = clean_text(get_meta_value(ext, "LicenseShortName"))
            usage_terms = clean_text(get_meta_value(ext, "UsageTerms"))
            if not is_free_license(license_name, usage_terms):
                continue

            text_for_match = " ".join(
                [
                    page.get("title", ""),
                    get_meta_value(ext, "ObjectName"),
                    get_meta_value(ext, "ImageDescription"),
                    get_meta_value(ext, "Categories"),
                ]
            )
            if normalize_match(name) not in normalize_match(text_for_match):
                continue

            return {
                "candidate": {
                    "file_title": page["title"],
                    "page_title": "",
                    "matched_by": "commons-search",
                },
                "metadata": {
                    "fileTitle": page["title"],
                    "sourcePage": info.get("descriptionurl", ""),
                    "downloadUrl": info.get("thumburl") or info.get("url", ""),
                    "originalUrl": info.get("url", ""),
                    "width": info.get("width"),
                    "height": info.get("height"),
                    "mime": info.get("mime", ""),
                    "title": clean_text(get_meta_value(ext, "ObjectName")),
                    "description": clean_text(get_meta_value(ext, "ImageDescription")),
                    "author": clean_text(get_meta_value(ext, "Artist")),
                    "credit": clean_text(get_meta_value(ext, "Credit")),
                    "license": license_name,
                    "usageTerms": usage_terms,
                    "licenseUrl": clean_text(get_meta_value(ext, "LicenseUrl")),
                },
            }

    return None


def extension_for(metadata):
    extension = mimetypes.guess_extension(metadata.get("mime", ""))
    if extension == ".jpe":
        extension = ".jpg"
    if extension:
        return extension

    path = urllib.parse.urlparse(metadata["downloadUrl"]).path
    return Path(path).suffix or ".jpg"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="iba_cocktails_translated.json")
    parser.add_argument("--output", default="cocktail_images.json")
    parser.add_argument("--image-dir", default="assets/images/cocktails")
    parser.add_argument("--thumb-width", type=int, default=1200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cocktails = json.loads(Path(args.data).read_text(encoding="utf-8"))
    image_dir = Path(args.image_dir)
    if not args.dry_run:
        image_dir.mkdir(parents=True, exist_ok=True)

    print("Fetching Wikipedia page images...")
    candidates = fetch_wikipedia_pageimages(cocktails)

    missing_names = [cocktail["name"] for cocktail in cocktails if cocktail["name"] not in candidates]
    for name in missing_names:
        print(f"Searching Wikipedia fallback: {name}")
        candidate = search_wikipedia_pageimage(name)
        if candidate:
            candidates[name] = candidate

    print("Fetching Commons license metadata...")
    metadata = fetch_commons_metadata(
        [candidate["file_title"] for candidate in candidates.values()],
        args.thumb_width,
    )

    records = {}
    missing = []
    needs_review = []

    for cocktail in cocktails:
        name = cocktail["name"]
        candidate = candidates.get(name)
        item = metadata.get(normalize_title(candidate["file_title"])) if candidate else None

        if not item:
            print(f"Searching Commons fallback: {name}")
            fallback = search_commons_image(name, args.thumb_width)
            if fallback:
                candidate = fallback["candidate"]
                item = fallback["metadata"]

        if not item:
            missing.append(name)
            continue

        extension = extension_for(item)
        file_name = f"{slugify(name)}{extension}"
        relative_path = f"assets/images/cocktails/{file_name}"

        if not args.dry_run:
            download_file(item["downloadUrl"], image_dir / file_name)

        records[name] = {
            "src": relative_path,
            "sourcePage": item["sourcePage"],
            "originalUrl": item["originalUrl"],
            "fileTitle": item["fileTitle"],
            "author": item["author"],
            "credit": item["credit"],
            "license": item["license"],
            "usageTerms": item["usageTerms"],
            "licenseUrl": item["licenseUrl"],
            "width": item["width"],
            "height": item["height"],
            "matchedBy": candidate["matched_by"],
            "wikipediaPage": candidate["page_title"],
        }

        if candidate["matched_by"] != "wikipedia-pageimage":
            needs_review.append(name)

    output = {
        "source": "Wikimedia Commons",
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "thumbnailWidth": args.thumb_width,
        "images": records,
        "missing": missing,
        "needsReview": needs_review,
    }

    if not args.dry_run:
        Path(args.output).write_text(
            json.dumps(output, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(f"Images: {len(records)}")
    print(f"Missing: {len(missing)}")
    if missing:
        print(", ".join(missing))
    if needs_review:
        print(f"Needs review: {len(needs_review)}")
        print(", ".join(needs_review))


if __name__ == "__main__":
    main()
