import base64
import json
import os
import re
import shutil
import traceback
import unicodedata
import urllib
import urllib.parse
import zipfile
from io import BytesIO

import xmltodict
import yaml
from lxml import etree
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image

from site_naver_book import SiteNaverBook
from site_ridi import SiteRidi
from site_naver_series import SiteNaverSeries
from site_kakao_page import SiteKakaoPage
from tool import d, get_logger, pt

logger = get_logger()


class ModMakeInfo:

    def __init__(self, config) -> None:
        self.config = config
        for key, value in self.config.get('DEFAULT_META', {}).items():
            META[key] = value
        action = self.config.get('DEFAULT_ACTION')
        if action != None:
            for key, value in action.items():
                ACTION[key] = value
        self.config['META'] = META
        self.config['ACTION'] = ACTION

    def find_code_in_kavita(self,yaml_file):
        br_code_pattern = re.compile(r'code:\s*(B[RN]\d+)$')
        line_count = 0
        with open(yaml_file, 'r', encoding='utf-8') as file:
            for line in file:
                line_count += 1
                if line_count > 5:
                    return False
                match = br_code_pattern.search(line)
                if match:
                    return True
                
    def start(self):
        root = self.config['ROOT']
        logger.info(f"INFO ROOT: {root}")
        if type(root) == str:
            root = [root]
        for path in root:
            logger.info(f"ROOT: {path}")
            for dirpath, dirnames, filenames in os.walk(path):
                try:
                    dirnames.sort()
                    is_library = False
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        tmps = filename.rsplit('.', 1)
                        if len(tmps) != 2:
                            continue
                        if tmps[1].lower() not in EXTENSIONS:
                            continue
                        is_library = True
                        break
                    #logger.error(f"{dirpath} {is_library}")
                    if is_library:
                        #logger.debug(f"라이브러리: {dirpath}")
                        kavita_info_path = os.path.join(dirpath, KAVITA_INFO)
                        if self.config.get('DELETE_INFO_XML'):
                            tmp = os.path.join(dirpath, 'info.xml')
                            if os.path.exists(tmp):
                                os.remove(tmp)

                        if os.path.exists(kavita_info_path) == False and self.config.get('DELETE_COVER_JPG'):
                            tmp = os.path.join(dirpath, 'cover.jpg')
                            if os.path.exists(tmp):
                                os.remove(tmp)

                        if os.path.exists(kavita_info_path) and self.config.get('PROCESS_EXIST_KAVITA_YAML') == "REMAKE":
                            os.remove(kavita_info_path)

                        elif os.path.exists(kavita_info_path) and self.config.get('PROCESS_EXIST_KAVITA_YAML') == "UPDATE":
                            self.update_info(dirpath,kavita_info_path)
                            continue
                        
                        elif os.path.exists(kavita_info_path) and self.config.get('PROCESS_EXIST_KAVITA_YAML') == "PASS":
                            # logger.debug(f"PROCESS_EXIST_KAVITA_YAML PASS!!")
                            continue

                        self.makeinfo_folder(dirpath, kavita_info_path)
                
                except Exception as e: 
                    logger.error(f"Exception:{str(e)}")
                    logger.error(traceback.format_exc())
                
    def update_info(self,dirpath,kavita_info_path):
        info = None
        logger.info(f">> {dirpath} Updating")
        b_code=''
        if os.path.exists(kavita_info_path):
            info = None
            try:
                
                with open(kavita_info_path, encoding='utf8') as file:
                    for line in file:
                        if line.strip()[:5] == 'code:':
                            b_code = line.strip()[5:].strip()
                            break
                    # info = yaml.load(file, Loader=yaml.FullLoader)
            except Exception as e: 
                logger.error(f"Exception:{str(e)}")
                logger.error(f"로딩실패: {kavita_info_path}")
        if b_code=='' or b_code=="''":  #or b_code[:3] == 'BNS':
            if os.path.exists(kavita_info_path):
                os.remove(kavita_info_path)
            self.makeinfo_folder(dirpath,kavita_info_path)
            logger.warning(f"Code가 없어서 Info Update")
            
        # if b_code[:3] == 'BNS':
        #     os.remove(kavita_info_path)
        #     self.makeinfo_folder(dirpath,kavita_info_path)
        #     logger.warning(f"Code가 없어서 Info Update")

    
    def makeinfo_folder(self, dirpath, kavita_info_path):
        info = None
        logger.info(f">> {dirpath}")
        
        if os.path.exists(kavita_info_path):
            info = None
            try:
                with open(kavita_info_path, encoding='utf8') as file:
                    info = yaml.load(file, Loader=yaml.FullLoader)  
            except Exception as e: 
                logger.error(f"Exception:{str(e)}")
                logger.error(f"로딩실패: {kavita_info_path}")
                #logger.error(traceback.format_exc())
        
        if info == None:
            info = {"files":{}}
        if info.get('action') == None:
            info['action'] = ACTION.copy()
        if self.config.get('PROCESS_EXIST_KAVITA_YAML') == "NORMAL":
            meta = info.get('meta')
        #files = OrderedDict()
        
        first_image = False
        # epub 메타를 시리즈에 적용했는가? ... 한번만
        dirpath = unicodedata.normalize('NFC', dirpath)
        flag_apply_epub_meta = False
        for filename in list(sorted(os.listdir(dirpath))):
            if info['files'].get(filename):
                info['files'][unicodedata.normalize('NFC', filename)] = info['files'].get(filename)
            filename = unicodedata.normalize('NFC', filename)
            tmps = filename.rsplit('.', 1)
            logger.debug(f"FILE: {filename} {info['files'].get(filename, {}).get('page')} {info['files'].get(filename, {}).get('wordcount')}")
            if len(tmps) != 2:

                continue
            if info['files'].get(filename) != None and (info['files'].get(filename)['cover'] != None and info['files'].get(filename)['cover'] != ''):
                if filename.lower().endswith('.epub') == False and info['files'].get(filename)['page']!='0':
                    continue
                if (filename.lower().endswith('.epub') == True and info['files'].get(filename)['page']!='0' and info['files'].get(filename)['wordcount']!='0'):
                    continue
            if tmps[1].lower() in EXTENSIONS:
                if first_image and info['action'].get('first_cover'):
                    info['files'][filename] = {"page":1, "wordcount":0, "cover":"FIRST"}
                else:
                    info['files'][filename] = {"page":1, "wordcount":0, "cover":""}
                wordcount = 0
                pagecount = 0
                img_str = ""
                
                try:
                    filepath = os.path.join(dirpath, filename)
                    filepath = unicodedata.normalize('NFC', filepath)
                    
                    if tmps[1].lower() == 'epub':
                        pagecount, img_str, wordcount = self.process_epub(filepath)
                        # if len(meta.keys()) > 0 and flag_apply_epub_meta == False:
                        #     self.apply_epub_meta(info, meta)
                        #     flag_apply_epub_meta = True
                    elif tmps[1].lower() == 'pdf':
                        pagecount, img_str = self.process_pdf(filepath)
                    elif tmps[1].lower() == 'txt':
                        pagecount = 2
                        img_str = 'TEXT'
                    else:
                        pagecount, img_str = self.process_archive(filepath)
                    
                
                    info['files'][filename]['page'] = pagecount
                    info['files'][filename]['cover'] = img_str
                    info['files'][filename]['wordcount'] = wordcount
                    
                    if first_image == False and self.config['MAKE_COVER'] == 'LOCAL_ONLY_EPUB' and tmps[1].lower() == 'epub':
                        self.save_cover(img_str, dirpath)
                    elif tmps[1].lower() != 'txt' and first_image == False and self.config['MAKE_COVER'] == 'LOCAL':
                        self.save_cover(img_str, dirpath)
                    if info['action'].get('first_cover', False) and first_image == True:
                        info['files'][filename]['cover'] = "FIRST"
                    if tmps[1].lower() != 'txt':
                        first_image = True
                except Exception as e:
                    logger.error(f"GET PAGE 에러 : {filepath}")
                    logger.error(traceback.format_exc())
                             
                logger.info(f"{filename} PAGE:{info['files'][filename]['page']} COVER:{info['files'][filename]['cover'] != ''} WC:{info['files'][filename]['wordcount']}")

        # Meta
        #if info.get('meta') == None:
        if info['action']['code'] == '':
            self.process_meta(info, dirpath)
            if info['action']['code'] == '':
                if self.config['META_SITE'] == 'RIDIBOOKS':
                    logger.error("Ridi 검색 실패 NAVERSERIES로 검색 시도")
                    self.config['META_SITE'] = 'NAVERSERIES'
                    self.process_meta(info, dirpath)
                    self.config['META_SITE'] = 'RIDIBOOKS'
        # elif self.config.get('META_SITE') == 'RIDIBOOKS2':
        #     self.process_meta(info, dirpath)

        # 변경된 파일 데이터 지우기
        filenames = list(sorted(os.listdir(dirpath)))
        filenames = [unicodedata.normalize('NFC', x) for x in filenames]
        newfiles = {}
        for filename, value in info['files'].items():
            #filename = unicodedata.normalize('NFC', filename)
            if filename in filenames:
                newfiles[filename] = value

        logger.info(f"기존: {len(info['files'].keys())}개 / 새로운: {len(newfiles.keys())}개")
        info['files'] = newfiles
        with open(kavita_info_path, 'w', encoding='utf8') as f:
            yaml.dump(info, f, default_flow_style=False, allow_unicode=True, indent=4)


        if self.config.get('META_SITE') == 'RIDIBOOKS2':
            if info['action']['code'] != '':
                logger.info(info['meta']['Tags'])
                tar = "/gdrive/Shareddrives/[GDS]/ROOT/GDRIVE/READING/책/리디셀렉트"
                tmps = info['meta']['Tags'].split(',')
                tar = os.path.join(tar, tmps[1].replace('/', '.'), tmps[0].replace('/', '.'))
                logger.debug(f"이동: {tar}")
                os.makedirs(tar, exist_ok=True)
                shutil.move(dirpath, tar)
            else:
                tar = "/gdrive/Shareddrives/[GDS]/ROOT/GDRIVE/READING/책/리디셀렉트/NOMETA"
                if os.path.exists(os.path.join(tar, os.path.basename(dirpath))):
                    logger.info("중복")
                else:
                    logger.info("NOMETA 이동")
                    shutil.move(dirpath, tar)

            #self.process_meta(info, dirpath)

    #############################################
    # Meta
    #############################################

    # epub 메타를 시리즈 메타로
    def apply_epub_meta(self, info, meta):
        series_meta = META.copy()
        series_meta['Name'] = meta['Chapter Title']
        series_meta['Genres'] = meta['Genres']
        series_meta['Language'] = meta['Language']
        series_meta['Person Publisher'] = meta['Publisher']
        series_meta['Release Date'] = meta['Release Date']
        if series_meta['Release Date'] != "":
            series_meta['Year'] = series_meta['Release Date'][:4]
        series_meta['Summary'] = meta['Summary']
        series_meta['Person Writers'] = meta['Writer'].replace('·', ',')
        info['meta'] = series_meta


    def process_meta(self, info, dirpath):
        try:
            name = os.path.basename(dirpath)
            name = re.sub(r'\[.*?\]', "", name).strip()
            name = re.sub(r'\s-{1,2}$', "", name).strip()
            name = re.sub(r'\s~{1,2}$', "", name).strip()
            meta = META.copy()
            meta['Name'] = name

            if self.config['META_SITE'] == 'NAVER':
                self.meta_naver(info, dirpath, meta)
            elif self.config['META_SITE'] == 'RIDIBOOKS':
                self.meta_ridibooks(info, dirpath, meta)
            elif self.config['META_SITE'] == 'NAVERSERIES':
                self.meta_naverseries(info, dirpath, meta)
            elif self.config['META_SITE'] == 'KAKAOPAGE':
                self.meta_kakaopage(info, dirpath, meta)
            elif self.config['META_SITE'] == 'RIDIBOOKS2':
                self.meta_ridibooks2(info, dirpath, meta)
            elif self.config['META_SITE'] == 'XML':
                self.meta_xml(info, dirpath, meta)
            else:
                logger.error("META_SITE not Found")    
                exit(0)
        except Exception as e:
            logger.error(f"process_meta")
            logger.error(traceback.format_exc())
            info['meta'] = meta
    
    def meta_naverseries(self,info,dirpath,meta):
        name = meta['Name']
        name = os.path.basename(dirpath)
        search_data = SiteNaverSeries.search(name,(self.config.get('META_GENRE') == "COMIC"),(self.config.get('IS_EBOOK') == True))

        if search_data['ret'] == 'success':
            count = min(10, len(search_data['data']))
            info['search'] = search_data['data'][:count]
        
        if info.get('search') and len(info['search']) > 0 and info['action']['code'] == '':
            info['action']['code'] = info['search'][0]['code']
        
        for item in info.get('search', []):
            if item['code'] == info['action']['code']:
                logger.debug(d(item))
                meta['Web Links'] = item['link']
                meta['Person Writers'] = item['author']
                meta['Person Penciller'] = item['illustrator']
                meta['Person Publisher'] = item['publisher']
                meta['Summary'] = item['description']
                meta['Release Date'] = item['Release Date']
                meta['Person Translator'] = ""
                meta['Year'] = item['Year']
                meta['Month'] = item['Month']
                meta['Day'] = item['Day']
                meta['Publication Status'] = item['Publication Status']
                

                if 'tag' in item:
                    meta['Tags'] = item['tag']
                else:
                    meta['Tags'] = None
                meta['Genres'] = item['genre']
                meta['Name'] = item['title']
                if 'META' in self.config['MAKE_COVER']:
                    coverpath = os.path.join(dirpath, 'cover.jpg')
                    if os.path.exists(coverpath) == False:
                        urllib.request.urlretrieve(item['poster_url'], coverpath)
                        with open(coverpath, 'rb') as f:
                            buff = f.read()
                        self.get_thumbnail_str(BytesIO(buff), coverpath)
                        

                break
        info['meta'] = meta
        
    def meta_kakaopage(self,info,dirpath,meta):
        name = meta['Name']
        name = os.path.basename(dirpath)
        search_data = SiteKakaoPage.search(name,(self.config.get('META_GENRE') == "COMIC"),(self.config.get('IS_EBOOK') == True))

        if search_data['ret'] == 'success':
            count = min(10, len(search_data['data']))
            info['search'] = search_data['data'][:count]
        
        if info.get('search') and len(info['search']) > 0 and info['action']['code'] == '':
            info['action']['code'] = info['search'][0]['code']
        
        for item in info.get('search', []):
            if item['code'] == info['action']['code']:
                logger.debug(d(item))
                meta['Web Links'] = item['link']
                meta['Person Writers'] = item['author']
                meta['Person Penciller'] = ""
                meta['Person Publisher'] = item['publisher']
                meta['Summary'] = item['description']
                meta['Release Date'] = item['Release Date']
                meta['Person Translator'] = ""
                meta['Year'] = item['Year']
                meta['Month'] = item['Month']
                meta['Day'] = item['Day']
                meta['Publication Status'] = item['Publication Status']
                

                if 'tag' in item:
                    meta['Tags'] = item['tag']
                else:
                    meta['Tags'] = None
                meta['Genres'] = item['genre']
                meta['Name'] = item['title']
                if 'META' in self.config['MAKE_COVER']:
                    coverpath = os.path.join(dirpath, 'cover.jpg')
                    if os.path.exists(coverpath) == False:
                        urllib.request.urlretrieve(item['poster_url'], coverpath)
                        with open(coverpath, 'rb') as f:
                            buff = f.read()
                        self.get_thumbnail_str(BytesIO(buff), coverpath)
                        

                break
        info['meta'] = meta
        
    def meta_ridibooks(self, info, dirpath, meta):
        name = meta['Name']
        # info['meta'] = meta
        # print(info['meta']['Person Writers'])
        name = os.path.basename(dirpath)
        search_data = SiteRidi.search(name,(self.config.get('META_GENRE') == "COMIC"),self.config.get('IS_EBOOK'))
        if search_data['ret'] == 'success':
            count = min(10, len(search_data['data']))
            info['search'] = search_data['data'][:count]
        
        if info.get('search') and len(info['search']) > 0 and info['action']['code'] == '' and info['search'][0]['score'] > 98:
            info['action']['code'] = info['search'][0]['code']
        
        for item in info.get('search', []):
            if item['code'] == info['action']['code']:
                logger.debug(d(item))
                meta['Web Links'] = item['link']
                meta['Person Writers'] = item['author']
                meta['Person Penciller'] = item['illustrator']
                meta['Person Publisher'] = item['publisher']
                meta['Summary'] = item['description']
                meta['Release Date'] = item['Release Date']
                meta['Person Translator'] = item['Person Translator']
                meta['Year'] = item['Year']
                meta['Month'] = item['Month']
                meta['Day'] = item['Day']
                meta['Publication Status'] = item['Publication Status']
                

                if 'tag' in item:
                    meta['Tags'] = item['tag']
                else:
                    meta['Tags'] = None
                if 'category_name' in item:
                    meta['Genres'] = item['parent_category_name'] + ',' + item['category_name']
                meta['Name'] = item['title']
                if 'META' in self.config['MAKE_COVER']:
                    coverpath = os.path.join(dirpath, 'cover.jpg')
                    if os.path.exists(coverpath) == False:
                        urllib.request.urlretrieve(item['poster_url'], coverpath)
                        with open(coverpath, 'rb') as f:
                            buff = f.read()
                        self.get_thumbnail_str(BytesIO(buff), coverpath)
                        

                break
        info['meta'] = meta


    def meta_ridibooks2(self, info, dirpath, meta):
        name = meta['Name']
        info['meta'] = meta

        name = os.path.basename(dirpath)
        search_data = SiteRidi.search(name)
        if search_data['ret'] == 'success':
            count = min(10, len(search_data['data']))
            info['search'] = search_data['data'][:count]

            for idx, data in enumerate(search_data['data']):
                #logger.info(f"{d(data)}")
                logger.info(f"{idx}. [{data['author']}] {data['title']} | {data.get('parent_category_name', '')}/{data.get('category_name', '')}")
            
            logger.warning(f"{os.path.basename(dirpath)}")
            select_idx = input("선택 idx: ")
            item = None
            if select_idx == "":
                info['action']['code'] = ""
            else:
                item = search_data['data'][int(select_idx)]

            if item != None:
                info['action']['code'] = item['code']
                
                logger.debug(d(item))
                meta['Web Links'] = item['link']
                meta['Person Writers'] = item['author']
                meta['Person Publisher'] = item['publisher']
                meta['Summary'] = item['description']
                meta['Tags'] = item['tag']
                meta['Name'] = item['title']
                
                
        else:
            info['action']['code'] = ""

        info['meta'] = meta

        

            



    def meta_naver(self, info, dirpath, meta):
        name = meta['Name']
        if 'meta' in info:
            author = info['meta']['Person Writers']
        else:
            author = meta['Person Writers']
            
        search_data = SiteNaverBook.search(name, author, "", "", "")
        if search_data['ret'] == 'success':
            info['search'] = search_data['data']
        if search_data['ret'] == 'empty':
            second = re.sub(r"\(.*?\)", '', name)
            if second != name:
                name = second
                search_data = SiteNaverBook.search(name, "", "", "", "")
                if search_data['ret'] == 'success':
                    info['search'] = search_data['data']


        #for item in info['search']:
        #    logger.debug(item)
        if info.get('search') and len(info['search']) > 0 and info['action']['code'] == '' and info['search'][0]['score'] > 98:
            info['action']['code'] = info['search'][0]['code']
        
        for item in info.get('search', []):
            if item['code'] == info['action']['code']:
                logger.debug(d(item))
                meta['Web Links'] = item['link']
                meta['Person Writers'] = item['author']
                meta['Person Publisher'] = item['publisher']
                meta['Release Date'] = item.get('pubdata', '')
                if meta['Release Date'] != "":
                    meta['Year'] = meta['Release Date'][0:4]
                    meta['Month'] = meta['Release Date'][4:6]
                    meta['Day'] = meta['Release Date'][6:]
                #meta['ISBN'] = item['isbn']
                meta['Summary'] = item['description']
                if 'META' in self.config['MAKE_COVER']:
                    coverpath = os.path.join(dirpath, 'cover.jpg')
                    
                    if os.path.exists(coverpath) == False:
                        urllib.request.urlretrieve(item['image'], coverpath)
                        with open(coverpath, 'rb') as f:
                            buff = f.read()
                        self.get_thumbnail_str(BytesIO(buff), coverpath)
                break
        info['meta'] = meta

    def meta_xml(self, info, dirpath, meta):
        tmp = os.path.join(dirpath, 'info.xml')
        if os.path.exists(tmp):
            with open(tmp, 'r', encoding='utf8') as f:
                data = f.read()
            data = json.loads(json.dumps(xmltodict.parse(data)))
            #logger.debug(d(data))
            data = data['ComicInfo']
            meta['Name'] = data['Series']  if data['Series'] else meta['Name']
            info['action']['code']  = meta['Name']
            meta['Summary'] = data['Summary']  if data['Summary'] else meta['Summary']
            meta['Person Writers'] = data['Writer']  if data['Writer'] else meta['Person Writers']
            meta['Person Publisher'] = data['Publisher']  if data['Publisher'] else meta['Person Publisher']
            meta['Genres'] = data['Genre']  if data['Genre'] else meta['Genres']
            meta['Tags'] = data['Tags']  if data['Tags'] else meta['Tags']
            meta['Language'] = data['LanguageISO']  if data['LanguageISO'] else meta['Language']
            try:
                if data['Notes'] == '완결':
                    meta['Publication Status'] = '2'
                else:
                    pass
            except:
                pass
            meta['Person Penciller'] = data['Penciller'] if data['Penciller'] else meta['Person Penciller']
            meta['Person Inker'] = data['Inker'] if data['Inker'] else meta['Person Inker']
            meta['Person Colorist'] = data['Colorist'] if data['Colorist'] else meta['Person Colorist']
            meta['Person Letterer'] = data['Letterer'] if data['Letterer'] else meta['Person Letterer'] 
            meta['Person Editor'] = data['Editor'] if data['Editor'] else meta['Person Editor']
            meta['Person Character'] = data['Characters'] if data['Characters'] else meta['Person Character']
            meta['Year'] = data['Year'] if data['Year'] else meta['Year']
            meta['Month'] = data['Month'] if data['Month'] else meta['Month']
            meta['Day'] = data['Day'] if data['Day'] else meta['Day'] 
            meta['Release Date'] = data['Year'] + data['Month'] + data['Day'] 

        info['meta'] = meta
            #meta = 










    #############################################
    # process
    #############################################
    def process_archive(self, zipfilepath):
        page_count = 0
        img_str = ''
        zip_ins = zipfile.ZipFile(zipfilepath)
        zipfilelist = zip_ins.namelist()

        for file_on_zip in zipfilelist:
            tmps = os.path.splitext(file_on_zip)
            if tmps[1].lower() in ['.png', '.jpg', '.gif', '.jpeg', '.webp']:
                page_count +=1
        
        zip_ins = zipfile.ZipFile(zipfilepath)
        zipfilelist = zip_ins.namelist()
        zipfilelist = sorted(zipfilelist)
        #print(f"파일수 : {len(zipfilelist)}")
        for file_on_zip in zipfilelist:
            tmps = os.path.splitext(file_on_zip)
            if tmps[1].lower() in ['.png', '.jpg', '.gif', '.jpeg', '.webp']:
                img_str = self.get_thumbnail_str(BytesIO(zip_ins.read(file_on_zip)))
                if img_str != '':
                    break
        return page_count, img_str               
    
    def process_pdf(self, filepath):
        pdf_info = pdfinfo_from_path(filepath, poppler_path="C:\\poppler-24.07.0\\Library\\bin")
        # pdf_info = pdfinfo_from_path(filepath)
        num_of_pages = pdf_info['Pages']
        pages = convert_from_path(filepath, last_page=1, poppler_path="C:\\poppler-24.07.0\\Library\\bin")
        # pages = convert_from_path(filepath, last_page=1)
        img_str = self.get_thumbnail_str(None, image=pages[0])
        return num_of_pages, img_str

    def process_epub(self, filepath):
        zip_ins = zipfile.ZipFile(filepath)
        zipfilelist = zip_ins.namelist()
        page_count = 0
        word_count = 0
        for file_on_zip in zipfilelist:
            tmps = os.path.splitext(file_on_zip)
            if tmps[1].lower().endswith('html') or tmps[1].lower().endswith('htm'):
                page_count +=1
                #parser = etree.XMLParser(resolve_entities=False,strip_cdata=False,recover=True)
                #root = etree.XML(zip_ins.read(file_on_zip), parser=parser)
                tmp = zip_ins.read(file_on_zip).decode('utf8')
                tmp = tmp.replace('&nbsp;',' ')
                try:
                    root = etree.fromstring(tmp.encode('utf8'))
                    tags = root.xpath('//xhtml:body//text()', namespaces=namespaces)
                    #logger.error(tags)
                    texts = [len(x) for x in tags]
                    word_count += sum(texts)
                except Exception as e:
                    logger.error(str(e))
        cover, meta = self.get_epub_cover(filepath)
        img_str = self.get_thumbnail_str(cover)
        return page_count, img_str, word_count

    def get_epub_cover(self, epub_path):
        with zipfile.ZipFile(epub_path) as z:
            meta = {}
            try:
                t = etree.fromstring(z.read("META-INF/container.xml"))
                rootfile_path =  t.xpath("/u:container/u:rootfiles/u:rootfile",namespaces=namespaces)[0].get("full-path")
                print("Path of root file found: " + rootfile_path)
                opfroot = etree.fromstring(z.read(rootfile_path))
                meta['Chapter Title'] = ''.join(opfroot.xpath('//dc:title/text()', namespaces=namespaces))
                meta['Name'] = ''.join(opfroot.xpath('//calibre:series/text()', namespaces=namespaces))
                meta['Volume'] = ''.join(opfroot.xpath('//calibre:series_index/text()', namespaces=namespaces))
                meta['Summary'] = ''.join(opfroot.xpath('//dc:description/text()', namespaces=namespaces))

                meta['Publisher'] = ''.join(opfroot.xpath('//dc:publisher/text()', namespaces=namespaces))
                meta['Writer'] = ''.join(opfroot.xpath('//dc:creator/text()', namespaces=namespaces))

                meta['Genres'] = ''.join(opfroot.xpath('//dc:subject/text()', namespaces=namespaces))

                meta['Language'] = ''.join(opfroot.xpath('//dc:language/text()', namespaces=namespaces))
                meta['ISBN'] = ''.join(opfroot.xpath('//dc:identifier[@opf:scheme="ISBN"]/text()', namespaces=namespaces))
                meta['Release Date'] = ''.join(opfroot.xpath('//dc:date/text()', namespaces=namespaces))
                #meta['Release Date'] = ''.join(root.xpath('//Year/text()', namespaces=namespaces)) 
            except:
                print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')

            cover_href = None
            try:
                cover_id = opfroot.xpath("//opf:metadata/opf:meta[@name='cover']",namespaces=namespaces)[0].get("content")
                print("ID of cover image found: " + cover_id)
                cover_href = opfroot.xpath("//opf:manifest/opf:item[@id='" + cover_id + "']", namespaces=namespaces)[0].get("href")
            except IndexError:
                pass

            if not cover_href:
                try:
                    cover_href = opfroot.xpath("//opf:manifest/opf:item[@properties='cover-image']", namespaces=namespaces)[0].get("href")
                except IndexError:
                    pass

            if not cover_href:
                try:
                    cover_page_id = opfroot.xpath("//opf:spine/opf:itemref", namespaces=namespaces)[0].get("idref")
                    cover_page_href = opfroot.xpath("//opf:manifest/opf:item[@id='" + cover_page_id + "']", namespaces=namespaces)[0].get("href")
                    cover_page_path = os.path.dirname(rootfile_path) + '/'+ cover_page_href
                    print("Path of cover page found: " + cover_page_path)
                    #t = etree.fromstring(z.read(cover_page_path).replace())
                    cover_page_path = cover_page_path.lstrip('/')
                    tmp = z.read(cover_page_path).decode('utf8').replace('&nbsp;', ' ')
                    tmp = tmp.encode('utf8')
                    t = etree.fromstring(tmp)
                    cover_href = t.xpath("//xhtml:img", namespaces=namespaces)[0].get("src")
                except IndexError:
                    pass
            include_root = False
            if not cover_href:
                img_count = 0
                img_path = ""
                for f in z.filelist:
                    if f.filename.endswith('.png') or f.filename.endswith('.jpg') or f.filename.endswith('.jpeg'):
                        img_count += 1
                        img_path = f.filename
                    if f.filename.endswith('cover.jpg'):
                        cover_href = f.filename
                        include_root = True
                        break
                if not cover_href and img_count == 1:
                    cover_href = img_path
                    include_root = True

            if not cover_href:
                try:
                    import re
                    text = etree.tostring(opfroot).decode()
                    match = re.search('(href|src)=\"(?P<href>[^"]+?\.(png|jpg|jpef))\"', text)
                    if match:
                        cover_href = match.group('href')
                        cover_href = urllib.parse.unquote_plus(cover_href)
                except Exception as e:
                    print(e)
                    print(e)

            if not cover_href:
                return None, meta

            if include_root == False:
                #cover_path = os.path.join(os.path.dirname(rootfile_path), cover_href)
                cover_path = os.path.dirname(rootfile_path) + '/' + cover_href
                print("Path of cover image found: " + cover_path)
                cover_path = cover_path.replace('/../', '/')

                zipfilelist = z.namelist()
                #print(zipfilelist)

                if '.jpeg' in cover_path and cover_path.replace('.jpeg', '.jpg') in zipfilelist:
                    cover_path = cover_path.replace('.jpeg', '.jpg')
                cover_path = cover_path.lstrip('/')
                try:
                    #logger.warning(cover_path.decode('utf8').encode("ascii","ignore"))
                    ret = z.open(cover_path)
                except:
                    try:
                        ret = z.open(cover_path.replace('.jpeg', '.jpg'))
                    except:
                        tmp = cover_path.replace('%5B', '[').replace('%5D', ']')
                        try:
                            ret = z.open(cover_path)
                        except:
                            try:
                                ret = z.open(urllib.parse.unquote(cover_path))
                            except:
                                ret = z.open(cover_href.replace('..', '').lstrip(('/')))
                            
            else:
                ret = z.open(cover_href)
                    
            return ret, meta
        
    #############################################
    # Tool
    #############################################
    def get_thumbnail_str(self, fileio, filepath=None, image=None):
        img_str = ""
        try:
            if image == None:
                im = Image.open(fileio)
                im = im.convert('RGB')
            else:
                im = image
            basewidth = 320
            # 가로형
            if self.config.get('WIDEIMAGE') == 'LEFT':
                if im.size[0] > im.size[1]:
                    im = im.crop((0, 0, im.size[0]/2, im.size[1]))
            wpercent = (basewidth/float(im.size[0]))
            hsize = int((float(im.size[1])*float(wpercent)))
            im2 = im.resize((basewidth,hsize), Image.LANCZOS)
            if filepath == None:
                buff = BytesIO()
                im2.save(buff, format='PNG')
                img_str = base64.b64encode(buff.getvalue()).decode("utf-8")
            else:
                im2.save(filepath, format='JPEG')
        except Exception as e:
            

            logger.error(f"썸네일 실패")
            logger.error(str(e))
            logger.error(filepath)
        return img_str


    def save_cover(self, img_str, dir_path):
        filepath = os.path.join(dir_path, 'cover.png')
        
        with open(filepath, 'wb') as f:
            bytes = base64.b64decode(img_str)
            f.write((bytes))






