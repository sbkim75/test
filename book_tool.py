import argparse
import base64
import json
import os
import re
import traceback
import urllib
import urllib.parse
import zipfile
from io import BytesIO
from typing import OrderedDict

import requests
import xmltodict
import yaml
from lxml import etree
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
from site_naver_book import SiteNaverBook
from site_ridi import SiteRidi
from tool import d, get_logger, pt

logger = get_logger()


class Tool:

    def __init__(self, config, args) -> None:
        self.config = config
        self.args = args
        SiteNaverBook.apikey = self.config['NAVER_APIKEY']
        for key, value in self.config.get('DEFAULT_META', {}).items():
            META[key] = value
        for key, value in self.config.get('DEFAULT_ACTION', {}).items():
            ACTION[key] = value


    def run(self):
        run_mode = self.args.run_mode if self.args.run_mode != None else self.config['RUN_MODE']
        if run_mode == 'MAKEINFO':
            self.makeinfo()
        elif run_mode == 'RIDIMOVE':
            SiteRidi.folder_move(self.config)
        


    def makeinfo(self):
        root = self.config['ROOT']
        logger.error(root)
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

                        elif os.path.exists(kavita_info_path) and self.config.get('PROCESS_EXIST_KAVITA_YAML') == "PASS":
                            continue
                        self.makeinfo_folder(dirpath, kavita_info_path)
                
                except Exception as e: 
                    logger.error(f"Exception:{str(e)}")
                    logger.error(traceback.format_exc())
                
    
    def makeinfo_folder(self, dirpath, kavita_info_path):
        info = None
        logger.info(f">> {dirpath}")
        """
        if os.path.exists(kavita_info_path):
            info = None
            with open(kavita_info_path, encoding='utf8') as file:
                info = yaml.load(file, Loader=yaml.FullLoader)
            if info and (info['action']['code'] == "" or info['action']['code'].startswith('BN')):
                logger.error("여기여기")
                os.remove(kavita_info_path)
            return
        else:
            return
        """
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
        #files = OrderedDict()
        
        first_image = False
        # epub 메타를 시리즈에 적용했는가? ... 한번만
        flag_apply_epub_meta = False
        for filename in list(sorted(os.listdir(dirpath))):
            tmps = filename.rsplit('.', 1)
            if len(tmps) != 2:
                continue
            if info['files'].get(filename) != None and (info['files'].get(filename)['cover'] != None and info['files'].get(filename)['cover'] != ''):
                continue
            if tmps[1].lower() in EXTENSIONS:
                if first_image and info['action']['first_cover']:
                    info['files'][filename] = {"page":1, "wordcount":0, "cover":"FIRST"}
                else:
                    info['files'][filename] = {"page":1, "wordcount":0, "cover":""}
                wordcount = 0
                pagecount = 0
                img_str = ""
                
                try:
                    filepath = os.path.join(dirpath, filename)
                    if tmps[1].lower() == 'epub':
                        pagecount, img_str, wordcount, meta = self.process_epub(filepath)
                        if len(meta.keys()) > 0 and flag_apply_epub_meta == False:
                            self.apply_epub_meta(info, meta)
                            flag_apply_epub_meta = True

                    elif tmps[1].lower() == 'pdf':
                        pagecount, img_str = self.process_pdf(filepath)
                    else:
                        pagecount, img_str = self.process_archive(filepath)

                    info['files'][filename]['page'] = pagecount
                    info['files'][filename]['cover'] = img_str
                    info['files'][filename]['wordcount'] = wordcount
                    #info['files'][filename]['meta'] = meta
                    
                    if first_image == False and self.config['MAKE_COVER'] == 'LOCAL_ONLY_EPUB' and tmps[1].lower() == 'epub':
                        self.save_cover(img_str, dirpath)
                    elif first_image == False and self.config['MAKE_COVER'] == 'LOCAL':
                        self.save_cover(img_str, dirpath)
                    if info['action']['first_cover'] and first_image == True:
                        info['files'][filename]['cover'] = "FIRST"
                    first_image = True
                except Exception as e:
                    logger.error(f"GET PAGE 에러 : {filepath}")
                    logger.error(traceback.format_exc())
                             
                logger.info(f"{filename} PAGE:{info['files'][filename]['page']} COVER:{info['files'][filename]['cover'] != ''} WC:{info['files'][filename]['wordcount']}")

        # Meta
        #if info.get('meta') == None:
        if info['action']['code'] == '':
            self.process_meta(info, dirpath)
        
        # 변경된 파일 데이터 지우기
        filenames = list(sorted(os.listdir(dirpath)))
        newfiles = {}
        for filename, value in info['files'].items():
            if filename in filenames:
                newfiles[filename] = value

        logger.info(f"기존: {len(info['files'].keys())}개 / 새로운: {len(newfiles.keys())}개")
        info['files'] = newfiles

        with open(kavita_info_path, 'w', encoding='utf8') as f:
            yaml.dump(info, f, default_flow_style=False, allow_unicode=True, indent=4)


    


    


    















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
            elif self.config['META_SITE'] == 'XML':
                self.meta_xml(info, dirpath, meta)
        except Exception as e:
            logger.error(f"process_meta")
            logger.error(traceback.format_exc())
            info['meta'] = meta
    

    def meta_ridibooks(self, info, dirpath, meta):
        name = meta['Name']
        info['meta'] = meta

        name = os.path.basename(dirpath)
        search_data = SiteRidi.search(name)
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
                meta['Person Publisher'] = item['publisher']
                meta['Summary'] = item['description']
                meta['Tags'] = item['tag']
                meta['Name'] = item['title']
                break
        info['meta'] = meta

    def meta_naver(self, info, dirpath, meta):
        name = meta['Name']
        search_data = SiteNaverBook.search(name, "", "", "", "")
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
            with open(tmp, 'r') as f:
                data = f.read()
            data = json.loads(json.dumps(xmltodict.parse(data)))
            logger.debug(d(data))
            logger.debug(d(data))
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
        pdf_info = pdfinfo_from_path(filepath, poppler_path="C:\\poppler-24.02.0\\Library\\bin")
        num_of_pages = pdf_info['Pages']
        pages = convert_from_path(filepath, last_page=1, poppler_path="C:\\poppler-24.02.0\\Library\\bin")
        img_str = self.get_thumbnail_str(None, image=pages[0])
        return num_of_pages, img_str

    def process_epub(self, filepath):
        zip_ins = zipfile.ZipFile(filepath)
        zipfilelist = zip_ins.namelist()
        page_count = 0
        word_count = 0
        for file_on_zip in zipfilelist:
            tmps = os.path.splitext(file_on_zip)
            if tmps[1].lower().endswith('html'):
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
        return page_count, img_str, word_count, meta

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
                    tmp = z.read(cover_page_path).decode('utf8').replace('&nbsp;', ' ')
                    tmp = tmp.encode('utf8')
                    t = etree.fromstring(tmp)
                    cover_href = t.xpath("//xhtml:img", namespaces=namespaces)[0].get("src")
                except IndexError:
                    pass
            include_root = False
            if not cover_href:
                for f in z.filelist:
                    if f.filename.endswith('cover.jpg'):
                        cover_href = f.filename
                        include_root = True
                        break
                

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
                            ret = z.open(urllib.parse.unquote(cover_path))
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
            wpercent = (basewidth/float(im.size[0]))
            hsize = int((float(im.size[1])*float(wpercent)))
            im2 = im.resize((basewidth,hsize), Image.ANTIALIAS)
            if filepath == None:
                buff = BytesIO()
                im2.save(buff, format='PNG')
                img_str = base64.b64encode(buff.getvalue()).decode("utf-8")
            else:
                im2.save(filepath, format='JPEG')
        except Exception as e:
            logger.error(f"썸네일 실패")
        return img_str


    def save_cover(self, img_str, dir_path):
        filepath = os.path.join(dir_path, 'cover.png')
        
        with open(filepath, 'wb') as f:
            bytes = base64.b64decode(img_str)
            f.write((bytes))






EXTENSIONS = ["cbz", "zip", "rar", "cbr", "tar.gz", "7zip", "7z", "cb7", "cbt", "pdf", "epub"]
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




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=False, default=None, help="설정파일경로")
    parser.add_argument('--run-mode', required=False, default=None, help="입력시 설정파일의 RUN_MODE 무시")
    args = parser.parse_args()
    if args.config == None:
        args.config = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')

    with open(args.config , encoding='utf8') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
        Kavita(config, args).run()

