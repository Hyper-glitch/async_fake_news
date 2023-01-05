import logging

from aiohttp import web

from server import handle_articles_query


def set_up_logger():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("pymorphy2.opencorpora_dict.wrapper").setLevel(logging.WARNING)
    logging.getLogger("aiohttp.access").setLevel(logging.WARNING)


def run_server():
    app = web.Application()
    app.add_routes([web.get("/", handle_articles_query)])
    web.run_app(app)


if __name__ == "__main__":
    set_up_logger()
    run_server()
