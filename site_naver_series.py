import traceback, requests
from datetime import datetime
from tool import d, default_headers, get_logger, pt
from urllib.parse import quote
import lxml.html
import re
from difflib import SequenceMatcher
import unicodedata

logger = get_logger()

"""
네이버시리즈     리디북스 
로맨스           로맨스
로판             서양풍 로판
판타지           퓨전 판타지
현판             현대 판타지
무협             신무협
"""
INCLUDE_TITLE_START = ['완결 세트','특별 세트']
EXCLUDE_TITLE_IN = ['(19세)','(연재중)','[연재]','[단행]']

class SiteNaverSeries():
    
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
    def similarity(cls, str1, str2):
        ratio = SequenceMatcher(None, str1, str2).ratio()
        return int(ratio * 100)

    @classmethod
    def info(cls, code):
        try:
            url = f"https://series.naver.com{code}"
            text = requests.get(url, headers=default_headers).text
            root = lxml.html.fromstring(text)

            entity = {}
            entity['code'] = "BNS"+(re.search(r'productNo=(\d+)', code) or [None]).group(1)

            tmp = root.xpath('//meta[@property="og:title"]')[0].attrib['content']
            entity['title'] = re.sub("\[.*?\]", '', tmp).strip()
            
            # ret['desc'] = root.xpath('//meta[@property="og:description"]')[0].attrib['content']
            synopsis_elements  =  root.xpath('//div[contains(@class, "_synopsis")]')
            text_content = ""
            for i, element in enumerate(synopsis_elements):
                element_text = element.text_content().replace("\xa0", " ").replace("\n", "").replace("<br>", "\n")
                
                # 첫 번째 요소에서 "더보기"가 포함된 경우 제외
                if i == 0 and "더보기" in element_text:
                    continue
                
                text_content += element_text
            entity['description'] = text_content.replace("더보기","").replace("접기","").replace("\t","")

            
            try:
                entity['poster_url'] = root.xpath('//*[@id="container"]/div[1]/a/img')[0].attrib['src'].split('?')[0]
            except:
                entity['poster_url'] = root.xpath('//*[@id="container"]/div[1]/span/img')[0].attrib['src'].split('?')[0]
                
            genre_mapping = {
                "로맨스": "로맨스",
                "로판": "서양풍 로판",
                "판타지": "퓨전 판타지",
                "현판": "현대 판타지",
                "무협": "신무협"
                }
            entity['genre'] =  genre_mapping.get(root.xpath('//*[@id="content"]/ul[1]/li/ul/li[2]/span/a')[0].text_content(),root.xpath('//*[@id="content"]/ul[1]/li/ul/li[2]/span/a')[0].text_content())
            # ret['genre'] =  root.xpath('//*[@id="content"]/ul[1]/li/ul/li[2]/span/a')[0].text_content()
            entity['Publication Status'] = 0 if "완결" not in root.xpath('//*[@id="content"]/ul[1]/li/ul/li[1]/span/text()')[0] else 2
            # ret['author'] = root.xpath('//*[@id="content"]/ul[1]/li/ul/li[3]/a')[0].text_content()
            entity['author'] = root.xpath("string(//span[contains(text(), '글')]/following-sibling::a[1])")
            entity['publisher'] = root.xpath("string(//span[contains(text(), '출판사')]/following-sibling::a[1])")
            if '/comic/' in code:
                entity['illustrator'] = root.xpath("string(//span[contains(text(), '그림')]/following-sibling::a[1])")
            else:
                entity['illustrator'] = ""
            entity['link'] = url

            if '/novel/' in code:
                url = 'https://series.naver.com/novel/volumeList.series?productNo=' + code.split('productNo=')[1]
            elif '/comic/' in code:
                url = 'https://series.naver.com/comic/volumeList.series?productNo=' + code.split('productNo=')[1]
            
            if 'tag' not in entity:
                entity['tag'] = ""
            # 평점 추출 및 평점에 따른 태그 추가
            try:
                rating_element = root.xpath('//*[@id="content"]/div[1]/div[1]/em')[0]
                rating = float(rating_element.text)
                if rating >= 9:
                    entity['tag']+=',평점9점이상'
                elif rating >= 8:
                    entity['tag']+=',평점8점이상'
            except Exception as e:
                logger.error(f"Rating extraction failed: {e}")

            # XPath 경로가 존재하는지 확인
            try:
                link_element = root.xpath('//*[@id="content"]/div[1]/div[2]/ul/li[5]/a')
                if link_element:
                    span_text = root.xpath('//*[@id="content"]/div[1]/div[2]/ul/li[5]/a/span')[0].text
                    if span_text == '연재본 보기':
                        entity['tag']+=',e북'
                    elif span_text == '단행본 보기':
                        entity['tag']+=',웹소설'
                else:
                    entity['tag']+=',웹소설'  # 해당 경로가 존재하지 않을 경우 '웹소설' 추가
            except Exception as e:
                entity['tag']+=',웹소설'  # 경로가 없거나 오류 발생 시 '웹소설' 추가
                
            entity['tag'] = entity['tag'][1:]









            data = requests.get(url, headers=default_headers).json()
            entity['Release Date'] = data['resultData'][0]['lastVolumeUpdateDate'].split(' ')[0].replace('-', '')
            entity['Year'] = entity['Release Date'][:4]
            entity['Month'] = entity['Release Date'][4:6]
            entity['Day'] = entity['Release Date'][6:]

            entity['score'] = 0
            return entity
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
       



    @classmethod
    def search(cls, title, is_comic=False,is_ebook=False):
        title = cls.organize_name(title)
        if is_comic:
            url = f"https://series.naver.com/search/search.series?t=comic&fs=default&q={quote(title)}"
        else:
            url = f"https://series.naver.com/search/search.series?t=novel&fs=default&q={quote(title)}"
        logger.warning(url)
        text = requests.get(url, headers=default_headers).text
        root = lxml.html.fromstring(text)

        tags = root.xpath('//ul[@class="lst_list"]/li')
        # logger.error(tags)
        ret = {}
        ret['data'] = []
        result_list = []
        for tag in tags:
            entity = {}
            is_adult = tag.xpath('.//em[@class="ico n19" and text()="19금"]')
            if is_adult:
                continue
            entity['code'] = tag.xpath('.//a')[0].attrib['href']
            tmp = None
            # logger.debug(d(entity))
            if '/novel/' in entity['code']:
                tmp = 'nov'
            elif '/comic/' in entity['code']:
                tmp = 'com'
            if tmp != None:
                
                entity['title'] = tag.xpath('.//a[@class="N=a:%s.title"]' % tmp)[0].text_content().replace('\n', '').replace('\t', '')
                # logger.debug(d(entity))
                entity['author'] = tag.xpath('.//span[@class="author"]')[0].text_content().replace('\n', '').replace('\t', '')
                    
                if is_ebook:
                    if '단행본' in entity['title']:
                        result_list.append(entity)
                    else:
                        continue
                else:
                    result_list.append(entity)
        
        if result_list:
            ret['ret'] = 'success'
            for i, result in enumerate(result_list):
                info = cls.info(result['code'])
                info['score'] = cls.similarity(title, info['title'])
                cleaned_info = {key: str(value) for key, value in info.items()}
                ret['data'].append(cleaned_info)
                
                # sorted_data = sorted(ret['data'].items(), key=lambda x: x[1]['score'], reverse=True)   
                # ret['data'] = {k: v for k, v in sorted_data}
        else:
            ret['ret'] = 'empty'
        return ret

if __name__ == '__main__':
    data = SiteNaverSeries.search('기사를 선택하는 법',False)
    logger.debug(d(data))
    # data = SiteNaverSeries.info(data[0]['code'])
    # logger.debug(d(data))



