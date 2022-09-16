import asyncio
import logging

import aiohttp
import pymorphy2
from anyio import create_task_group, TASK_STATUS_IGNORED
from anyio.abc import TaskStatus
from async_timeout import timeout

from adapters import ArticleNotFound
from enums import ProcessingStatus
from text_tools import calculate_jaundice_rate, read_charged_words, split_by_words


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


async def get_results(results_queue):
    result = await results_queue.get()
    print(result)


async def process_article(
        session, morph, charged_words, url, results_queue,
        task_status: TaskStatus = TASK_STATUS_IGNORED,
):
    task_status.started()

    score = None
    words_count = None

    try:
        async with timeout(4):
            html = await fetch(session, url)
    except aiohttp.ClientResponseError:
        status = ProcessingStatus.FETCH_ERROR.value
    except asyncio.TimeoutError:
        status = ProcessingStatus.TIMEOUT.value
    else:
        try:
            ''
            # sanitized_text = SANITIZERS['inosmi_ru'](html, plaintext=True)
        except ArticleNotFound:
            status = ProcessingStatus.PARSING_ERROR.value
        else:
            try:
                article_words = split_by_words(morph, html)
            except TimeoutError:
                status = ProcessingStatus.TIMEOUT.value
            else:
                words_count = len(article_words)
                score = calculate_jaundice_rate(article_words, charged_words)
                status = ProcessingStatus.OK.value

    results_queue.put_nowait(
        {
            'URL': url,
            'http_status': status,
            'score': score,
            'words_count': words_count,
        }
    )


async def main():
    charged_words = await read_charged_words()
    results_queue = asyncio.Queue()
    morph = pymorphy2.MorphAnalyzer()

    # test_articles = [
    #     'https://inosmi.ru/20220908/polonez-255973070.html',
    #     'https://lenta.ru/brief/2021/08/26/afg_terror/',
    #     'https://inosmi.ru/20220909/ukraina-256005416.html',
    #     'https://inosmi.ru/20220909/evro-25600579.html',
    #     'https://inosmi.ru/20220909/korolevstvo-256004302.html',
    # ]
    test_articles = [
        'https://dvmn.org/media/filer_public/51/83/51830f54-7ec7-4702-847b-c5790ed3724c/gogol_nikolay_taras_bulba_-_bookscafenet.txt']

    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in test_articles:
                tg.start_soon(process_article, session, morph, charged_words, url, results_queue)
                tg.start_soon(get_results, results_queue)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('pymorphy2.opencorpora_dict.wrapper').setLevel(logging.WARNING)
    asyncio.run(main())
