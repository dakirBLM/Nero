from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """WhiteNoise manifest static storage that tolerates missing files.

    With the default (strict) manifest storage, a template that references a
    static file which wasn't collected — e.g. an optional asset not in the repo —
    raises ValueError and returns a 500 for the whole page. Setting
    manifest_strict = False makes it fall back to the plain filename instead, so a
    single missing asset can't take a page down. Files that DO exist are still
    hashed + compressed for cache-busting.
    """

    manifest_strict = False