EXTENSIONS = ["cbz", "zip", "rar", "cbr", "tar.gz", "7zip", "7z", "cb7", "cbt", "pdf", "epub", 'txt']
KAVITA_INFO = "kavita.yaml"

namespaces = {
   "calibre":"http://calibre.kovidgoyal.net/2009/metadata",
   "dc":"http://purl.org/dc/elements/1.1/",
   "dcterms":"http://purl.org/dc/terms/",
   "opf":"http://www.idpf.org/2007/opf",
   "u":"urn:oasis:names:tc:opendocument:xmlns:container",
   "xsi":"http://www.w3.org/2001/XMLSchema-instance",
   "xhtml":"http://www.w3.org/1999/xhtml"
}

META = {
    "Name": "",
    "Publication Status": "",
    "Summary": "",
    "Release Date": "",
    "Year": "",
    "Month": "",
    "Day": "",
    "Genres": "",
    "Tags": "",
    "Web Links": "",
    "Writer": "",
    "Language": "",
    "Collections": "",
    "Age Rating": "",
    "Person Writers": "",
    "Person Penciller": "",
    "Person Character": "",
    "Person Colorist": "",
    "Person Editor": "",
    "Person Inker": "",
    "Person Imprint": "",
    "Person Team": "",
    "Person Location": "",
    "Person Letterer": "",
    "Person Translator": "",
    "Person Publisher": "",
    "Person CoverArtist": "",
}


ACTION = {
    "code": "",
    "first_cover": False,
    "all_file_is_special": False,
}

