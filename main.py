import asyncio

import aiohttp
import pymorphy2
from anyio import create_task_group, TASK_STATUS_IGNORED
from anyio.abc import TaskStatus

import adapters
from text_tools import calculate_jaundice_rate, split_by_words, read_charged_words


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def process_article(session, morph, charged_words, url, task_status: TaskStatus = TASK_STATUS_IGNORED):
    task_status.started()

    html = await fetch(session, url)
    sanitized_text = adapters.SANITIZERS['inosmi_ru'](html, plaintext=True)
    article_words = split_by_words(morph, sanitized_text)
    words_count = len(article_words)
    score = calculate_jaundice_rate(article_words, charged_words)

    print('URL:', url)
    print('Рейтинг:', score)
    print('Слов в статье:', words_count)


async def main():
    charged_words = await read_charged_words()
    morph = pymorphy2.MorphAnalyzer()

    test_articles = [
        'https://inosmi.ru/20220908/polonez-255973070.html',
        'https://inosmi.ru/20220909/evrei-256006103.html',
        'https://inosmi.ru/20220909/ukraina-256005416.html',
        'https://inosmi.ru/20220909/evro-256005079.html',
        'https://inosmi.ru/20220909/korolevstvo-256004302.html',
    ]
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in test_articles:
                tg.start_soon(process_article, session, morph, charged_words, url)


asyncio.run(main())
