import argparse
import os

import yaml

from mod_makeinfo import ModMakeInfo
from site_naver_book import SiteNaverBook
from site_ridi import SiteRidi
from tool import d, get_logger, pt

logger = get_logger()

class Kavita:

    def __init__(self, config, args) -> None:
        self.config = config
        self.args = args
        SiteNaverBook.apikey = self.config.get('NAVER_APIKEY', [])
        self.option = None
        if self.args.option != None:
            for opt in self.config.get('OPTIONS', []):
                if str(opt['NAME']) == self.args.option:
                    self.option = opt
                    break
        if self.option == None:
            self.option = self.config.get('OPTIONS')[0]
        if 'META_GENRE' not in self.option:
            self.option['META_GENRE']=""

    def run(self):
        if self.option['MODE'] == 'MAKEINFO':
            ModMakeInfo(self.option).start()
        elif self.option['MODE'] == 'RIDIMOVE':
            SiteRidi.folder_move(self.option)
        elif self.option['MODE'] == 'RIDIMOVE2':
            SiteRidi.folder_move2(self.option)
    

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=False, default=None, help="설정파일경로")
    parser.add_argument('--option', required=False, default=None, help="선택 옵션")
    args = parser.parse_args()
    if args.config == None:
        args.config = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.yaml')

    with open(args.config , encoding='utf8') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
        Kavita(config, args).run()
