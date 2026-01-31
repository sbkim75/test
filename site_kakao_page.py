import traceback, urllib.parse, requests, re
from tool import d,  get_logger
from urllib.parse import quote


logger = get_logger()

INCLUDE_TITLE_START = ['완결 세트','특별 세트']
EXCLUDE_TITLE_IN = ['(19세)','(연재중)','[연재]','[단행]']

class SiteKakaoPage():

    headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    }
    session = requests.Session()
    @classmethod
    def init_session(cls):
        """
        비로그인 상태에서도 필요한 세션 쿠키를 자동으로 받아오는 함수
        """
        start_url = "https://page.kakao.com/"
        res = cls.session.get(start_url, headers=cls.headers)
        if res.status_code == 200:
            logger.info("세션 초기화 완료 (쿠키 획득)")
        else:
            logger.warning(f"세션 초기화 실패: {res.status_code}")
            
            
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
    def info(cls, code, select_item):
        encoded_string = urllib.parse.quote(select_item['title'])
        cls.headers['Referer'] = f"https://page.kakao.com/search/result?keyword={encoded_string}"
        try:
            if not cls.session.cookies:
                cls.init_session()
                
            url = f"https://bff-page.kakao.com/graphql"
            data = {
            "query": "\n    query contentHomeInfo($seriesId: Long!) {\n  contentHomeInfo(seriesId: $seriesId) {\n    about {\n      id\n      themeKeywordList {\n        uid\n        title\n        scheme\n      }\n      description\n      screenshotList\n      authorList {\n        id\n        name\n        role\n        roleDisplayName\n      }\n      detail {\n        id\n        publisherName\n        retailPrice\n        ageGrade\n        category\n        rank\n      }\n      guideTitle\n      characterList {\n        thumbnail\n        name\n        description\n      }\n      detailInfoList {\n        title\n        info\n      }\n    }\n    recommend {\n      id\n      seriesId\n      list {\n        ...ContentRecommendGroup\n      }\n    }\n  }\n}\n    \n    fragment ContentRecommendGroup on ContentRecommendGroup {\n  id\n  impLabel\n  type\n  title\n  description\n  items {\n    id\n    type\n    ...PosterViewItem\n  }\n}\n    \n\n    fragment PosterViewItem on PosterViewItem {\n  id\n  type\n  showPlayerIcon\n  scheme\n  title\n  altText\n  thumbnail\n  badgeList\n  ageGradeBadge\n  statusBadge\n  subtitleList\n  rank\n  rankVariation\n  ageGrade\n  selfCensorship\n  eventLog {\n    ...EventLogFragment\n  }\n  seriesId\n}\n    \n\n    fragment EventLogFragment on EventLog {\n  fromGraphql\n  click {\n    layer1\n    layer2\n    setnum\n    ordnum\n    copy\n    imp_id\n    imp_provider\n  }\n  eventMeta {\n    id\n    name\n    subcategory\n    category\n    series\n    provider\n    series_id\n    type\n  }\n  viewimp_contents {\n    type\n    name\n    id\n    imp_area_ordnum\n    imp_id\n    imp_provider\n    imp_type\n    layer1\n    layer2\n  }\n  customProps {\n    landing_path\n    view_type\n    helix_id\n    helix_yn\n    helix_seed\n    content_cnt\n    event_series_id\n    event_ticket_type\n    play_url\n    banner_uid\n  }\n}\n    ",
            "variables": {
                "seriesId": code
            }
            }
            res = cls.session.post(url, json=data, headers=cls.headers).json()
            ret = {}
            ret['code'] = 'BKP'+code
            ret['title'] = select_item['title']
            ret['description'] = res['data']['contentHomeInfo']['about']['description']
            ret['poster_url'] = select_item['thumbnail']
            ret['author'] = res['data']['contentHomeInfo']['about']['authorList'][0]['name']
            ret['publisher'] = res['data']['contentHomeInfo']['about']['detail']['publisherName']
            ret['Publication Status'] = '0' if '연재중' in select_item['overall'] else '2'
            ret['tag'] = ['카카오페이지']
            ret['genre'] = [
                {'현판소설': '현대 판타지', '로판소설': '서양풍 로판', '판타지소설': '퓨전 판타지', '무협소설': '신무협', '로맨스소설': '로맨스'}.get(genre, genre)
                for genre in res['data']['contentHomeInfo']['about']['detail']['category'].split(' | ') 
                if genre != '웹소설'
            ]
            ret['genre'] = ','.join(ret['genre'])
            ret['Release Date'] = (
                '20' + select_item['premiered'] if len(select_item['premiered']) == 6 else select_item['premiered']
            )
            
            #ret['genre'] = res['data']['contentHomeInfo']['about']['detail']['category'].split(' | ')
            ret['Release Date'] = '20' + select_item['premiered'] if len(select_item['premiered']) == 6 else select_item['premiered']
            ret['Year'] = ret['Release Date'][:4]
            ret['Month'] = ret['Release Date'][4:6]
            ret['Day'] = ret['Release Date'][6:]
            ret['link'] = "https://page.kakao.com/content/"+code
            themeKeywordList = res['data']['contentHomeInfo']['about']['themeKeywordList']
            tags = ''
            for theme in themeKeywordList:
                title = theme['title']
                if title not in tags:  # 중복 태그 방지
                    tags += ','+title
            tags = tags[1:]
                    
            ret['tag'] = tags
            return ret
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())
       
    @classmethod
    def search(cls, title, is_comic=False,is_ebook=False):

        try:
            if not cls.session.cookies:
                cls.init_session()

            url = f'https://page.kakao.com/search/result?keyword={quote(title)}'
            logger.warning(url)
            cls.headers['Referer'] = url
            title = cls.organize_name(title)
            variables = {"input": title}
            
            data = {
                  "query": "\n    query SearchKeyword($input: SearchKeywordInput!) {\n  searchKeyword(searchKeywordInput: $input) {\n    id\n    list {\n      ...NormalListViewItem\n    }\n    total\n    isEnd\n    keyword\n    sortOptionList {\n      ...SortOption\n    }\n    selectedSortOption {\n      ...SortOption\n    }\n    categoryOptionList {\n      ...SortOption\n    }\n    selectedCategoryOption {\n      ...SortOption\n    }\n    showOnlyComplete\n    page\n  }\n}\n    \n    fragment NormalListViewItem on NormalListViewItem {\n  id\n  type\n  altText\n  ticketUid\n  thumbnail\n  badgeList\n  ageGradeBadge\n  statusBadge\n  ageGrade\n  isAlaramOn\n  row1\n  row2\n  row3 {\n    id\n    metaList\n  }\n  row4\n  row5\n  scheme\n  continueScheme\n  nextProductScheme\n  continueData {\n    ...ContinueInfoFragment\n  }\n  seriesId\n  isCheckMode\n  isChecked\n  isReceived\n  isHelixGift\n  showPlayerIcon\n  rank\n  isSingle\n  singleSlideType\n  ageGrade\n  selfCensorship\n  eventLog {\n    ...EventLogFragment\n  }\n  giftEventLog {\n    ...EventLogFragment\n  }\n}\n    \n\n    fragment ContinueInfoFragment on ContinueInfo {\n  title\n  isFree\n  productId\n  lastReadProductId\n  scheme\n  continueProductType\n  hasNewSingle\n  hasUnreadSingle\n}\n    \n\n    fragment EventLogFragment on EventLog {\n  fromGraphql\n  click {\n    layer1\n    layer2\n    setnum\n    ordnum\n    copy\n    imp_id\n    imp_provider\n  }\n  eventMeta {\n    id\n    name\n    subcategory\n    category\n    series\n    provider\n    series_id\n    type\n  }\n  viewimp_contents {\n    type\n    name\n    id\n    imp_area_ordnum\n    imp_id\n    imp_provider\n    imp_type\n    layer1\n    layer2\n  }\n  customProps {\n    landing_path\n    view_type\n    helix_id\n    helix_yn\n    helix_seed\n    content_cnt\n    event_series_id\n    event_ticket_type\n    play_url\n    banner_uid\n  }\n}\n    \n\n    fragment SortOption on SortOption {\n  id\n  name\n  param\n}\n    ",
                  "variables": {
                    "input": {
                      "keyword": title,
                      "categoryUid": "0",
                      "showOnlyComplete": False,
                      "sortType": "Accuracy"
                    }
                  }
                }
            res = cls.session.post('https://bff-page.kakao.com/graphql', json=data, headers=cls.headers)
            # print(res.text)
            ret = {}
            ret['data'] = []
            result_list = []
            if res.status_code == 200:
                for data in res.json()['data']['searchKeyword']['list']:
                    if is_comic:
                        if '웹툰' not in data['altText']:
                            continue
                        if '단행본' in data['altText']:
                            if not is_ebook:
                                continue
                    else:
                        if '웹툰' in data['altText']:
                            continue
                            
                    if is_ebook:
                        if '단행본' not in data['altText']:
                            continue
                        if not is_comic:
                            if '웹툰' in data['altText']:
                                continue
                    else:
                        if '단행본' in data['altText']:
                            continue

                    entity = {}
                    entity['code'] = re.search('\d+',data['id']).group()
                    print(entity['code'])
                    entity['title'] = re.search('작품,([^,]+)',data['altText']).group().replace('작품,','').strip()
                    entity['premiered'] = re.search('\d{2}\.\d{2}\.\d{2}', data['altText']).group().replace('.','').strip()
                    entity['author'] = re.search('작가\s([^,]+)',data['altText']).group().replace('작가 ','').strip()
                    entity['thumbnail']= 'https:' + data['thumbnail'].replace("dn-img-page.kakao","page-images.kakaoentcdn").replace("filename=th3","filename=o1")
                    entity['overall'] = data['altText']
                    result_list.append(entity)
            else:
                ret['ret'] = 'empty'
                return
                
            if result_list:
                ret['ret'] = 'success'
                for i, result in enumerate(result_list):
                    info = cls.info(result['code'],result)
                    ret['data'].append(info)
                    
                    # sorted_data = sorted(ret['data'].items(), key=lambda x: x[1]['score'], reverse=True)   
                    # ret['data'] = {k: v for k, v in sorted_data}
            else:
                ret['ret'] = 'empty'
            return ret
                
        except Exception as exception:
            logger.error('Exception:%s', exception)
            logger.error(traceback.format_exc())


if __name__ == '__main__':
    data = SiteKakaoPage.search('나 혼자만 레벨업',True,True)
    logger.debug(d(data))
    # data = SiteKakaoPage.info(data['data'][0]['code'],data['data'][0])
    # logger.debug(d(data))