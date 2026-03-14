def _cache_key(self, query: str):
    import hashlib
    return hashlib.md5(query.encode()).hexdigest()