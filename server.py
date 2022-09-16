"""Module for all server logic."""
import asyncio

import aiohttp
import pymorphy2
from aiohttp import web
from anyio import create_task_group, TASK_STATUS_IGNORED
from anyio.abc import TaskStatus
from async_timeout import timeout

import adapters
from adapters import ArticleNotFound
from enums import ProcessingStatus
from settings import TIMEOUT_FETCH_EXPIRED_SEC
from text_tools import calculate_jaundice_rate, read_charged_words, split_by_words


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def process_article(
        session, morph, charged_words, url, analyzed_results, task_status: TaskStatus = TASK_STATUS_IGNORED,
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
            sanitized_text = adapters.SANITIZERS['inosmi_ru'](html, plaintext=True)
        except ArticleNotFound:
            status = ProcessingStatus.PARSING_ERROR.value
        else:
            try:
                article_words = split_by_words(morph, sanitized_text)
            except TimeoutError:
                status = ProcessingStatus.TIMEOUT.value
            else:
                words_count = len(article_words)
                score = calculate_jaundice_rate(article_words, charged_words)
                status = ProcessingStatus.OK.value

    analyzed_results.append(
        {
            'URL': url,
            'http_status': status,
            'score': score,
            'words_count': words_count,
        }
    )


async def handle_articles_query(request):
    query = dict(request.query)
    analyzed_results = []

    if query:
        query['urls'] = query['urls'].split(',')
        charged_words = await read_charged_words()
        morph = pymorphy2.MorphAnalyzer()

        async with aiohttp.ClientSession() as session:
            async with create_task_group() as tg:
                for url in query['urls']:
                    tg.start_soon(process_article, session, morph, charged_words, url, analyzed_results)

    return web.json_response(analyzed_results)
