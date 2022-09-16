from aiohttp import web


async def handle(request):
    query = dict(request.query)
    if query:
        query['urls'] = query['urls'].split(',')
    return web.json_response(query)


app = web.Application()
app.add_routes([web.get('/', handle), web.get('/{query}', handle)])

if __name__ == '__main__':
    web.run_app(app, port=7777)
