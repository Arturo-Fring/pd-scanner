"""Compiled regex patterns used by the detectors."""

from __future__ import annotations

import re


EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]{1,64}@[a-zA-Z0-9.-]+\.[A-Za-z]{2,24}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+7|7|8)?[\s\-()]*(?:\d[\s\-()]*){10,11}(?!\d)")
DATE_RE = re.compile(r"\b(?:0?[1-9]|[12]\d|3[01])[./-](?:0?[1-9]|1[0-2])[./-](?:19\d{2}|20\d{2})\b")
PASSPORT_RF_RE = re.compile(r"(?<!\d)(\d{2}\s?\d{2}\s?\d{6})(?!\d)")
SNILS_RE = re.compile(r"(?<!\d)(\d{3}-\d{3}-\d{3}\s?\d{2}|\d{11})(?!\d)")
INN_RE = re.compile(r"(?<!\d)(\d{10}|\d{12})(?!\d)")
BANK_CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
BANK_ACCOUNT_RE = re.compile(r"(?<!\d)(\d{20})(?!\d)")
BIK_RE = re.compile(r"(?<!\d)(\d{9})(?!\d)")
DRIVER_LICENSE_RE = re.compile(r"(?<!\d)(\d{2}\s?\d{2}\s?\d{6})(?!\d)")
MRZ_LINE_RE = re.compile(r"\b[A-Z0-9<]{25,44}\b")
CVV_CONTEXT_RE = re.compile(
    r"\b(?:cvv|cvc|security code|код безопасности)\b[:\s#-]{0,5}(\d{3,4})\b",
    re.IGNORECASE,
)
FIO_CONTEXT_RE = re.compile(
    r"\b(?:фио|фамилия\s+имя\s+отчество|full name)\b[:\s-]{0,6}"
    r"([А-ЯЁ][а-яё-]+(?:\s+[А-ЯЁ][а-яё-]+){1,2})",
    re.IGNORECASE,
)
FIO_VALUE_RE = re.compile(
    r"\b[А-ЯЁ][а-яё-]{1,30}\s+[А-ЯЁ][а-яё-]{1,30}(?:\s+[А-ЯЁ][а-яё-]{1,30})?\b"
)
ADDRESS_RE = re.compile(
    r"\b(?:адрес|место жительства|место регистрации|registration address|address)\b"
    r"[:\s-]{0,6}([^\n\r;]{8,180})",
    re.IGNORECASE,
)
BIRTH_PLACE_RE = re.compile(
    r"\b(?:место рождения|birth place)\b[:\s-]{0,6}([^\n\r;]{2,120})",
    re.IGNORECASE,
)
