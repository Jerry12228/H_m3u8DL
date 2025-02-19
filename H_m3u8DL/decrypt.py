import subprocess
import sys,os
import base64,json,re
import requests
from H_m3u8DL import delFile
from H_m3u8DL.Util import util


class Decrypt:
    def __init__(self, m3u8obj, temp_dir, method=None, key=None, iv=None,nonce=None, headers=None):
        if headers is None:
            self.headers = {'user-agent',
                       'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63030532) Edg/100.0.4896.60'}
        self.m3u8obj = m3u8obj

        self.segments = m3u8obj.data['segments']
        if method is None:
            self.method = m3u8obj.data['keys'][-1]['method']
            # self.method = self.segments[0]['key']['method']
            # if self.method is None and 'keys' in m3u8obj.data:
            #     self.method = m3u8obj.data['keys'][-1]['method']


        self.temp_dir = temp_dir
        self.method = method
        self.key = key
        self.iv = iv
        self.nonce = nonce



    def judge_method(self):
        WideVine = ['SAMPLE-AES-CTR', 'cbcs', 'SAMPLE-AES']
        if self.method == 'AES-128':
            self.mode_AES_128()

        elif self.method == 'SAMPLE-AES-CTR':
            self.mode_SAMPLE_AES_CTR()
        elif self.method ==  'SAMPLE-AES':
            self.mode_SAMPLE_AES()

        elif self.method == 'KOOLEARN-ET':
            self.mode_KOOLEARN_ET()
        elif self.method == 'copyrightDRM':
            self.mode_copyrightDRM()
        elif self.method == 'CHACHA':
            self.mode_CHACHA()
        elif self.method == 'default':
            self.mode_default()

        else:
            self.mode_AES_128()

    def mode_AES_128(self):
        self.key = self.dec_key()
        self.iv = self.dec_iv()
        for i, segment in enumerate(self.segments):
            self.segments[i]['key']['uri'] = self.key
            self.segments[i]['key']['iv'] = self.iv

    def mode_AES_128_ECB(self):
        self.key = self.dec_key()

        for i, segment in enumerate(self.segments):
            self.segments[i]['key']['uri'] = self.key

    def mode_SAMPLE_AES(self):
        init = self.segments[0]['init_section']['uri']
        with open(self.temp_dir + '.mp4', 'wb') as f:
            f.write(requests.get(init).content)
            f.close()

    def mode_SAMPLE_AES_CTR(self):

        init = self.m3u8obj.base_uri + self.segments[0]['init_section']['uri'] if self.segments[0]['init_section']['uri'][:4] != 'http' else self.segments[0]['init_section']['uri']

        with open(self.temp_dir + '.mp4', 'wb') as f:
            f.write(requests.get(init).content)
            f.close()
        # if 'key' in self.segments[0]:
        #
        #     init = self.segments[0]['key']['uri']
        #     with open(self.temp_dir+'.mp4', 'wb') as f:
        #         f.write(base64.b64decode(init.split(',')[-1]))
        #         f.close()
        # else:
        #     print('decrypt 63 init_section:',self.segments[0]['init_section']['uri'])
        #     init = self.segments[0]['init_section']['uri']
        #
        #     with open(self.temp_dir + '.mp4', 'wb') as f:
        #         f.write(requests.get(init).content)
        #         f.close()


    def mode_KOOLEARN_ET(self):
        self.mode_AES_128() # 整合

    def mode_copyrightDRM(self):
        pass
    def mode_CHACHA(self):
        self.key = self.dec_key()
        self.nonce = self.dec_nonce()
        for i, segment in enumerate(self.segments):
            self.segments[i]['key']['uri'] = self.key

            self.segments[i]['key']['nonce'] = self.nonce

    def mode_cbcs(self):
        pass
    def mode_default(self):
        pass

    def dec_key(self):
        # 自定义key
        deckey = ''
        if self.key != None:
            if 'http' in self.key:
                key_temp = requests.get(url=self.segments[0]['key']['uri'], headers=self.headers).content
                deckey = base64.b64encode(key_temp).decode()

            elif '{' in self.key:
                deckeys = re.findall('{.+?}', self.segments[0]['key']['uri'])
                for dk in deckeys:
                    dk = json.loads(dk)
                    index_begin = dk['index'][0]
                    index_end = dk['index'][1]
                    if 1 >= index_begin and 1 <= index_end:
                        return dk['key']
            else:
                # hexkey 转 base64
                deckey = self.key if '=' in self.key else base64.b64encode(bytes.fromhex(self.key)).decode()

        # 文件中含key
        elif 'base64:' in self.segments[0]['key']['uri']:
            deckey = re.findall('base64:(.+)', self.segments[0]['key']['uri'])[0]

        elif 'hex:' in self.segments[0]['key']['uri']:
            deckey = base64.b64encode(bytes.fromhex(re.findall('hex:(.+)', self.segments[0]['key']['uri'])[0])).decode()
        # 网络链接
        elif 'http' in self.segments[0]['key']['uri']:
            keyurl = self.segments[0]['key']['uri']

            key_temp = requests.get(url=keyurl).content

            deckey = base64.b64encode(key_temp).decode()



        elif self.segments[0]['key']['uri'][0] == '/':
            self.segments[0]['key']['uri'] = self.m3u8obj.base_uri[:-1] + self.segments[0]['key']['uri']
            key_temp = requests.get(url=self.segments[0]['key']['uri'], headers=self.headers).content
            deckey = base64.b64encode(key_temp).decode()

        elif '{' in self.segments[0]['key']['uri']:

            deckeys = re.findall('{.+?}',self.segments[0]['key']['uri'])

            for dk in deckeys:
                dk = json.loads(dk)
                index_begin = dk['index'][0]
                index_end = dk['index'][1]
                if 1 >= index_begin and 1 <= index_end:
                    return dk['key']

        else:
            print('The key parsed failed.', 'Exit after 5s.')

            sys.exit(0)

        return deckey
    def dec_iv(self):
        if 'iv' not in self.segments[0]['key']:
            return '00000000000000000000000000000000'
        else:
            iv = self.segments[0]['key']['iv'].split('x')[-1]
            if len(iv) != 32:
                return '00000000000000000000000000000000'
            return iv
    def dec_nonce(self):
        if type(self.nonce) == bytes:
            return self.nonce
        elif '=' in self.nonce:
            return base64.b64decode(self.nonce)
        else:
            return bytes.fromhex(self.nonce)

    def run(self):
        self.judge_method()
        return self.method,self.segments

# SAMPLE_AES_CTR/cbcs 合并完成后的解密
def decrypt2(temp_dir,key):
    print('Widevine')
    try:
        # https://widevine-proxy.appspot.com/proxy
        if key is None:
            key = input('输入key：')
            # 转为hex
        if '==' in key:
            key = base64.b64decode(key).hex()
        before_title = temp_dir + '.mp4'
        after_title = temp_dir + '_de.mp4'
        command = fr'{util().mp4decryptPath} --show-progress --key 1:{key} "{before_title}" "{after_title}"'
        # 自行下载 mp4decrypt
        subprocess.call(command)

        delFile.del_file(before_title)
    except:
        print('解密出错，请检查key是否正确并配置mp4decrypt \n')

def decrypt_copyrightDRM(m3u8url,title,key):
    cmd = fr'{util().youkudecryptPath} "{m3u8url}" --workDir "Downloads" --saveName "{title}" --useKeyBase64 "{key}" --enableMuxFastStart --enableYouKuAes '
    print(cmd)
    # "m3u8url" --workDir "Downloads" --saveName "title" --useKeyBase64 "youkukey" --enableMuxFastStart --enableYouKuAes
    subprocess.call(cmd)




