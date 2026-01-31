import json
import traceback
import urllib.parse
import urllib.request
from random import randint
import re
import requests
import xmltodict
from lxml import etree, html
from tool import d, get_logger, pt

logger = get_logger()


class SiteNaver(object):
    site_name = 'naver'
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language' : 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    apikey = None



class SiteNaverBook(SiteNaver):
    @classmethod
    def search_api(cls, title, auth, cont, isbn, publ):
        logger.debug(f"책 검색 : [{title}] [{auth}] ")
        
        tmp = cls.apikey[randint(0, len(cls.apikey)-1)]
        client_id, client_secret = tmp.split(',')
        try:
            if client_id == '' or client_id is None or client_secret == '' or client_secret is None: 
                return
            # url = "https://openapi.naver.com/v1/search/book.json?query=%s&display=100" % py_urllib.quote(str(keyword))
            url = f"https://openapi.naver.com/v1/search/book_adv.xml?display=100"
            if title != '':
                url += f"&d_titl={urllib.parse.quote(str(title))}"
            if auth != '':
                url += f"&d_auth={urllib.parse.quote(str(auth))}"
            if cont != '':
                url += f"&d_cont={urllib.parse.quote(str(cont))}"
            if isbn != '':
                url += f"&d_isbn={urllib.parse.quote(str(isbn))}"
            if publ != '':
                url += f"&d_publ={urllib.parse.quote(str(publ))}"
            print(url)
            requesturl = urllib.request.Request(url)
            requesturl.add_header("X-Naver-Client-Id", client_id)
            requesturl.add_header("X-Naver-Client-Secret", client_secret)
            #response = py_urllib2.urlopen(requesturl, data = data.encode("utf-8"))
            response = urllib.request.urlopen(requesturl)
            data = response.read()
            data = json.loads(json.dumps(xmltodict.parse(data)))
            #logger.warning(data)
            rescode = response.getcode()
            if rescode == 200:
                return data
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())

    @classmethod
    def search(cls, title, auth, cont, isbn, publ):
        data = cls.search_api(title, auth, cont, isbn, publ)
        # logger.warning(d(data))
        result_list = []
        ret = {}

        if data['rss']['channel']['total'] != '0':
            tmp = data['rss']['channel']['item'] 
            if type(tmp) == type({}):
                tmp = [tmp]
            for idx, item in enumerate(tmp):
                #logger.debug(d(item))
                
                entity = {}
                entity['code'] = 'BN' + item['link'].rsplit('/', 1)[1]
                entity['title'] = item['title'].replace('<b>', '').replace('</b>', '')
                entity['image'] = item['image']
                try:
                    entity['author'] = item['author'].replace('<b>', '').replace('</b>', '')
                except:
                    entity['author'] = ''
                entity['publisher'] = item['publisher']
                entity['description'] = ''
                try:
                    if item['description'] is not None:
                        entity['description'] = item['description'].replace('<b>', '').replace('</b>', '')
                except:
                    pass
                entity['pubdata'] = item['pubdate']
                entity['link'] = item['link']
                entity['isbn'] = item['isbn']
                
                #logger.warning(idx)
                if cls.compare_title(title) == cls.compare_title(entity['title']) or cls.compare_title(title + " 1") == cls.compare_title(entity['title']):
                    entity['score'] = 100
                elif title in entity['title'] and auth in entity['author']:
                    if entity['image'] != None:
                        entity['score'] = 95 - idx
                    else:
                        entity['score'] = 90 - idx
                elif title in entity['title']:
                    entity['score'] = 95 - idx*5
                else:
                    entity['score'] = 90 - idx*5
                if entity['description'] == '':
                    entity['score'] += -10
                #logger.error(entity['score'])
                result_list.append(entity)
        else:
            logger.warning("검색 실패")
            
        if result_list:
            ret['ret'] = 'success'
            result_list = sorted(result_list, key=lambda k: k['score'], reverse=True) 
            ret['data'] = result_list
        else:
            ret['ret'] = 'empty'

        return ret

    @classmethod
    def compare_title(cls, title):
        title =  re.sub(r'\(.*?\)', '', title).strip()
        return title.replace(' ', '')
    
    @classmethod
    def change_for_plex(cls, text):
        return text.replace('<p>', '').replace('</p>', '').replace('<br/>', '\n').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&apos;', '‘').replace('&quot;', '"').replace('&#13;', '').replace('<b>', '').replace('</b>', '')


    @classmethod 
    def get_tree(cls, url, proxy_url=None, headers=None, post_data=None, cookies=None, verify=None):
        text = cls.get_text(url, proxy_url=proxy_url, headers=headers, post_data=post_data, cookies=cookies, verify=verify)
        #logger.debug(text)
        if text is None:
            return
        return html.fromstring(text)
    
    @classmethod 
    def get_text(cls, url, proxy_url=None, headers=None, post_data=None, cookies=None, verify=None):
        res = cls.get_response(url, proxy_url=proxy_url, headers=headers, post_data=post_data, cookies=cookies, verify=verify)
        #logger.debug('url: %s, %s', res.status_code, url)
        #if res.status_code != 200:
        #    return None
        return res.text

    @classmethod 
    def get_response(cls, url, proxy_url=None, headers=None, post_data=None, cookies=None, verify=None):
        proxies = None
        if proxy_url is not None and proxy_url != '':
            proxies = {"http"  : proxy_url, "https" : proxy_url}
        if headers is None:
            headers = cls.default_headers

        if post_data is None:
            if verify == None:
                res = requests.get(url, headers=headers, proxies=proxies, cookies=cookies)
            else:
                res = requests.get(url, headers=headers, proxies=proxies, cookies=cookies, verify=verify)
        else:
            if verify == None:
                res = requests.post(url, headers=headers, proxies=proxies, data=post_data, cookies=cookies)
            else:
                res = requests.post(url, headers=headers, proxies=proxies, data=post_data, cookies=cookies, verify=verify)
        
        #logger.debug(res.headers)
        #logger.debug(res.text)
        return res

    @classmethod
    def info(cls, code):
        url = 'http://book.naver.com/bookdb/book_detail.php?bid=' + code[2:].rstrip('A')
        logger.warning(url)
        entity = {}
        cls.default_headers['cookie'] = 'NNB=XQGFQBOWGNBGE; m_loc=b2b2b6c4440be5abe1ea34bebe527345edec8baf44561fc56d44161a8f043863; NV_WETR_LAST_ACCESS_RGN_M="MDUxNTU3MTA="; NV_WETR_LOCATION_RGN_M="MDUxNTU3MTA="; _fbp=fb.1.1648692556239.1218201641; nx_ssl=2; _ga=GA1.2.1577883733.1648692557; _ga_4BKHBFKFK0=GS1.1.1651853567.8.0.1651853567.60; page_uid=ho62Odprvh8ssh+ptj4ssssstho-337997; BMR=s=1652834815703&r=https%3A%2F%2Fm.blog.naver.com%2Fteammac%2F221390625108&r2=https%3A%2F%2Fwww.google.com%2F; nid_inf=1706584944; NID_AUT=dYuokF0TKz1sOs+wpFUF2UuBMzXkNgzBGMYDtFZojCZfxLEdPEkH9COuGSo7X/Og; NID_JKL=86rhD5mHv39TeK3g7okWSjjzCJV9zCtIYeT1upMggmE=; NID_SES=AAABdewNrP13SKNYH9cQQYf4rXRkYhwkVYIA8LcQQhszQd4YkJxKRe0Mgkq+JyK6JrcPqruIlTo9duyRZl1s8iKa+R/KRFGwQF1CHDlweCflUMEIllTDG9oQb0+68xTPvWFyErsUHycjINwa6cez2HWMVQyUf5cljUwM8RUkZnTodSAyK+QT6n6QkZB8sCeFjIziudqiPmIudpjgoZqpgGwHrs5kPfp1NaSUh5MO9baKe3E2g6/LkJn1rBR4mAy4rYnpmmmuo5UWZHzEaJBfUUtyEOAqG/FdywaPs4M3OC8KVWj7+LoyPLQCKSyUo2BsDGLWbWnt51VVc/VuBG993OF9SsluLt3tpkT9Hqw1vnvRs69S76+9c758rQl8sFpD62engnkTbwaduyWmh99yI18ylvz9/wXSAtdspOauHmgBu/cEQebqwwJAeuEkdYoTjc/JiOkXVnSzGhOkM7dHj285Fud9q/sAv6a2QKAvTLRXC69IgkiGefyuckbCwlQ8Wjf0yA==; JSESSIONID=DE09CFAA46079601DF2A712DF50809E8'
        #text = requests.get(url, headers=cls.default_headers).text

        #logger.debug(d(text))
        
        root = cls.get_tree(url, headers=cls.default_headers)
        entity['code'] = code
        entity['title'] = cls.change_for_plex(root.xpath('//div[@class="book_info"]/h2/a/text()')[0].strip())
        entity['poster'] = root.xpath('//div[@class="book_info"]/div[1]/div/a/img')[0].attrib['src'].split('?')[0]
        entity['ratings'] = root.xpath('//*[@id="txt_desc_point"]/strong[1]/text()')[0]
        tmp = root.xpath('//div[@class="book_info"]/div[2]/div[2]')[0].text_content().strip()
        tmps = tmp.split('|')
        #logger.warning(tmps)
        #if len(tmps) == 3:
        #entity['author'] = tmps[0].replace('저자', '').strip()
        try:
            entity['author'] = tmps[0].replace('저자', '').replace('글', '').strip()
            entity['publisher'] = tmps[-2].strip()
            entity['premiered'] = tmps[-1].replace('.', '')
        except:
            pass

        try:
            tmp = etree.tostring(root.xpath('//*[@id="bookIntroContent"]/p')[0], pretty_print=True, encoding='utf8').decode('utf8')
            entity['desc'] = cls.change_for_plex(tmp)
        except:
            entity['desc'] = ''

        try:
            tmp = etree.tostring(root.xpath('//*[@id="authorIntroContent"]/p')[0], pretty_print=True, encoding='utf8').decode('utf8')
            entity['author_intro'] = cls.change_for_plex(tmp)
        except:
            entity['author_intro'] = ''
        
        return entity



if __name__ == '__main__':
    SiteNaverBook.apikey = ['pmsxLjHJOcOotg68XpS4,O55FrEBUCD']
    data = SiteNaverBook.search("인간력 [다사카 히로시]",'','','','')
    logger.debug(d(data))