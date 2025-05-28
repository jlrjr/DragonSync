"""
MIT License

Copyright (c) 2024 cemaxecuter

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import threading
import os
import configparser
import logging

logger = logging.getLogger(__name__)

DEFAULT_AFFILIATION_INI = "affiliation.ini"

_affiliation_cache = {}
_affiliation_mtime = None
_affiliation_lock = threading.Lock()

def load_affiliations(affiliation_file=DEFAULT_AFFILIATION_INI):
    """
    Load (and reload on change) UID-to-affiliation mappings from an INI file.
    Returns: dict { uid_string: affiliation_type }
    """
    global _affiliation_cache, _affiliation_mtime
    with _affiliation_lock:
        try:
            mtime = os.path.getmtime(affiliation_file)
            if mtime == _affiliation_mtime:
                return _affiliation_cache
            config = configparser.ConfigParser()
            config.read(affiliation_file)
            d = {}
            for section in ("authorized", "unauthorized", "unknown"):
                raw = config.get(section, "uids", fallback="")
                for uid in (x.strip() for x in raw.split(",") if x.strip()):
                    d[uid] = section
            _affiliation_cache = d
            _affiliation_mtime = mtime
            logger.info(f"Affiliation file '{affiliation_file}' loaded ({len(d)} entries)")
            return d
        except Exception as e:
            logger.warning(f"Failed to load affiliation file: {e}")
            return _affiliation_cache
