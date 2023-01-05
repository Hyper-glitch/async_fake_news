import aiohttp
import pymorphy2
import pytest
import requests
from anyio import create_task_group

import adapters
from server import process_article
from text_tools import calculate_jaundice_rate, split_by_words


def test_calculate_jaundice_rate():
    assert -0.01 < calculate_jaundice_rate([], []) < 0.01
    assert (
        33.0
        < calculate_jaundice_rate(
            ["все", "аутсайдер", "побег"], ["аутсайдер", "банкротство"]
        )
        < 34.0
    )


def test_split_by_words():
    morph = pymorphy2.MorphAnalyzer()

    assert split_by_words(morph, "Во-первых, он хочет, чтобы") == [
        "во-первых",
        "хотеть",
        "чтобы",
    ]

    assert split_by_words(morph, "«Удивительно, но это стало началом!»") == [
        "удивительно",
        "это",
        "стать",
        "начало",
    ]


def test_sanitize():
    resp = requests.get("https://inosmi.ru/economic/20190629/245384784.html")
    resp.raise_for_status()
    clean_text = adapters.inosmi_ru.sanitize(resp.text)

    assert "В субботу, 29 июня, президент США Дональд Трамп" in clean_text
    assert "За несколько часов до встречи с Си" in clean_text

    assert '<img src="' in clean_text
    assert "<h1>" in clean_text

    clean_plaintext = adapters.inosmi_ru.sanitize(resp.text, plaintext=True)

    assert "В субботу, 29 июня, президент США Дональд Трамп" in clean_plaintext
    assert "За несколько часов до встречи с Си" in clean_plaintext

    assert '<img src="' not in clean_plaintext
    assert '<a href="' not in clean_plaintext
    assert "<h1>" not in clean_plaintext
    assert "</article>" not in clean_plaintext
    assert "<h1>" not in clean_plaintext


def test_sanitize_wrong_url():
    resp = requests.get("http://example.com")
    resp.raise_for_status()
    with pytest.raises(adapters.exceptions.ArticleNotFound):
        adapters.inosmi_ru.sanitize(resp.text)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_input,expected",
    [
        (
            {
                "url": "http://example.com",
            },
            "PARSING_ERROR",
        ),
        (
            {
                "url": "https://inosmi.ru/20230105/pridnestrove-259354265.html",
            },
            "OK",
        ),
        (
            {
                "url": "https://inosmi.ru/20230105/tseny-25945785.html",
            },
            "FETCH_ERROR",
        ),
        (
            {
                "url": "https://petertarka.com/",
            },
            "TIMEOUT",
        ),
    ],
)
async def test_process_article(test_input, expected):
    morph = pymorphy2.MorphAnalyzer()
    session = aiohttp.ClientSession()
    analyzed_results = []
    charged_words = ["авария", "авиакатастрофа", "ад"]
    async with create_task_group() as tg:
        tg.start_soon(
            process_article,
            session,
            morph,
            charged_words,
            test_input["url"],
            analyzed_results,
        )
    assert analyzed_results[0]["http_status"] == expected
