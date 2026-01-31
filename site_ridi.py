import os
import re
import traceback
import unicodedata
import urllib.parse
import urllib.request
import json
from random import randint

import urllib.request as py_urllib2
import urllib.parse as py_urllib #urlencode

import requests
from bs4 import BeautifulSoup
import xmltodict
from lxml import etree, html
from numpy import sort

from tool import d, default_headers, get_logger, pt, get_epub_info

logger = get_logger()

INCLUDE_TITLE_START = ['완결 세트','특별 세트']
EXCLUDE_TITLE_IN = ['(19세)','(연재중)']

class SiteRidi:
    default_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
    "Referer": "https://select.ridibooks.com/",}
    
    
    @classmethod
    def merge_json(cls,json1, json2):
        for key in json2:
            if key in json1:
                if isinstance(json1[key], dict) and isinstance(json2[key], dict):
                    cls.merge_json(json1[key], json2[key])
                elif isinstance(json1[key], list) and isinstance(json2[key], list):
                    # 두 리스트를 병합 (중복을 허용할 경우)
                    json1[key].extend(json2[key])

                    # 중복을 제거하려면 아래와 같이 추가 처리 가능
                    # json1[key] = list({frozenset(item.items()):item for item in json1[key]}.values())
                else:
                    json1[key] = json2[key]
            else:
                json1[key] = json2[key]
        return json1
    @classmethod
    def change_htmltext(cls, text):
        return text.replace('<p>', '').replace('</p>', '').replace('<br/>', '\n').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&apos;', '‘').replace('&quot;', '"').replace('&#13;', '').replace('<b>', '').replace('</b>', '')
    
    @classmethod
    def search_api(cls, title , is_comic=False , select_search=False):
        logger.debug(f"책 검색 : [{title}]  ")
        start = "0"
        if select_search == False:
            # RIDIBOOKS
            url = f"https://search-api.ridibooks.com/apps/search/search?adult_exclude=n&keyword={urllib.parse.quote_plus(title)}&what=base&where=book&site=ridi-store&start={start}"
        else:
            # RIDISELECT
            url = f"https://search-api.ridibooks.com/search?keyword={urllib.parse.quote_plus(title)}&where=book&site=ridi-select&what=base&start={start}"
        logger.warning(url)
        data = requests.get(url, headers=default_headers).json()

        # if is_comic and not select_search: 
        #     data['books'] = [book for book in data['books'] if '만화' in book['parent_category_name'] or '웹툰' in book['parent_category_name']]
        #     ret = data['books']
        # else:
        if select_search:
            books_count = data['total']
        else:
            books_count = data['total']
        max_page = 2
        if books_count>24:
            for i in range(24,books_count,24):
                max_page-=1
                if select_search == False:
                    # RIDIBOOKS
                    url = f"https://search-api.ridibooks.com/apps/search/search?adult_exclude=n&keyword={urllib.parse.quote_plus(title)}&what=base&where=book&site=ridi-store&start={str(i)}"
                else:
                    # RIDISELECT
                    url = f"https://search-api.ridibooks.com/search?keyword={urllib.parse.quote_plus(title)}&where=book&site=ridi-select&what=base&start={str(i)}"
                tmp = requests.get(url, headers=default_headers).json()
                data = cls.merge_json(data,tmp)
                if max_page == 0:
                    break
                
        ret = data['books']
        return ret
    
    @classmethod
    def clean_string(cls, s):
    # 개정판등 제거,[]안에 내용 제거 후 영어와한글만 남김
        # print(f"befor:{s}")
        s = s.replace("개정판 l ","")
        s = s.replace("개정판","")
        s = s.replace("()","")
        s = s.replace("개정증보판","")
        s = re.sub(r'\[.*?\]', '', s)
        s = re.sub(r"[^a-zA-Z0-9가-힣\s\+\(\)\_\']", "", s).strip().replace(" ","")
        # s = re.sub(r'\(.*?\)', '', s)
        # s = re.sub(r'[^a-zA-Z0-9가-힣]', '', s).replace(" ","")
        # s = re.sub(r'[^a-zA-Z0-9가-힣一-龥ぁ-んァ-ン]', '', s).replace(" ","")
        s = s.upper()
        # print(f"after:{s}")
        return s
    
    @classmethod
    def get_authors(cls,authors_info):
        author_name=''
        illustrator_name=''
        for author in authors_info:
            if 'author' in author['role']:
                author_name = author_name + (','+author['name'] if len(author_name)!=0 else author['name'])
            elif 'story_writer' in author['role']:
                author_name = author_name + (','+author['name'] if len(author_name)!=0 else author['name'])
                
            if 'illustrator' in author['role']:
                illustrator_name = illustrator_name + (','+author['name'] if len(illustrator_name)!=0 else author['name'])
        return [author_name,illustrator_name]
    
    @classmethod
    def select_info(cls, code):
        url = 'https://select-api.ridibooks.com/api/books/' + code
        # logger.warning(url)
        data = requests.get(url, headers=default_headers).json()
        entity = {}
        entity['code'] = code
        entity['b_id'] = code
        entity['title'] = data['title']['main']
        entity['web_title'] = data['title']['main']
        entity['author'] = ""
        entity['author2'] = ""
        entity['translator'] = ""
        entity['poster'] = data['thumbnail']['large']
        if len(data['authors'])>0:
            for author in data['authors']:
                if 'author' in author:
                    tmp = data['authors']['author']
                    for i,writer in enumerate(tmp):
                        entity[f"author{'' if i==0 else str(i+1).strip()}"] = writer['name'] if i == 0 else ',' + writer['name']
                if 'translator' in author :
                    tmp = data['authors']['translator']
                    for i,translator in enumerate(tmp):
                        entity['translator'] = translator['name'] if i == 0 else ',' + translator['name']
        entity['publisher'] = data['publisher']['name']
        p_date=""
        if data['publishing_date']['ridibooks_publish_date'] is not None:
            p_date = data['publishing_date']['ridibooks_publish_date'][:10].replace("-","")
        elif data['publishing_date']['ebook_publish_date'] is not None: 
            p_date = data['publishing_date']['ebook_publish_date'][:10].replace("-","")
        elif data['publishing_date']['paper_book_publish_date'] is not None: 
            p_date = data['publishing_date']['paper_book_publish_date'][:10].replace("-","")
        entity['Release Date'] = p_date
        # <img src=\"//misc.ridibooks.com/desc.intro/3284000039\"/>
        intro_image_url = data['intro_image_url'] if data['intro_image_url'] != None else ''
        entity['description'] =  (('<img src=\"' + intro_image_url + '\"/>\n\n') if len(intro_image_url) != 0 else "") + data['introduction']
        try:
            if len(data['categories'][1]) > 1:
                entity['parent_category_name'] = data['categories'][1][0]['name']
                entity['category_name'] = data['categories'][1][1]['name']
        except:
            try:
                entity['parent_category_name'] = data['categories'][0][0]['name']
                entity['category_name'] = data['categories'][0][1]['name']
            except:
                entity['parent_category_name'] = ""
                entity['category_name'] = ""
        return entity

    @classmethod
    def get_book_desc(cls,b_id):

        url = f"https://ridibooks.com/books/{b_id}"
        response = requests.get(url,headers=default_headers)
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        element = soup.find(attrs={"aria-label": "19세 미만 구독불가"})
        ret_adult_only = False
        if element:
            ret_adult_only = True
        
        intro_header = soup.find(['h2', 'h3'], string='작품 소개')
        intro_div = ''
        
        if intro_header:
            if intro_header.parent.name == 'button':
                intro_div = intro_header.find_parent('div').find_next_sibling('div', class_='rigrid-1sma1m6')
                img_tag = soup.find('img', class_='rigrid-dzaqf9')
                img_url = img_tag['src'] if img_tag else None
            else:
                intro_div = intro_header.find_next('div', class_='rigrid-1sma1m6')
                img_tag = soup.find('img', class_='rigrid-dzaqf9')
                img_url = img_tag['src'] if img_tag else None
        else:
            info_header = soup.find('h2', string='작품 정보')
            if info_header:
                intro_div = info_header.find_next('div', class_='rigrid-1sma1m6')
                img_tag = soup.find('img', class_='rigrid-dzaqf9')
                img_url = img_tag['src'] if img_tag else None


        if intro_div:
            innermost_div = intro_div.find('div', recursive=True)
            if innermost_div:
                intro_text = innermost_div.get_text()
                img_tag = soup.find('img', class_='rigrid-dzaqf9')
                img_url = img_tag['src'] if img_tag else None
                introduction_text = cls.change_htmltext(intro_text)
        else:
            introduction_text = ''
            img_url = ''                    
            
        desc = []
        if introduction_text:
            introduction_text = ('<img src=\"'+img_url+ '\"/> \n\n' if img_url is not None else '') + introduction_text
            #<img src=\"//misc.ridibooks.com/desc.intro/856000307\"/>
            desc.append(introduction_text)
        else:
            desc.append('')

        date = soup.find('li', class_='rigrid-jekr1u')
        if date:
            p_date = date.get_text().strip()[:10].replace('.','')
        else:
            p_date = ""
        is_status = soup.find('div', class_='rigrid-snzzqn')
        if is_status:        
            p_status = soup.find('svg', class_='rigrid-h8fpe0')
            if p_status:
                desc.append('2')
            else:
                desc.append('0')
        else:
            desc.append('2')
        poster_url = f"https://img.ridicdn.net/cover/{b_id}/xxlarge"
        return desc,p_date,poster_url,ret_adult_only




    @classmethod
    def remove_sub(cls, title):
        if '개정판' in title or '개정증보판' in title:
            title = title.replace('개정판','').replace('개정증보판','').replace('：','').replace('|','').replace('｜','').replace('()','').replace('l','') + '(개정판)'
            title = title.strip()
        print(title)
        return title
    
    @classmethod
    def organize_name(cls,title):

        for exclude_in in EXCLUDE_TITLE_IN:
            if exclude_in in EXCLUDE_TITLE_IN:
                title = title.replace(exclude_in,'')

        included_titles_pattern = '|'.join(map(re.escape, INCLUDE_TITLE_START))
        pattern = rf'^\[[^\]]+\]\s*(?:\[(?:{included_titles_pattern}|[^\]]+)\]\s*)*'

        match = re.match(pattern, title)
        
        if match:

            included_titles_pattern = '|'.join([fr'\[{re.escape(title)}\]' for title in INCLUDE_TITLE_START])
            special_sets = re.findall(rf'({included_titles_pattern})', match.group())
            
            # 매치된 부분을 제거
            processed_title = re.sub(pattern, '', title)
            
            # 찾은 특별 세트를 다시 앞에 추가 (대괄호 유지)
            if special_sets:
                processed_title = ' '.join(special_sets) + ' ' + processed_title
        else:
            processed_title = title
            
        return processed_title

        
    @classmethod
    def search(cls, name , is_comic=False, is_ebook = False , select_search = False , recursion_depth=0):
        # print(name)
        name = cls.organize_name(name)
        # print(name)
        # name = name.replace("-_","").replace("_","")
        title = name
        pattern = r"^(.*)\s*\[(.*?)\]$"
        match = re.match(pattern, name)
        author = ""
        if match:
            # 전체 제목 부분: 마지막 대괄호 앞까지
            title = match.group(1).strip()
            
            # 마지막 대괄호 안의 저자 정보
            author = match.group(2).strip()

        match = re.search(r'.+\((\d+)\)$', title)
        if match:
            title = re.sub(r'\(\d+\)$', '', title)
        title = title.strip()
        

        logger.debug(f"{title} - {author}")
        
        # title = re.sub(r'[^\w\s]', '', title)
        data = cls.search_api(title,is_comic,select_search)
        #logger.warning(d(data))
        ret = {}

        if len(data) == 0:
            data = cls.search_api(re.sub(r"\(.*?\)", "", title).strip(),is_comic,select_search)
            if len(data) == 0:
                temp = title + " 1"
                data = cls.search_api(temp,is_comic,select_search)

        result_list = []
        if data:
            for idx, item in enumerate(data):
                entity = {}
                if select_search == True:
                    item = cls.select_info(item['b_id'])
                
                category = item['parent_category_name'] if item['parent_category_name'] is not None else item['category_name']
                if not is_comic:
                    if '만화' in category:
                        continue
                    
                if is_ebook:
                    if 'e북' not in category:
                        continue
                elif is_ebook == False:
                    if 'e북' in category:
                        continue
                
                entity['code'] = 'BR' + item['b_id']
                entity['title'] = cls.remove_sub(item['title'])
                if 'tags_info' in item:
                    if len(item['tags_info']) != 0:
                        excluded_tags = {'대여', 'e북' , '할인' , '기다리면', '이벤트'}
                        tags = [
                            tag['tag_name']
                            for tag in item['tags_info']
                            if 'tag_name' in tag and not any(keyword in tag['tag_name'] for keyword in excluded_tags)
                        ]

                        tag_string = ','.join(tags)
                        entity['tag'] = tag_string
                if 'tag' not in entity:
                    entity['tag'] = ''
                if not select_search:
                    authors = cls.get_authors(item['authors_info'])
                    entity['author'] = authors[0] if authors[0] != '' else (item['author'] + item['author2'])
                    entity['illustrator'] = authors[1]
                    entity['Person Translator'] = item['translator']
                else:
                    entity['author'] = item['author']+item['author2']
                    entity['illustrator'] = ''
                    entity['Person Translator'] = item['translator']
                    
                entity['publisher'] = item['publisher']
                desc , rdate, poster_url,only19  = cls.get_book_desc(item['b_id']) if select_search == False else (item['description'],item['Release Date'],item['poster'],False)
                if not select_search:
                    entity['description'] = desc[0]
                    entity['Publication Status'] = desc[1]
                else:
                    entity['description'] = desc
                    entity['Publication Status'] = '2'
                entity['Release Date'] = rdate
                entity['poster_url'] = poster_url
                # 2022.01.01
                # 0123456789                    
                entity['Year'] = entity['Release Date'][:4]
                entity['Month'] = entity['Release Date'][4:6]
                entity['Day'] = entity['Release Date'][6:]
                if select_search == False:
                    entity['link'] = f"https://ridibooks.com/books/{item['b_id']}"
                else:
                    entity['link'] = f"https://select.ridibooks.com/book/{item['b_id']}"

                # if is_comic != True:
                #     entity['parent_category_name'] = item['parent_category_name']
                #     entity['category_name'] = item['category_name']
                # else:
                entity['parent_category_name'] = item['parent_category_name'] if item['parent_category_name'] is not None else item['category_name']
                entity['category_name'] = item['category_name'] + ((','+item['category_name2'] if item['category_name2'] != None else '') if 'category_name2' in item else '')
                if only19:
                    if '성인' not in entity['category_name']:
                        entity['category_name'] += ",성인"
                find100 = False
                # print(item['parent_category_name'])
                if item['parent_category_name'] is not None:
                    if is_comic and ('만화' not in item['parent_category_name'] and '웹툰' not in item['parent_category_name']): 
                        continue
                entity_author = entity['author']
                if author in entity_author:
                    if cls.clean_string(entity['title']) == cls.clean_string(title):
                        print(cls.clean_string(entity['title']),'        ',cls.clean_string(title))
                        entity['score'] = 100
                    if entity.get('score') == None:
                        tmp = re.sub(r"\s\d+$", "", entity['title'])
                        if tmp ==title or tmp == title.replace('(개정판)', '').strip():
                            entity['score'] = 99
                            find100 = True
                    if entity.get('score') == None:
                        tmp = entity['title'].replace('개정판 | ', '').strip()
                        tmp = entity['title'].split('|', 1)
                        if len(tmp) == 2:
                            tmp = tmp[1].strip()
                            if tmp == title :
                                entity['score'] = 99
                                find100 = True
                            elif tmp.startswith(title):
                                entity['score'] = 99
                                find100 = True
                    if entity.get('score') == None:
                        tmp = entity['title'].replace(' : ', ' ').strip()
                        if tmp == title :
                            entity['score'] = 100
                            find100 = True
                        elif tmp.startswith(title):
                            entity['score'] = 99
                            find100 = True
                    if entity.get('score') == None:
                        tmp = entity['title'].replace(' | ', ' ').strip()
                        if tmp == title :
                            entity['score'] = 100
                            find100 = True                                
                    if entity.get('score') == None:
                        tmp = entity['title'].replace(': ', ' ').strip()
                        if tmp == title :
                            entity['score'] = 100
                            find100 = True   
                                

                    if entity.get('score') == None:
                        tmp = entity['title'].replace(' <', '').replace('>', '').replace('?', '').strip()
                        if tmp == title:
                            entity['score'] = 100
                            find100 = True

                    if entity.get('score') == None:
                        tmp = entity['title'].replace('[원서]', '').strip()
                        if tmp == title:
                            entity['score'] = 100
                            find100 = True
                    if entity.get('score') == None:
                        tmp = entity['title'].split(':', 1)
                        if len(tmp) == 2 and tmp[0].strip() == title:
                            entity['score'] = 100
                            find100 = True

                    if entity.get('score') == None:
                        entity['score'] = 90 - (idx+1)*5

                    # if entity['score'] == 99:
                    #     if item['web_title'] != '':
                    #         entity['score'] = 100

                elif author == None:
                    if entity.get('score') == None:
                        tmp = cls.clean_string(entity['title'])
                        title = cls.clean_string(title)
                        if tmp == title:
                            entity['score'] = 100
                    if entity.get('score') == None:
                        tmp = entity['title'].split('|', 1)
                        if len(tmp) == 2:
                            tmp = tmp[1].strip()
                            if tmp == title :
                                entity['score'] = 99
                                find100 = True
                            elif tmp.startswith(title):
                                entity['score'] = 99
                                find100 = True

                if entity.get('score') == None:
                    entity['score'] = 100 - (idx+1)*2

                # if entity['score'] == 99:
                #     if item['web_title'] != '':
                #         entity['score'] = 100


                result_list.append(entity)
                if entity['score'] == 100:
                    break
        else:
            logger.warning(f"리디 검색실패:{title}")
        
            
        if result_list:
            ret['ret'] = 'success'
            result_list = sorted(result_list, key=lambda k: k['score'], reverse=True) 
            min1 = min(30, len(result_list))
            ret['data'] = result_list[:min1]
            if ret['data'][0]['score'] < 99 and recursion_depth == 0:
                return cls.search(name, is_comic,is_ebook, True, recursion_depth + 1)
        else:
            if recursion_depth == 0:
                return cls.search(name, is_comic,is_ebook, True, recursion_depth + 1)

            ret['ret'] = 'empty'

        return ret


    @classmethod
    def folder_move(cls, config):
        import os
        import re
        import shutil
        import time
        for idx, foldername in enumerate(list(sort(os.listdir(config['SRC'])))):
            foldername = unicodedata.normalize('NFC', foldername)
            src_path = os.path.join(os.path.join(config['SRC'], foldername))
            src_path = unicodedata.normalize('NFC', src_path)
            
            """
            search = re.sub(r"\[.*?\]", "", foldername).strip()
            
            api = cls.search_api(search)
            if len(api)==0:
                search = re.sub(r"\(.*?\)", "", search).strip()
                api = cls.search_api(search)
                if len(api) == 0:
                    continue
            """
            try:
                logger.debug(f"폴더: {foldername}")
                search_data = SiteRidi.search(os.path.basename(src_path))

                if search_data['ret'] == 'success':
                        
                    data = search_data['data'][0]
                    if data['score'] > 98:
                        
                        target_folder = config['TAR']
                        if data['parent_category_name'] != None:
                            target = os.path.join(target_folder, data['parent_category_name'].replace('/', '.'), data['category_name'].replace('/', '.'))
                        else:
                            target = os.path.join(target_folder, data['category_name'].replace('/', '.'))

                        logger.info(f"{target}/{foldername}")

                        if os.path.exists(target) == False:
                            os.makedirs(target)
                        if os.path.exists(target) and os.path.exists(os.path.join(target, foldername)) == False:
                            logger.debug("이동")
                            shutil.move(src_path, target)
                            logger.debug("이동22")
                            import time
                            time.sleep(1)
                        else:
                            logger.error(f"이미 있음 {foldername}")
                            shutil.move(src_path, config['EXIST'])
                        time.sleep(1)
                        #return
                else:
                    logger.info("검색실패")
            except Exception as e: 
                    logger.error(f"Exception:{str(e)}")
                    logger.error(traceback.format_exc())



if __name__ == '__main__':
    data = SiteRidi.search("운동하는 아이가 행복하다",False,False) # 제목,IS_COMIC,IS_EBOOK
    logger.debug(d(data))
    