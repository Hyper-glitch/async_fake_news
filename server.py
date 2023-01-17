"""Module for all server logic."""
import asyncio
import logging
import time

import aiohttp
import pymorphy2
from aiohttp import web
from anyio import create_task_group, TASK_STATUS_IGNORED
from anyio.abc import TaskStatus
from async_timeout import timeout

import adapters
from adapters import ArticleNotFound
from enums import ProcessingStatus
from settings import TIMEOUT_FETCH_EXPIRED_SEC, MAX_URLS_AMOUNT, MIN_RUNTIME_SEC
from text_tools import calculate_jaundice_rate, read_charged_words, split_by_words


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def process_article(
    session,
    morph,
    charged_words,
    url,
    analyzed_results,
    task_status: TaskStatus = TASK_STATUS_IGNORED,
):
    task_status.started()

    score = None
    words_count = None

    try:
        async with timeout(TIMEOUT_FETCH_EXPIRED_SEC):
            html = await fetch(session, url)
    except aiohttp.ClientResponseError:
        status = ProcessingStatus.FETCH_ERROR.value
    except asyncio.TimeoutError:
        status = ProcessingStatus.TIMEOUT.value
    else:
        try:
            sanitized_text = adapters.SANITIZERS["inosmi_ru"](html, plaintext=True)
        except ArticleNotFound:
            status = ProcessingStatus.PARSING_ERROR.value
        else:
            try:
                start = time.monotonic()
                article_words = await split_by_words(morph, sanitized_text)
                end = time.monotonic()
                if end - start > MIN_RUNTIME_SEC:
                    raise TimeoutError
                logging.info(f"Анализ закончен за {end - start} сек")
            except TimeoutError:
                status = ProcessingStatus.TIMEOUT.value
            else:
                words_count = len(article_words)
                score = calculate_jaundice_rate(article_words, charged_words)
                status = ProcessingStatus.OK.value

    analyzed_results.append(
        {
            "URL": url,
            "http_status": status,
            "score": score,
            "words_count": words_count,
        }
    )


async def handle_articles_query(request):
    query = request.query.get("urls")
    analyzed_results = []
    if not query:
        return web.json_response(analyzed_results)

    splitted_urls = query.split(",")
    ddos_condition = len(splitted_urls) > MAX_URLS_AMOUNT

    if ddos_condition:
        return web.json_response(
            {"error": "too many urls in request, should be 10 or less"}, status=400
        )

    charged_words = await read_charged_words()
    morph = pymorphy2.MorphAnalyzer()

    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in splitted_urls:
                tg.start_soon(
                    process_article,
                    session,
                    morph,
                    charged_words,
                    url,
                    analyzed_results,
                )
