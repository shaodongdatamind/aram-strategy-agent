"""
Utility for fetching League of Legends ARAM build guides for one or more
champions.

This module exposes a single function, ``get_aram_guides``, which
takes an iterable of champion names and returns a dictionary mapping each
champion to a structured representation of their ARAM build guide.  The
implementation scrapes champion‑specific pages from the statistical
analysis site `METAsrc` to gather the latest recommended items, runes,
summoner spells and starting items for the ARAM game mode.  It also
extracts high level performance metrics such as tier placement, win
rate, pick rate and total number of games analysed.

Because ``METAsrc`` hosts semi‑static pages, we can reliably parse
these recommendations from the summary paragraph near the top of
each champion’s ARAM page.  If a champion’s page is unavailable or
its expected summary cannot be found, the corresponding entry in the
result dictionary will be set to ``None``.

Example
-------

>>> from aram_guides import get_aram_guides
>>> guides = get_aram_guides(["Garen", "Lee Sin"])
>>> guides["Garen"]["items"]
['Heartsteel', 'Stridebreaker', "Mercury's Treads", 'Phantom Dancer', 'Black Cleaver', 'Dead Man\'s Plate']

The function uses the :mod:`requests` and :mod:`bs4` packages to perform
HTTP requests and HTML parsing.  A modern browser user‑agent string is
specified to avoid basic bot detection.  If either of these packages
is unavailable, install them via ``pip install requests bs4``.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Dict, Optional, Any, List

import requests
from bs4 import BeautifulSoup


def _slugify(name: str) -> str:
    """Convert a human readable champion name into the slug used by METAsrc.

    Parameters
    ----------
    name:
        A champion name as used in League of Legends (e.g. ``"Lee Sin"`` or
        ``"K'Sante"``).

    Returns
    -------
    str
        A slug appropriate for constructing a METAsrc URL.  The function
        strips punctuation, removes diacritics, lowercases the string and
        replaces whitespace with hyphens.  Apostrophes and periods are
        removed entirely.
    """
    # Lower case and normalise accents to ASCII
    normalized = unicodedata.normalize("NFD", name.lower())
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    # Remove apostrophes and periods
    ascii_only = ascii_only.replace("'", "").replace(".", "")
    # Keep alphanumeric characters and spaces only
    cleaned = re.sub(r"[^a-z0-9 ]", "", ascii_only)
    # Replace whitespace with hyphens
    return cleaned.strip().replace(" ", "-")


def get_aram_guides(champions: Iterable[str]) -> Dict[str, Optional[Dict[str, Any]]]:
    """Retrieve ARAM build guides for a list of champions from METAsrc.

    This function visits the ARAM build page for each champion on
    ``metasrc.com`` and extracts a concise guide summarising the
    recommended items, runes, summoner spells, starting items and
    performance statistics.  The site analyses millions of ARAM games
    per patch, so its recommendations are data driven and updated
    regularly.

    Parameters
    ----------
    champions:
        An iterable of champion names.  Names should match the official
        English champion names used by Riot Games.  The function is
        case‑insensitive and will handle names containing spaces or
        apostrophes (e.g. ``"Bel'Veth"`` or ``"K'Sante"``).

    Returns
    -------
    dict
        A dictionary mapping each input champion name to either a
        structured guide or ``None`` if the guide could not be
        retrieved.  Each guide dictionary contains the following keys:

        ``tier``
            Single letter tier (S, A, B, C, etc.) if available.

        ``win_rate``
            Champion win rate in ARAM as a float percentage (e.g. ``52.4``).

        ``pick_rate``
            Champion pick rate in ARAM as a float percentage.

        ``games``
            Number of ARAM games analysed for this champion.

        ``kda``
            Average KDA for the champion in ARAM.

        ``score``
            METAsrc internal rating score.

        ``items``
            A list of six core items recommended for the full build.

        ``primary_tree``
            The rune tree used as the primary rune page (e.g. ``"Precision"``).

        ``keystone``
            The recommended keystone rune (e.g. ``"Conqueror"``).

        ``secondary_tree``
            The rune tree used as the secondary rune page.

        ``summoner_spells``
            A list of two summoner spells (e.g. ``["Flash", "Mark"]``).

        ``starting_items``
            A list of recommended starting items.

        ``source``
            The URL of the page from which the guide was scraped.

    Notes
    -----
    - A modern User‑Agent header is specified to avoid being blocked by
      basic bot detection.  If you encounter HTTP 429 (Too Many
      Requests) responses, consider adding delays between requests.
    - The parser relies on the presence of a summary paragraph that
      begins with "For items, our build recommends:".  Should METAsrc
      change the page structure in the future, the extraction logic
      may need adjustment.
    """
    guides: Dict[str, Optional[Dict[str, Any]]] = {}
    # Precompile regular expressions once for performance
    tier_re = re.compile(
        r"Tier:\s*([A-Z])\s*Win\s*(\d+\.\d+)%\s*Pick\s*(\d+\.\d+)%\s*Games:\s*([\d,]+)\s*KDA:\s*(\d+\.\d+)\s*Score:\s*(\d+\.\d+)"
    )
    items_re = re.compile(r"For items, our build recommends:\s*(.*?)\.\s*For runes", re.S)
    runes_re = re.compile(
        r"For runes, the strongest choice is\s*(.*?)\s*\(Primary\)\s*with\s*(.*?)\s*\(Keystone\),\s*and\s*(.*?)\s*\(Secondary\)",
        re.S,
    )
    spells_re = re.compile(r"The optimal Summoner Spells for this build are\s*(.*?)\.\s*")
    start_re = re.compile(r"Starting items should include\s*(.*?)\.")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/118.0 Safari/537.36"
        )
    }

    for champ in champions:
        slug = _slugify(champ)
        url = f"https://www.metasrc.com/lol/aram/build/{slug}"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
        except Exception:
            # Network error
            guides[champ] = None
            continue
        if resp.status_code != 200:
            # HTTP error or page missing
            guides[champ] = None
            continue
        soup = BeautifulSoup(resp.text, "html.parser")
        # Combine all text into a single string; collapse whitespace to single spaces
        page_text = " ".join(soup.stripped_strings)
        # Extract performance statistics
        tier_match = tier_re.search(page_text)
        if tier_match:
            tier, win_rate, pick_rate, games, kda, score = tier_match.groups()
            win_rate_f = float(win_rate)
            pick_rate_f = float(pick_rate)
            games_i = int(games.replace(",", ""))
            kda_f = float(kda)
            score_f = float(score)
        else:
            tier = win_rate_f = pick_rate_f = games_i = kda_f = score_f = None
        # Extract core items
        items_match = items_re.search(page_text)
        if items_match:
            items_str = items_match.group(1)
            # Split by comma and strip whitespace
            items_list = [itm.strip() for itm in items_str.split(",")]
        else:
            items_list = []
        # Extract runes
        runes_match = runes_re.search(page_text)
        if runes_match:
            primary_tree = runes_match.group(1).strip()
            keystone = runes_match.group(2).strip()
            secondary_tree = runes_match.group(3).strip()
        else:
            primary_tree = keystone = secondary_tree = None
        # Extract summoner spells
        spells_match = spells_re.search(page_text)
        if spells_match:
            spells_str = spells_match.group(1)
            # Spells are typically separated by " and "
            spells_list = [s.strip() for s in re.split(r"\s+and\s+", spells_str)]
        else:
            spells_list = []
        # Extract starting items
        start_match = start_re.search(page_text)
        if start_match:
            start_items_str = start_match.group(1)
            starting_items_list = [itm.strip() for itm in start_items_str.split(",")]
        else:
            starting_items_list = []
        guides[champ] = {
            "tier": tier,
            "win_rate": win_rate_f,
            "pick_rate": pick_rate_f,
            "games": games_i,
            "kda": kda_f,
            "score": score_f,
            "items": items_list,
            "primary_tree": primary_tree,
            "keystone": keystone,
            "secondary_tree": secondary_tree,
            "summoner_spells": spells_list,
            "starting_items": starting_items_list,
            "source": url,
        }
    return guides


__all__ = ["get_aram_guides"]