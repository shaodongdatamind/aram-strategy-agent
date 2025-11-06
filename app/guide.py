from __future__ import annotations

import logging
import re
import time
import unicodedata
from typing import List

import httpx

from .state import Snippet

logger = logging.getLogger(__name__)


def slugify_champion(name: str) -> str:
    """Convert champion name to URL slug format used by METAsrc."""
    normalized = unicodedata.normalize("NFD", name.lower())
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_only = ascii_only.replace("'", "").replace(".", "")
    cleaned = re.sub(r"[^a-z0-9 ]", "", ascii_only)
    return cleaned.strip().replace(" ", "-")


def _fetch_guide(champ_name: str, client: httpx.Client) -> str | None:
    """Fetch high-quality ARAM guide from metasrc.com using proven extraction patterns."""
    slug = slugify_champion(champ_name)
    url = f"https://www.metasrc.com/lol/aram/build/{slug}"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36",
    }
    
    try:
        resp = client.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        
        html_text = resp.text
        
        # Remove scripts and styles to get clean text
        clean_html = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL | re.IGNORECASE)
        clean_html = re.sub(r'<style[^>]*>.*?</style>', '', clean_html, flags=re.DOTALL | re.IGNORECASE)
        
        # Extract text content (remove HTML tags and collapse whitespace)
        text_content = re.sub(r'<[^>]+>', ' ', clean_html)
        text_content = ' '.join(text_content.split())
        
        parts = []
        
        # Extract items using proven pattern
        items_re = re.compile(r"For items, our build recommends:\s*(.*?)\.\s*For runes", re.S)
        items_match = items_re.search(text_content)
        if items_match:
            items_str = items_match.group(1)
            items_list = [itm.strip() for itm in items_str.split(",")]
            if items_list:
                parts.append(f"Core items: {', '.join(items_list[:6])}")
        
        # Extract runes
        runes_re = re.compile(
            r"For runes, the strongest choice is\s*(.*?)\s*\(Primary\)\s*with\s*(.*?)\s*\(Keystone\),\s*and\s*(.*?)\s*\(Secondary\)",
            re.S,
        )
        runes_match = runes_re.search(text_content)
        if runes_match:
            primary_tree = runes_match.group(1).strip()
            keystone = runes_match.group(2).strip()
            secondary_tree = runes_match.group(3).strip()
            rune_info = f"{keystone} ({primary_tree}) with {secondary_tree}"
            parts.append(f"Runes: {rune_info}")
        
        # Extract summoner spells
        spells_re = re.compile(r"The optimal Summoner Spells for this build are\s*(.*?)\.\s*")
        spells_match = spells_re.search(text_content)
        if spells_match:
            spells_str = spells_match.group(1)
            spells_list = [s.strip() for s in re.split(r"\s+and\s+", spells_str)]
            if spells_list:
                parts.append(f"Summoner spells: {', '.join(spells_list)}")
        
        # Extract starting items
        start_re = re.compile(r"Starting items should include\s*(.*?)\.")
        start_match = start_re.search(text_content)
        if start_match:
            start_items_str = start_match.group(1)
            starting_items_list = [itm.strip() for itm in start_items_str.split(",")]
            if starting_items_list:
                parts.append(f"Starting items: {', '.join(starting_items_list)}")
        
        # Extract win rate and tier
        tier_re = re.compile(
            r"Tier:\s*([A-Z])\s*Win\s*(\d+\.\d+)%\s*Pick\s*(\d+\.\d+)%\s*Games:\s*([\d,]+)\s*KDA:\s*(\d+\.\d+)\s*Score:\s*(\d+\.\d+)"
        )
        tier_match = tier_re.search(text_content)
        if tier_match:
            tier, win_rate, pick_rate, games, kda, score = tier_match.groups()
            parts.append(f"Tier {tier}, Win rate: {win_rate}%, Pick rate: {pick_rate}%, KDA: {kda}")
        
        if parts:
            text = ". ".join(parts)
            if len(text) > 800:
                text = text[:797] + "..."
            return text.strip()
        
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch guide for {champ_name}: {e}")
        return None


def fetch_guides(champ_names: List[str]) -> List[Snippet]:
    """
    Fetch ARAM guides at runtime for given champion names.
    Returns list of Snippet objects.
    """
    if not champ_names:
        return []
    
    snippets: List[Snippet] = []
    with httpx.Client(follow_redirects=True, timeout=15) as client:
        for champ in champ_names:
            if not champ:
                continue
            text = _fetch_guide(champ, client)
            if text:
                snippets.append(Snippet(
                    id=slugify_champion(champ),
                    champ=champ,
                    text=text,
                ))
            # Be polite - small delay between requests
            time.sleep(0.2)
    
    logger.debug(f"Fetched {len(snippets)} guides for {len(champ_names)} champions")
    return snippets
