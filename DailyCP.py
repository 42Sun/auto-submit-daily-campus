import requests
import json
import io
import random
import time
import re
import pyDes
import base64
import uuid
import sys
from Crypto.Cipher import AES

class DailyCP:
    def __init__(self, schoolName="安徽理工大学"):
        self.key = "ST83=@XV"#dynamic when app update
        self.session = requests.session()
        self.host = ""
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Pragma": "no-cache",
            "Accept": "application/json, text/plain, */*",
            # "User-Agent": "okhttp/3.12.4"
        })
        extension = {"deviceId":str(uuid.uuid4()),"systemName":"未来操作系统","userId":"5201314","appVersion":"8.1.13","model":"红星一号量子计算机","lon":0.0,"systemVersion":"初号机","lat":0.0}
        self.session.headers.update({"Cpdaily-Extension": self.encrypt(json.dumps(extension))})
        self.setHostBySchoolName(schoolName)

    def setHostBySchoolName(self,schoolName):
        ret = self.request("https://static.campushoy.com/apicache/tenantListSort")
        school = [j for i in ret["data"] for j in i["datas"] if j["name"] == schoolName]
        if len(school) == 0:
            print("不支持的学校或者学校名称错误,以下是支持的学校列表")
            print(ret)
            exit()
        ret = self.request("https://mobile.campushoy.com/v6/config/guest/tenant/info?ids={ids}".format(ids=school[0]["id"]))
        ret = re.findall(r"//(.*?)/",ret["data"][0]["idsUrl"])
        if len(ret) == 0:
            print("学校并没有申请入驻今日校园平台")
            exit()
        self.host = ret[0]

    def encrypt(self,text):
        k = pyDes.des(self.key, pyDes.CBC, b"\x01\x02\x03\x04\x05\x06\x07\x08", pad=None, padmode=pyDes.PAD_PKCS5)
        ret = k.encrypt(text)
        return base64.b64encode(ret).decode()

    def passwordEncrypt(self,text:str,key:str):
        pad = lambda s: s + (16 - len(s) % 16) * chr(16 - len(s) % 16)
        unpad = lambda s: s[:-ord(s[len(s) - 1:])]
        text = pad("TdEEGazAXQMBzEAisrYaxRRax5kmnMJnpbKxcE6jxQfWRwP2J78adKYm8WzSkfXJ"+text).encode("utf-8")
        aes = AES.new(str.encode(key), AES.MODE_CBC,str.encode("ya8C45aRrBEn8sZH"))
        return base64.b64encode(aes.encrypt(text))

    def request(self,url:str,body=None,parseJson=True,JsonBody=True):
        url = url.format(host=self.host)
        if body == None:ret = self.session.get(url).text
        else:
            self.session.headers.update({"Content-Type": ("application/json" if JsonBody else "application/x-www-form-urlencoded")})
            ret = self.session.post(url,data=(json.dumps(body) if JsonBody else body)).text
        if parseJson:return json.loads(ret)
        else:return ret

    def decrypt(self,text):
        k = pyDes.des(self.key, pyDes.CBC, b"\x01\x02\x03\x04\x05\x06\x07\x08", pad=None, padmode=pyDes.PAD_PKCS5)
        ret = k.decrypt(base64.b64decode(text))
        return ret.decode()

    def checkNeedCaptcha(self, username):
        url = "https://{host}/iap/checkNeedCaptcha?username={username}".format(host=self.host,username=username)
        ret = self.session.get(url)
        ret = json.loads(ret.text)
        return ret["needCaptcha"]

    def generateCaptcha(self):
        url = "https://{host}/iap/generateCaptcha?ltId={client}&codeType=2".format(host=self.host,client=self.client)
        ret = self.session.get(url)
        return ret.content

    def getBasicInfo(self):
        return self.request("https://{host}/iap/tenant/basicInfo","{}")

    def login(self, username, password, captcha=""):
        if self.host.find("authserver") != -1:return self.loginAuthserver(username,password,captcha)
        else: return self.loginIAP(username,password,captcha)

    def loginIAP(self, username, password, captcha=""):
        ret = self.session.get("https://{host}/iap/login?service=https://{host}/portal/login".format(host=self.host)).url
        client = ret[ret.find("=")+1:]
        ret = self.request("https://{host}/iap/security/lt","lt={client}".format(client=client),True,False)
        client = ret["result"]["_lt"]
        #self.encryptSalt = ret["result"]["_encryptSalt"]

        body = {
            "username": username,
            "password": password,
            "lt": client,
            "captcha": captcha,
            "rememberMe": "true",
            "dllt": "",
            "mobile": ""
        }
        ret = self.request("https://{host}/iap/doLogin",body,True,False)
        if ret["resultCode"] == "REDIRECT":
            self.session.get(ret["url"])
            return True
        else: return False

    def checkNeedCaptchaAuthServer(self,username):
        ret = self.request("http://{host}/authserver/needCaptcha.html?username={username}&pwdEncrypt2=pwdEncryptSalt".format(username=username),parseJson=False)
        return ret == "true"

    def loginAuthserver(self,username,password,captcha=""):
        ret = self.request("https://{host}/authserver/login",parseJson=False)
        body = dict(re.findall(r'''<input type="hidden" name="(.*?)" value="(.*?)"''',ret))
        salt = dict(re.findall(r'''<input type="hidden" id="(.*?)" value="(.*?)"''',ret))
        body["username"] = username
        body["password"] = self.passwordEncrypt(password,salt["pwdDefaultEncryptSalt"])
        ret = self.request("https://{host}/authserver/login",body,False,False)
        #由于手头上没有测试账号，请小伙伴自行测试可用性。
        #有些学校的登录过程包含验证码

    def getCollectorList(self):
        body = {
            "pageSize": 10,
            "pageNumber": 1
        }
        ret = self.request("https://{host}/wec-counselor-collector-apps/stu/collector/queryCollectorProcessingList",body)
        return ret["datas"]["rows"]

    def getNoticeList(self):
        body = {
            "pageSize": 10,
            "pageNumber": 1
        }
        ret = self.request("https://{host}/wec-counselor-stu-apps/stu/notice/queryProcessingNoticeList",body)
        return ret["datas"]["rows"]

    def confirmNotice(self, wid):
        body = {
            "wid": wid
        }
        ret = self.request("https://{host}/wec-counselor-stu-apps/stu/notice/confirmNotice",body)
        print(ret["message"])
        return ret["message"] == "SUCCESS"

    def getCollectorDetail(self, collectorWid):
        body = {
            "collectorWid": collectorWid
        }
        return self.request("https://{host}/wec-counselor-collector-apps/stu/collector/detailCollector",body)["datas"]

    def getCollectorFormFiled(self, formWid, collectorWid):
        body = {
            "pageSize": 50,
            "pageNumber": 1,
            "formWid": formWid,
            "collectorWid": collectorWid
        }
        return self.request("https://{host}/wec-counselor-collector-apps/stu/collector/getFormFields",body)["datas"]["rows"]

    def submitCollectorForm(self, formWid, collectWid, schoolTaskWid, rows, address):
        body = {
            "formWid": formWid,
            "collectWid": collectWid,
            "schoolTaskWid": schoolTaskWid,
            "form": rows,
            "address": address
        }
        ret = self.request("https://{host}/wec-counselor-collector-apps/stu/collector/submitForm",body)
        print(ret["message"])
        return ret["message"] == "SUCCESS"

    def autoFill(self, rows):
        for item in rows:
            index = 0
            while index < len(item["fieldItems"]):
                if item["fieldItems"][index]["isSelected"] == 1:index = index + 1
                else:item["fieldItems"].pop(index)
        #此函数通过表格的默认值自动填写，如果你们学校没有提供默认值的，需要手动编辑此函数。
        #先print(rows)，观察表格的形式，想选择哪一个选项，pop掉其他无关选项就行了。当然也可以直接将rows硬编码在代码里面。
        #因为每个人的定位地址都不一样，有些学校的表格也不一定一样，所以这里就不写细节了。

    def autoComplete(self, address):
        collectList = self.getCollectorList()
        print(collectList)
        for item in collectList:
            detail = self.getCollectorDetail(item["wid"])
            form = self.getCollectorFormFiled(detail["collector"]["formWid"], detail["collector"]["wid"])
            self.autoFill(form)
            self.submitCollectorForm(detail["collector"]["formWid"], detail["collector"]["wid"], detail["collector"]["schoolTaskWid"], form, address)

        confirmList = self.getNoticeList()
        print(confirmList)
        for item in confirmList:self.confirmNotice(item["noticeWid"])


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("python3 DailyCp.py 学校全名 学号 密码 定位地址")
        exit()
    app = DailyCP(sys.argv[1])
    if not app.login(sys.argv[2], sys.argv[3]):exit()
    app.autoComplete(sys.argv[3])

# Author:HuangXu,FengXinYang,ZhouYuYang.
# By:AUST HACKER

#2020/5/20 重要更新：修复登录过程，移除验证码（不需要），优化代码格式，感谢giteee及时反馈。
#2020/5/28 更改为使用自动获取学校URL的方式，更改为使用参数形式，添加另一种登录形式AuthServer的支持(已完成但未测试)。感谢柠火的反馈。