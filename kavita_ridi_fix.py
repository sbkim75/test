import argparse
import base64
import os
import re
import shutil
import traceback
import urllib
import urllib.parse
import zipfile
from io import BytesIO
from typing import OrderedDict

import PyPDF2
import requests
import yaml
from lxml import etree
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image

from site_naver_book import SiteNaverBook
from site_ridi import SiteRidi
from tool import d, get_logger, pt

logger = get_logger()



class Kavita:

    def __init__(self, config, args) -> None:
        self.config = config
        self.args = args
        SiteNaverBook.apikey = self.config['NAVER_APIKEY']
        for key, value in self.config.get('DEFAULT_META', {}).items():
            META[key] = value


    def run(self):
        self.makeinfo()
        

    def makeinfo(self):
        
        root = "I:\\공유 드라이브\\DATA2 - 리딩2\\GDS\\리디셀렉트"
        logger.error(root)
        if type(root) == str:
            root = [root]
        for path in root:
            logger.info(f"ROOT: {path}")
            for dirpath, dirnames, filenames in os.walk(path):
                try:
                    if '리디셀렉트\\[' in dirpath: continue
                    if '리디셀렉트\\111' in dirpath: continue
                    if '리디셀렉트\\222' in dirpath: continue
                    if '리디셀렉트\\333' in dirpath: continue
                    #if '리디셀렉트\\가정.' in dirpath: continue
                    #if '리디셀렉트\\건강.' in dirpath: continue
                    #if '리디셀렉트\\과학' in dirpath: continue
                    #if '리디셀렉트\\로맨스' in dirpath: continue
                    #if '리디셀렉트\\만화' in dirpath: continue
                    ##if '리디셀렉트\\소설' in dirpath: continue
                    #if '리디셀렉트\\어린이' in dirpath: continue
                    #if '리디셀렉트\\에세이' in dirpath: continue
                    #if '리디셀렉트\\여행' in dirpath: continue
                    #if '리디셀렉트\\외국어' in dirpath: continue
                    #if '리디셀렉트\\웹툰' in dirpath: continue
                    #if '리디셀렉트\\인문' in dirpath: continue
                    
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
                        
                        self.makeinfo_folder(dirpath, kavita_info_path)
                
                except Exception as e: 
                    logger.error(f"Exception:{str(e)}")
                    logger.error(traceback.format_exc())
                
    def makeinfo_folder(self, dirpath, kavita_info_path):
        info = None
        logger.debug(f">> {dirpath}")
        
        move_flag = False
        try:
            if os.path.exists(kavita_info_path) == False:
                move_flag = True
                info = None
            with open(kavita_info_path, encoding='utf8') as file:
                info = yaml.load(file, Loader=yaml.FullLoader)
        
            if info['action']['code'].startswith('BN'):
                move_flag = True

            if move_flag == False:
                tmp = os.path.basename(dirpath)
                data = SiteRidi.search(tmp)
                if data['data'][0]['code'] == info['action']['code']:
                    logger.warning("OK")

                    
                    tmp = info['meta']['Tags'].split(',')
                    tmp[0] = tmp[0].replace('/', '.')
                    tmp[1] = tmp[1].replace('/', '.')

                    tmp = os.path.join("I:\\공유 드라이브\\DATA2 - 리딩2\\GDS\\리디셀렉트", tmp[1], tmp[0])
                    tmp1 = os.path.join(tmp, os.path.basename(dirpath))
                    if dirpath != tmp1:
                        logger.error(f"다른 폴더로 이동 {tmp}")
                        shutil.move(dirpath, tmp)
                        import time
                        time.sleep(1)
                    return
                move_flag = True
           
                
        except Exception as e:
            logger.error(f"process_meta")
            logger.error(traceback.format_exc())
            
            move_flag = True
         
        if move_flag:
            logger.error("이동")
            if os.path.exists(kavita_info_path):
                os.remove(kavita_info_path)
            shutil.move(dirpath, "I:\\공유 드라이브\\DATA2 - 리딩2\\GDS\\리디셀렉트\\222")
            import time
            time.sleep(1)



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

