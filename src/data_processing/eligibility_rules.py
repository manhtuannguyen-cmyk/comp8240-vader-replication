"""Shared text-only eligibility heuristics; no sentiment labels or text mutation."""
from __future__ import annotations
import re
from langdetect import detect_langs, DetectorFactory, LangDetectException

DetectorFactory.seed=42
SHORT_ENGLISH={'lol','lmao','lmfao','bruh','wow','nice','thanks','amazing','love','great','good','bad','cool','awesome','yes','no','fr','ngl','tbh','idk','goat','rip','haha','hahaha','wtf','omg','bro','peak','based','cooked'}

def personal_information(text: str) -> bool:
    return bool(re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?:https?://)?(?:t\.me|wa\.me)/\S+|(?<!\w)\+\d[\d ()-]{8,}\d',text,re.I))

def classify(text: str) -> tuple[str,str,str]:
    if not text.strip():return 'exclude','empty','not_applicable'
    if personal_information(text):return 'exclude','personal_information','not_assessed'
    if re.fullmatch(r'(?:https?://\S+\s*)+',text.strip(),re.I):return 'exclude','links_only_no_meaningful_text','not_assessed'
    if re.search(r'\b(?:telegram|whatsapp)\b|\b(?:earn|make)\s*\$\d+|\bsubscribe to my channel\b',text,re.I):return 'review','possible_spam_or_advertising','uncertain'
    tokens=re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?",text.lower())
    if tokens and all(t in SHORT_ENGLISH for t in tokens):return 'include','recognized_english_informal_text','en_lexicon'
    if len(tokens)<5 or sum(c.isalpha() for c in text)<20:return 'review','short_or_language_uncertain','uncertain'
    try:
        predictions=detect_langs(text)
    except LangDetectException:return 'review','language_uncertain','uncertain'
    best=predictions[0]
    label=f'{best.lang}:{best.prob:.4f}'
    if best.lang=='en' and best.prob>=.95:return 'include','english_language_screen',label
    if best.lang!='en' and best.prob>=.99 and len(text.split())>=10:return 'exclude','non_english_high_confidence',label
    return 'review','language_uncertain',label

