from django.core.management.base import BaseCommand, CommandError
import requests
import json
import time
from django.conf import settings
import os
from bs4 import BeautifulSoup as bs
import re
import asyncio
import aiohttp

to_clean = re.compile('<.*?>')

headers = {
    "Cookie": "_fbp=fb.1.1660480602612.1324652329; aiADB_PV=1; antihacker_cookie=%23Africa/Casablanca%23-60%23linux%20x86_64%23Linux%230%2Cfalse%2Cfalse%23Google%20Inc.%20%28Intel%20Open%20Source%20Technology%20Center%29%7EANGLE%20%28Intel%20Open%20Source%20Technology%20Center%2C%20Mesa%20DRI%20Intel%28R%29%20HD%20Graphics%205500%20%28Broadwell%20GT2%29%20%2C%20OpenGL%204.5%29; recaptcha_cookie=%23Africa/Casablanca%23-60%23linux%20x86_64%23Linux%230%2Cfalse%2Cfalse%23Google%20Inc.%20%28Intel%20Open%20Source%20Technology%20Center%29%7EANGLE%20%28Intel%20Open%20Source%20Technology%20Center%2C%20Mesa%20DRI%20Intel%28R%29%20HD%20Graphics%205500%20%28Broadwell%20GT2%29%20%2C%20OpenGL%204.5%29",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"
}

new_data = []
ev = 50
alrd = {}
t = '\n\n\n\n\n\n'


async def get_chapter(s, index, index_col, index_chapter):
    link = new_data[index]['cols'][index_col]['chapters'][index_chapter]['link']

    async with s.get(link) as r:
        if r.status != 200:
            print(r.status)
            return
        #print('Id Chapter :', id_chapter)
        html = await r.text()
        b = bs(html, 'html.parser')
        prgs = b.select('.epcontent p')
        paragraphs = [prg.text for prg in prgs]
        dis = ['', ' ', '\xa0', 'ترجمة موقع ملوك الروايات. لا تُلهِكُم القراءة عن اداء الصلوات فى أوقاتها و لا تنسوا نصيبكم من القرآن', '---']

        k = '::split-here::'.join(paragraphs)
        xml = bs(k, 'lxml')
        pgs_wtags = xml.text.split('::split-here::')

        ln_prgs = len(pgs_wtags)
        p = 0
        while p < ln_prgs:
            pgs_wtags[p] = pgs_wtags[p].replace('\xa0', '').replace('\t', '')
            if pgs_wtags[p] not in dis:
                s = 0
                e = 0
                j = pgs_wtags[p]
                while s != -1 and e != -1:
                    s = pgs_wtags[p].find(
                        t, s)
                    e = j.find(
                        t, s+len(t))
                    if e != -1:
                        pgs_wtags[p] = j[:s] + \
                            j[:e+len(t)]

                if j.find('k') != -1 and j.find('n') != -1 and j.find('e') != -1:
                    j = ''

                if j.count(' ') == len(j):
                    del pgs_wtags[p]
                    ln_prgs -= 1
                    continue
                p += 1
            else:
                del pgs_wtags[p]
                ln_prgs -= 1
        new_data[index]['cols'][index_col]['chapters'][index_chapter]['prgs'] = pgs_wtags
        alrd[f'{index} {index_col} {index_chapter}'] = True
        return


async def get_chapters_tasks(s, index, index_col, start, end):
    tasks = []
    for chapter in range(start, end):
        if f'{index} {index_col} {chapter}' in alrd:
            continue
        task = asyncio.create_task(get_chapter(s, index, index_col, chapter))
        tasks.append(task)

    res = await asyncio.gather(*tasks)


async def get_chapters_main(index, index_col, start, end):
    async with aiohttp.ClientSession(headers=headers) as session:
        htmls = await get_chapters_tasks(session, index, index_col, start, end)

url = 'https://novel.pythonanywhere.com/'
def main():
    
    r = requests.get(f'{url}get_last_chapters')
    data = r.json()
    new = False
    new_col = False

    index = 0
    for novel in data:
        new_data.append(
            {'id': novel['id'], 'name': novel['name'], 'cols': []})
        link = novel['link']
        r = requests.get(link, headers=headers)
        if r.status_code == 200:
            b = bs(r.text, 'html.parser')
            collapsible = b.select('span.ts-chl-collapsible')[::-1]
            content = b.select('.ts-chl-collapsible-content')[::-1]
            ln = len(content)
            index_col = 0
            for i in range(ln):
                title = re.sub(to_clean, '', collapsible[i].text).replace(
                    '\n', '').replace('\t', '')
                if title == novel['last_col']['title']:
                    new_col = True

                if new_col:
                    new_data[index]['cols'].append({
                        'title': title,
                        'chapters': []
                    })
                    chs = content[i].select(
                        '.eplister.eplisterfull > ul > li > a')[::-1]

                    for ch in chs:

                        link = ch['href'].replace(
                            '\n', '').replace('\t', '')
                        children = ch.findChildren()
                        title_chapter = children[1].text.replace(
                            '\n', '').replace('\t', '')
                        number_chapter = children[0].text.replace(
                            '\n', '').replace('\t', '')
                        date_chapter = children[2].text.replace(
                            '\n', '').replace('\t', '')

                        if title_chapter == novel['last_chapter']['title'] and number_chapter == novel['last_chapter']['chapter']:
                            new = True
                            continue

                        if new:
                            new_data[index]['cols'][index_col]['chapters'].append({
                                'link': link,
                                'chapter': number_chapter,
                                'title': title_chapter,
                                'date': date_chapter,
                            })

                    ln_chapters = len(
                        new_data[index]['cols'][index_col]['chapters'])
                    opr = ln_chapters // ev + (ln_chapters % ev != 0)
                    print(ln_chapters, opr)
                    for every in range(opr):
                        error = False
                        if every != opr-1:
                            end = (every+1)*ev
                        else:
                            end = ln_chapters

                        while True:
                            try:
                                asyncio.run(get_chapters_main(
                                    index, index_col, start=every*ev, end=end))
                            except Exception as e:
                                print('Error :', e)
                                error = True
                                time.sleep(3)
                                continue

                            if error:
                                print('The Problem is Solved')

                            break

                        if every != opr-1:
                            print('End of', (every+1)*ev, 'Chapters')
                        else:
                            print('End Col Of ', title,
                                  f'That Has {ln_chapters} Chapter')

                    index_col += 1

        else:
            if headers["User-Agent"] == "Mozilla/5.0 (X11; Windows x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36":
                headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"
            else:
                headers["User-Agent"] = "Mozilla/5.0 (X11; Windows x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"

        index += 1

    r = requests.get(f'{url}add_chapters/', json=new_data)
    print(r.status_code)


class Command(BaseCommand):
    help = 'Delete objects older than 10 days'

    def handle(self, *args, **options):
        while True:
            main()
            new_data = []
            alrd = {}
            time.sleep(60*10)

        self.stdout.write('Get All Data Of Novel')
